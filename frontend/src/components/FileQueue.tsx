/**
 * File queue display component
 * Shows all queued files with status, progress, and actions
 */

import type { QueuedFile } from "../types/transcription";
import { getFileStatusColor, getFileStatusBgColor } from "../types/transcription";

interface FileQueueProps {
  files: QueuedFile[];
  onRemove: (id: string) => void;
  onOpenFolder: (path: string) => void;
}

export default function FileQueue({ files, onRemove, onOpenFolder }: FileQueueProps) {
  if (files.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-lg">No files in queue</p>
        <p className="text-sm mt-2">Add videos above to get started</p>
      </div>
    );
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const getStatusIcon = (file: QueuedFile) => {
    switch (file.status) {
      case "pending":
        return (
          <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "processing":
        return (
          <svg
            className="w-5 h-5 text-blue-500 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        );
      case "completed":
        return (
          <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "failed":
        return (
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
    }
  };

  return (
    <div className="space-y-2">
      {files.map((file) => (
        <div
          key={file.id}
          className={`
            rounded-lg p-4 flex items-center gap-4
            ${getFileStatusBgColor(file)} border border-gray-200
          `}
        >
          {/* Status Icon */}
          <div className="flex-shrink-0">{getStatusIcon(file)}</div>

          {/* File Info */}
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{file.name}</p>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
              <span>{formatFileSize(file.size)}</span>
              <span className={`font-medium ${getFileStatusColor(file)}`}>
                {file.status.toUpperCase()}
              </span>
            </div>

            {/* Progress Bar */}
            {file.status === "processing" && (
              <div className="mt-2">
                {/* Progress percentage and segment count */}
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-blue-600">{file.progress}%</span>
                  <span className="text-gray-500">
                    {file.progressMessage || "Processing..."}
                    {file.segmentCount && file.estimatedTotalSegments &&
                      ` • ${file.segmentCount} / ~${file.estimatedTotalSegments} segments`}
                    {file.segmentCount && !file.estimatedTotalSegments &&
                      ` • ${file.segmentCount} segments`}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300 ease-out"
                    style={{ width: `${file.progress}%` }}
                  />
                </div>

                {/* Stage message with timestamp */}
                {file.progressMessage && (
                  <div className="flex justify-between items-center mt-1">
                    <p className="text-xs text-gray-500">{file.progressMessage}</p>
                    <p className="text-xs text-gray-400">
                      {new Date().toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {file.status === "failed" && (
              <p className="text-sm text-red-600 mt-2">{file.error}</p>
            )}

            {/* Output Files */}
            {file.status === "completed" && (
              <div className="text-xs text-gray-500 mt-2">
                <span>✓ JSON and TXT outputs created</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex-shrink-0 flex gap-2">
            {file.status === "pending" && (
              <button
                onClick={() => onRemove(file.id)}
                className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                title="Remove from queue"
              >
                Remove
              </button>
            )}

            {file.status === "completed" && (
              <button
                onClick={() => {
                  // Extract directory from first output file path
                  const outputPath = file.outputs?.json || file.outputs?.txt;
                  if (outputPath) {
                    // Get directory containing the output files
                    const directory = outputPath.substring(0, outputPath.lastIndexOf('/'));
                    onOpenFolder(directory);
                  } else {
                    // Fallback: use video file directory (outputs should be there)
                    const videoDir = file.path.substring(0, file.path.lastIndexOf('/'));
                    onOpenFolder(videoDir);
                  }
                }}
                className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
                title="Open folder containing transcription files"
              >
                Open Folder
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
