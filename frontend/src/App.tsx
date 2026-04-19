/**
 * Main App component
 * Brings together all components and manages application state
 */

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import FileUpload from "./components/FileUpload";
import FileQueue from "./components/FileQueue";
import { usePersistedQueue } from "./hooks/usePersistedQueue";
import { initializeApi, setAuthToken as setApiAuthToken } from "./api/transcription";
import { transcribeWithProgress } from "./hooks/useTranscriptionProgress";
import type { QueuedFile } from "./types/transcription";

/**
 * Validates folder path for security
 * Checks for shell metacharacters, directory traversal, and null bytes
 */
const validatePath = (path: string): boolean => {
  if (!path?.trim()) return false;

  const dangerous = /[;&|`$()]/;  // Shell metacharacters
  const traversal = /\.\./;        // Directory traversal
  const nullByte = /\x00/;         // Null bytes

  return !(dangerous.test(path) || traversal.test(path) || nullByte.test(path));
};

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
    clearAll,
  } = usePersistedQueue();

  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize API connection on mount, retrying until connected
  useEffect(() => {
    let cancelled = false;

    const initialize = async () => {
      setIsInitializing(true);
      setError(null);

      while (!cancelled) {
        try {
          const result = await initializeApi();
          if (result.connected && result.token) {
            if (!cancelled) {
              setBackendConnected(true);
              setAuthToken(result.token);
              setApiAuthToken(result.token);
              setError(null);
              setIsInitializing(false);
            }
            return;
          }
        } catch (err) {
          console.log("Connection attempt failed, retrying...", err);
        }

        if (!cancelled) {
          await new Promise(resolve => setTimeout(resolve, 1500));
        }
      }
    };

    initialize();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debug: Log state changes
  useEffect(() => {
    console.log("📊 State updated:", {
      backendConnected: state.backendConnected,
      hasToken: !!state.authToken,
      queueSize: state.queue.size
    });
  }, [state.backendConnected, state.authToken, state.queue.size]);

  // Handle adding multiple files
  const handleFilesAdded = (files: QueuedFile[]) => {
    files.forEach((file) => addFile(file));
  };

  // Handle adding a YouTube URL
  const handleYoutubeUrlAdded = (file: QueuedFile) => {
    addFile(file);
  };

  // Open folder in native file explorer (Custom Tauri Command)
  const handleOpenFolder = async (folderPath: string) => {
    try {
      // Client-side validation (defense in depth)
      if (!validatePath(folderPath)) {
        console.error("Invalid folder path format");
        alert("Invalid folder path");
        return;
      }

      // Call our custom Rust command (with server-side validation)
      await invoke('open_folder', { path: folderPath });
    } catch (err) {
      // Type-safe error handling
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error("Failed to open folder:", errorMessage);

      // User-friendly error messages based on error type
      if (errorMessage.includes("does not exist")) {
        alert("The folder was not found. It may have been moved or deleted.");
      } else if (errorMessage.includes("not a directory")) {
        alert("The path is not a valid folder.");
      } else if (errorMessage.includes("Invalid path")) {
        alert("The folder path is invalid.");
      } else {
        alert("Could not open folder. Please try again.");
      }
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

    // Ensure API module has the auth token
    if (!state.authToken) {
      console.error("No auth token available");
      return;
    }

    // Process files sequentially
    for (const file of pendingFiles) {
      try {
        // Update status to processing with 0% progress
        updateFile(file.id, {
          status: "processing",
          progress: 0,
          progressMessage: "Starting transcription..."
        } as QueuedFile);
        setCurrentlyProcessing(file.id);

        console.log(`🎬 Starting transcription: ${file.name}`);

        // Use SSE for real-time progress updates
        await transcribeWithProgress({
          filePath: file.source === "file" ? file.path : undefined,
          youtubeUrl: file.source === "youtube" ? file.youtubeUrl : undefined,
          modelSize: "base",  // Changed from "turbo" to "base" for faster CPU processing
          beamSize: 5,
          authToken: state.authToken,

          // onProgress callback - update progress bar
          onProgress: (progress, message, segmentCount, estimatedTotal) => {
            console.log(`[${file.name}] ${progress}% - ${message}${segmentCount ? ` (${segmentCount} segments)` : ''}`);
            updateFile(file.id, {
              status: "processing",
              progress,
              progressMessage: message,
              segmentCount: segmentCount,
              estimatedTotalSegments: estimatedTotal
            } as QueuedFile);
          },

          // onComplete callback - mark as completed
          onComplete: (result) => {
            console.log(`✅ Transcription complete: ${file.name}`);
            updateFile(file.id, {
              status: "completed",
              outputs: result.output_files,
            } as QueuedFile);
          },

          // onError callback - mark as failed
          onError: (error) => {
            console.error(`❌ Transcription failed for ${file.name}:`, error);
            updateFile(file.id, {
              status: "failed",
              error,
            } as QueuedFile);
          }
        });

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
            <div className="flex items-center gap-3">
              <img src="/icon.png" alt="Scribble" className="w-8 h-8" />
              <h1 className="text-2xl font-bold text-gray-900">Scribble</h1>
            </div>

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
          </div>
        )}

        {/* File Upload Section */}
        <section className="mb-8">
          <FileUpload
            onFilesAdded={handleFilesAdded}
            onYoutubeUrlAdded={handleYoutubeUrlAdded}
            authToken={state.authToken}
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

                {filesArray.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                    title="Remove all files from queue"
                  >
                    Clear All
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
