/**
 * Main App component
 * Brings together all components and manages application state
 */

import { useEffect, useState } from "react";
import FileUpload from "./components/FileUpload";
import FileQueue from "./components/FileQueue";
import { usePersistedQueue } from "./hooks/usePersistedQueue";
import { initializeApi, transcribeVideo } from "./api/transcription";
import type { QueuedFile } from "./types/transcription";

function App() {
  const {
    state,
    addFile,
    removeFile,
    updateFile,
    setBackendConnected,
    setAuthToken,
    setCurrentlyProcessing,
    clearCompleted,
  } = usePersistedQueue();

  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize API connection on mount
  useEffect(() => {
    const initialize = async () => {
      setIsInitializing(true);
      setError(null);

      try {
        const result = await initializeApi();

        if (result.connected && result.token) {
          setBackendConnected(true);
          setAuthToken(result.token);
          console.log("✅ Backend connected:", result.health);
        } else {
          setBackendConnected(false);
          setError("Failed to connect to backend. Make sure the Python server is running.");
        }
      } catch (err) {
        setBackendConnected(false);
        setError(`Backend initialization failed: ${err}`);
        console.error("Initialization error:", err);
      } finally {
        setIsInitializing(false);
      }
    };

    initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Handle adding multiple files
  const handleFilesAdded = (files: QueuedFile[]) => {
    files.forEach((file) => addFile(file));
  };

  // Open file in folder (Tauri API)
  const handleOpenFolder = async (filePath: string) => {
    try {
      // TODO: Implement with Tauri shell API
      alert(`Would open folder for: ${filePath}`);
    } catch (err) {
      console.error("Failed to open folder:", err);
    }
  };

  // Process transcription queue
  const processQueue = async () => {
    const pendingFiles = Array.from(state.queue.values()).filter(
      (file) => file.status === "pending"
    );

    if (pendingFiles.length === 0) {
      return;
    }

    // Process files sequentially
    for (const file of pendingFiles) {
      try {
        // Update status to processing
        updateFile(file.id, { status: "processing", progress: 0 } as QueuedFile);
        setCurrentlyProcessing(file.id);

        // Call transcription API
        const response = await transcribeVideo({
          file_path: file.path,
          model_size: "turbo",
          beam_size: 5,
        });

        // Update to completed with outputs
        updateFile(file.id, {
          status: "completed",
          outputs: response.output_files,
        } as QueuedFile);

        console.log(`✅ Transcription complete: ${file.name}`);
      } catch (err) {
        // Update to failed with error
        const errorMessage = err instanceof Error ? err.message : String(err);
        updateFile(file.id, {
          status: "failed",
          error: errorMessage,
        } as QueuedFile);

        console.error(`❌ Transcription failed for ${file.name}:`, err);
      }
    }

    setCurrentlyProcessing(null);
  };

  // Get files as array for display
  const filesArray = Array.from(state.queue.values());
  const pendingCount = filesArray.filter((f) => f.status === "pending").length;
  const processingCount = filesArray.filter((f) => f.status === "processing").length;
  const completedCount = filesArray.filter((f) => f.status === "completed").length;
  const failedCount = filesArray.filter((f) => f.status === "failed").length;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Video Transcriber</h1>

            {/* Connection Status */}
            <div className="flex items-center gap-3">
              {isInitializing ? (
                <span className="text-sm text-gray-500">Connecting...</span>
              ) : state.backendConnected ? (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  Backend Connected
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <div className="w-2 h-2 bg-red-500 rounded-full" />
                  Backend Disconnected
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
            <p className="text-sm text-red-600 mt-2">
              Start the backend: <code className="bg-red-100 px-2 py-1 rounded">cd backend && ./scripts/dev.sh</code>
            </p>
          </div>
        )}

        {/* File Upload Section */}
        <section className="mb-8">
          <FileUpload
            onFilesAdded={handleFilesAdded}
            disabled={!state.backendConnected || isInitializing}
          />
        </section>

        {/* Queue Stats */}
        {filesArray.length > 0 && (
          <section className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex gap-6 text-sm">
                {pendingCount > 0 && (
                  <span className="text-gray-600">
                    <span className="font-medium">{pendingCount}</span> pending
                  </span>
                )}
                {processingCount > 0 && (
                  <span className="text-blue-600">
                    <span className="font-medium">{processingCount}</span> processing
                  </span>
                )}
                {completedCount > 0 && (
                  <span className="text-green-600">
                    <span className="font-medium">{completedCount}</span> completed
                  </span>
                )}
                {failedCount > 0 && (
                  <span className="text-red-600">
                    <span className="font-medium">{failedCount}</span> failed
                  </span>
                )}
              </div>

              <div className="flex gap-2">
                {pendingCount > 0 && state.backendConnected && processingCount === 0 && (
                  <button
                    onClick={processQueue}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    Start Transcription
                  </button>
                )}

                {(completedCount > 0 || failedCount > 0) && (
                  <button
                    onClick={clearCompleted}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                  >
                    Clear Completed
                  </button>
                )}
              </div>
            </div>
          </section>
        )}

        {/* File Queue */}
        <section>
          <FileQueue files={filesArray} onRemove={removeFile} onOpenFolder={handleOpenFolder} />
        </section>
      </main>
    </div>
  );
}

export default App;
