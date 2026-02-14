/**
 * TypeScript types for transcription with discriminated unions
 * Following research insights for type-safe state management
 */

// File state using discriminated unions for compile-time safety
export type QueuedFile =
  | {
      status: "pending";
      id: string;
      name: string;
      path: string;
      size: number;
    }
  | {
      status: "processing";
      id: string;
      name: string;
      path: string;
      size: number;
      progress: number;
      progressMessage?: string;  // Optional stage message
      segmentCount?: number;  // Number of segments processed so far
      estimatedTotalSegments?: number;  // Estimated total segments
    }
  | {
      status: "completed";
      id: string;
      name: string;
      path: string;
      size: number;
      outputs: OutputFiles;
    }
  | {
      status: "failed";
      id: string;
      name: string;
      path: string;
      size: number;
      error: string;
    };

export type OutputFiles = {
  json: string;
  txt: string;
};

// Type guards for runtime checking
export function isPending(file: QueuedFile): file is Extract<QueuedFile, { status: "pending" }> {
  return file.status === "pending";
}

export function isProcessing(file: QueuedFile): file is Extract<QueuedFile, { status: "processing" }> {
  return file.status === "processing";
}

export function isCompleted(file: QueuedFile): file is Extract<QueuedFile, { status: "completed" }> {
  return file.status === "completed";
}

export function isFailed(file: QueuedFile): file is Extract<QueuedFile, { status: "failed" }> {
  return file.status === "failed";
}

// Application state with Map-based single source of truth
export type AppState = {
  queue: Map<string, QueuedFile>;
  currentlyProcessing: string | null;
  backendConnected: boolean;
  authToken: string | null;
};

// Serialized state for localStorage
export type SerializedState = {
  queue: [string, QueuedFile][];
  currentlyProcessing: string | null;
  backendConnected: boolean;
  authToken: string | null;
};

// API types matching backend Pydantic models

export type TranscribeRequest = {
  file_path: string;
  model_size?: string;
  language?: string | null;
  beam_size?: number;
};

export type TranscriptionSegment = {
  id: number;
  start: number;
  end: number;
  text: string;
};

export type TranscriptionMetadata = {
  source_file: string;
  transcription_date: string;
  model: string;
  device: string;
  language: string;
  language_probability: number;
  duration_seconds: number;
};

export type TranscribeResponse = {
  metadata: TranscriptionMetadata;
  segments: TranscriptionSegment[];
  output_files: Record<string, string>;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  initialized: boolean;
  model_loaded: boolean;
  device: string;
  model_size: string;
};

export type TokenResponse = {
  token: string;
};

// Helper function for exhaustive pattern matching
export function getFileStatusColor(file: QueuedFile): string {
  switch (file.status) {
    case "pending":
      return "text-gray-600";
    case "processing":
      return "text-blue-600";
    case "completed":
      return "text-green-600";
    case "failed":
      return "text-red-600";
    // TypeScript ensures all cases are covered
  }
}

export function getFileStatusBgColor(file: QueuedFile): string {
  switch (file.status) {
    case "pending":
      return "bg-gray-100";
    case "processing":
      return "bg-blue-100";
    case "completed":
      return "bg-green-100";
    case "failed":
      return "bg-red-100";
  }
}
