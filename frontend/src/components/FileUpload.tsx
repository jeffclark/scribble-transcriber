/**
 * File upload component with drag-and-drop support and YouTube URL input
 */

import { useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import type { QueuedFile } from "../types/transcription";
import { fetchYoutubeInfo } from "../api/transcription";

const ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v", ".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac"];
const MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024; // 10GB

const YOUTUBE_URL_PATTERN = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/|embed\/)|youtu\.be\/)[A-Za-z0-9_-]{11}/;

interface FileUploadProps {
  onFilesAdded: (files: QueuedFile[]) => void;
  onYoutubeUrlAdded: (file: QueuedFile) => void;
  authToken: string | null;
  disabled?: boolean;
}

export default function FileUpload({ onFilesAdded, onYoutubeUrlAdded, authToken, disabled = false }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlLoading, setUrlLoading] = useState(false);

  const validateFile = (file: File): string | null => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Invalid file type: ${ext}. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }

    if (file.size > MAX_FILE_SIZE) {
      return `File too large: ${(file.size / (1024 * 1024 * 1024)).toFixed(2)}GB. Max: 10GB`;
    }

    return null;
  };

  const processFiles = (files: FileList) => {
    console.log("📁 processFiles called with FileList:", files);
    console.log("📁 Number of files:", files.length);

    const validFiles: QueuedFile[] = [];
    const errors: string[] = [];

    Array.from(files).forEach((file, index) => {
      console.log(`📄 Processing file ${index + 1}:`, {
        name: file.name,
        size: file.size,
        type: file.type,
        path: (file as any).path
      });

      const error = validateFile(file);

      if (error) {
        console.log(`❌ Validation failed:`, error);
        errors.push(`${file.name}: ${error}`);
      } else {
        console.log(`✅ Validation passed`);
        const queuedFile: QueuedFile = {
          status: "pending",
          id: crypto.randomUUID(),
          name: file.name,
          source: "file",
          path: (file as any).path || file.name, // Tauri provides full path
          size: file.size,
        };
        console.log(`✅ Created queued file:`, queuedFile);
        validFiles.push(queuedFile);
      }
    });

    console.log(`📊 Results: ${validFiles.length} valid, ${errors.length} errors`);

    if (errors.length > 0) {
      alert(`Some files were skipped:\n\n${errors.join("\n")}`);
    }

    if (validFiles.length > 0) {
      console.log(`✅ Calling onFilesAdded with ${validFiles.length} files`);
      onFilesAdded(validFiles);
    } else {
      console.log(`⚠️ No valid files to add`);
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFiles(files);
    }
  };

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    console.log("🖱️ Click handler triggered");
    console.log("🖱️ Disabled:", disabled);

    if (disabled) {
      console.log("⚠️ Upload disabled");
      return;
    }

    try {
      console.log("🖱️ Opening native file dialog...");

      // Use Tauri's native file dialog
      const selected = await open({
        multiple: true,
        filters: [{
          name: "Media Files",
          extensions: ["mp4", "mov", "avi", "mkv", "webm", "flv", "m4v", "m4a", "mp3", "wav", "aac", "ogg", "flac"]
        }]
      });

      console.log("📁 Dialog result:", selected);

      if (!selected) {
        console.log("⚠️ No files selected (user cancelled)");
        return;
      }

      // Convert paths to QueuedFile objects
      const paths = Array.isArray(selected) ? selected : [selected];
      console.log("📁 Selected paths:", paths);

      const validFiles: QueuedFile[] = [];

      for (const path of paths) {
        console.log(`📄 Processing path: ${path}`);

        // Extract filename from path
        const filename = path.split(/[\\/]/).pop() || path;

        const queuedFile: QueuedFile = {
          status: "pending",
          id: crypto.randomUUID(),
          name: filename,
          source: "file",
          path: path,
          size: 0, // We don't have size from dialog, backend will validate
        };

        console.log(`✅ Created queued file:`, queuedFile);
        validFiles.push(queuedFile);
      }

      if (validFiles.length > 0) {
        console.log(`✅ Adding ${validFiles.length} files to queue`);
        onFilesAdded(validFiles);
      }
    } catch (error) {
      console.error("❌ Error opening file dialog:", error);
    }
  };

  const handleAddUrl = async () => {
    const url = urlInput.trim();
    setUrlError(null);

    if (!url) return;

    if (!YOUTUBE_URL_PATTERN.test(url)) {
      setUrlError("Please enter a valid YouTube URL (youtube.com or youtu.be)");
      return;
    }

    if (!authToken) {
      setUrlError("Not connected to backend yet. Please wait and try again.");
      return;
    }

    setUrlLoading(true);
    try {
      const info = await fetchYoutubeInfo(url, authToken);
      const queuedFile: QueuedFile = {
        status: "pending",
        id: crypto.randomUUID(),
        name: info.title,
        source: "youtube",
        youtubeUrl: url,
        size: 0,
      };
      onYoutubeUrlAdded(queuedFile);
      setUrlInput("");
    } catch (err) {
      setUrlError(`Could not fetch video info: ${err}`);
    } finally {
      setUrlLoading(false);
    }
  };

  const handleUrlKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleAddUrl();
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Drag-and-drop zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-gray-50"}
          ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-blue-400 hover:bg-blue-50"}
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <div className="flex flex-col items-center gap-4">
          <svg
            className="w-16 h-16 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>

          <div>
            <p className="text-lg font-medium text-gray-700">
              {isDragging ? "Drop files here" : "Drag & drop video or audio files"}
            </p>
            <p className="text-sm text-gray-500 mt-1">or click to browse</p>
          </div>

          <div className="text-xs text-gray-400 mt-2">
            <p>Supported formats: {ALLOWED_EXTENSIONS.join(", ")}</p>
            <p>Maximum size: 10GB per file</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 border-t border-gray-200" />
        <span className="text-sm text-gray-400">or</span>
        <div className="flex-1 border-t border-gray-200" />
      </div>

      {/* YouTube URL input */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-700">YouTube URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={urlInput}
            onChange={(e) => { setUrlInput(e.target.value); setUrlError(null); }}
            onKeyDown={handleUrlKeyDown}
            disabled={disabled || urlLoading}
            className={`
              flex-1 px-3 py-2 text-sm border rounded-lg outline-none
              transition-colors duration-150
              ${disabled || urlLoading ? "bg-gray-50 text-gray-400 cursor-not-allowed" : "bg-white text-gray-800"}
              ${urlError ? "border-red-400 focus:border-red-500" : "border-gray-300 focus:border-blue-400"}
            `}
          />
          <button
            onClick={handleAddUrl}
            disabled={disabled || urlLoading || !urlInput.trim()}
            className={`
              px-4 py-2 text-sm font-medium rounded-lg transition-colors duration-150
              ${disabled || urlLoading || !urlInput.trim()
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800"}
            `}
          >
            {urlLoading ? "Loading..." : "Add"}
          </button>
        </div>
        {urlError && (
          <p className="text-xs text-red-500">{urlError}</p>
        )}
      </div>
    </div>
  );
}
