/**
 * API client for backend transcription service
 * Handles all HTTP communication with Python FastAPI backend
 */

import type {
  TranscribeRequest,
  TranscribeResponse,
  HealthResponse,
  TokenResponse,
} from "../types/transcription";

const API_BASE_URL = "http://localhost:8765";

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
  const response = await fetch(`${API_BASE_URL}/token`);

  if (!response.ok) {
    throw new Error(`Failed to fetch token: ${response.statusText}`);
  }

  const data: TokenResponse = await response.json();
  authToken = data.token;
  return data.token;
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }

  return response.json();
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

  const response = await fetch(`${API_BASE_URL}/transcribe`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Auth-Token": authToken,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || response.statusText;
    throw new Error(`Transcription failed: ${errorMessage}`);
  }

  return response.json();
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
}> {
  try {
    // Test connection
    const health = await checkHealth();

    // Fetch auth token
    const token = await fetchAuthToken();

    return {
      connected: true,
      token,
      health,
    };
  } catch (error) {
    console.error("API initialization failed:", error);
    return {
      connected: false,
      token: null,
      health: null,
    };
  }
}
