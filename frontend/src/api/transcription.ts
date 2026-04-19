/**
 * API client for backend transcription service
 * Uses Tauri commands (IPC) to communicate with Python FastAPI backend
 */

import { invoke } from "@tauri-apps/api/core";
import type {
  TranscribeRequest,
  TranscribeResponse,
  HealthResponse,
  YoutubeInfoResponse,
} from "../types/transcription";

// Stored auth token
let authToken: string | null = null;

/**
 * Set authentication token for API requests
 */
export function setAuthToken(token: string) {
  authToken = token;
}

/**
 * Get current authentication token
 */
export function getAuthToken(): string | null {
  return authToken;
}

/**
 * Fetch authentication token from backend
 */
export async function fetchAuthToken(): Promise<string> {
  try {
    console.log("🔑 Fetching auth token via Tauri command");
    const token = await invoke<string>("fetch_auth_token");
    authToken = token;
    console.log(`✅ Auth token received: ${token.substring(0, 12)}...`);
    return token;
  } catch (error) {
    console.error("❌ Failed to fetch auth token:", error);
    throw new Error(`Cannot fetch auth token. Backend may not be running: ${error}`);
  }
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    console.log("🔍 Checking backend health via Tauri command");
    console.log("Invoking command: check_health");
    const data = await invoke<HealthResponse>("check_health");
    console.log("✅ Backend health check successful:", data);
    return data;
  } catch (error) {
    console.error("❌ Backend health check failed:");
    console.error("Error type:", typeof error);
    console.error("Error:", error);
    console.error("Error string:", String(error));
    throw new Error(`Cannot connect to backend: ${JSON.stringify(error)}`);
  }
}

/**
 * Transcribe a video file
 */
export async function transcribeVideo(
  request: TranscribeRequest
): Promise<TranscribeResponse> {
  if (!authToken) {
    throw new Error("Authentication token not set. Call fetchAuthToken() first.");
  }

  try {
    return await invoke<TranscribeResponse>("transcribe_video", {
      filePath: request.file_path,
      modelSize: request.model_size || "turbo",
      language: request.language || null,
      authToken: authToken,
    });
  } catch (error) {
    // If unauthorized, refresh token and retry once
    if (error && typeof error === "string" && error.includes("401")) {
      console.log("Token expired, refreshing...");
      await fetchAuthToken();

      return await invoke<TranscribeResponse>("transcribe_video", {
        filePath: request.file_path,
        modelSize: request.model_size || "turbo",
        language: request.language || null,
        authToken: authToken,
      });
    }

    throw new Error(`Transcription failed: ${error}`);
  }
}

/**
 * Fetch YouTube video info (title, duration) without downloading
 */
export async function fetchYoutubeInfo(
  url: string,
  token: string
): Promise<YoutubeInfoResponse> {
  return await invoke<YoutubeInfoResponse>("fetch_youtube_info", {
    url,
    authToken: token,
  });
}

/**
 * Test backend connection
 */
export async function testConnection(): Promise<boolean> {
  try {
    await checkHealth();
    return true;
  } catch (error) {
    console.error("Backend connection failed:", error);
    return false;
  }
}

/**
 * Initialize API client (fetch token and test connection)
 */
export async function initializeApi(): Promise<{
  connected: boolean;
  token: string | null;
  health: HealthResponse | null;
  error?: string;
}> {
  try {
    console.log("🚀 Initializing API connection via Tauri commands");

    // Test connection
    const health = await checkHealth();
    console.log(`✅ Health check passed. Backend version: ${health.version}, Device: ${health.device}`);

    // Fetch auth token
    const token = await fetchAuthToken();
    console.log("✅ Authentication token acquired");

    return {
      connected: true,
      token,
      health,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("❌ API initialization failed:", errorMessage);
    console.error("Full error:", error);

    return {
      connected: false,
      token: null,
      health: null,
      error: errorMessage,
    };
  }
}
