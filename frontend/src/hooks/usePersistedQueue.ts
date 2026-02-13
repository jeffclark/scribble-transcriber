/**
 * Persisted queue state management with localStorage
 * Following research insights for crash recovery and race condition prevention
 */

import { useEffect, useState, useRef } from "react";
import type { AppState, QueuedFile, SerializedState } from "../types/transcription";

const STORAGE_KEY = "transcription-queue";

/**
 * Custom hook for persisted queue state with localStorage
 *
 * Features:
 * - Automatic persistence to localStorage on every state change
 * - Crash recovery (loads state on mount)
 * - Mount/unmount guards to prevent race conditions
 */
export function usePersistedQueue() {
  // Load from localStorage on mount
  const [state, setState] = useState<AppState>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: SerializedState = JSON.parse(saved);
        return {
          queue: new Map(parsed.queue),
          currentlyProcessing: parsed.currentlyProcessing,
          backendConnected: parsed.backendConnected,
          authToken: parsed.authToken,
        };
      }
    } catch (e) {
      console.error("Failed to load persisted state:", e);
    }

    // Default state
    return {
      queue: new Map(),
      currentlyProcessing: null,
      backendConnected: false,
      authToken: null,
    };
  });

  // Track if component is mounted to prevent race conditions
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Save to localStorage on every state change
  useEffect(() => {
    try {
      const serialized: SerializedState = {
        queue: Array.from(state.queue.entries()),
        currentlyProcessing: state.currentlyProcessing,
        backendConnected: state.backendConnected,
        authToken: state.authToken,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(serialized));
    } catch (e) {
      console.error("Failed to persist state:", e);
    }
  }, [state]);

  /**
   * Add file to queue
   */
  const addFile = (file: QueuedFile) => {
    if (!isMountedRef.current) return;

    setState((prev) => {
      const newQueue = new Map(prev.queue);
      newQueue.set(file.id, file);
      return { ...prev, queue: newQueue };
    });
  };

  /**
   * Remove file from queue
   */
  const removeFile = (id: string) => {
    if (!isMountedRef.current) return;

    setState((prev) => {
      const newQueue = new Map(prev.queue);
      newQueue.delete(id);
      return { ...prev, queue: newQueue };
    });
  };

  /**
   * Update file in queue (immutable update)
   */
  const updateFile = (id: string, updates: Partial<QueuedFile>) => {
    if (!isMountedRef.current) return;

    setState((prev) => {
      const file = prev.queue.get(id);
      if (!file) return prev;

      const updatedFile = { ...file, ...updates } as QueuedFile;
      const newQueue = new Map(prev.queue);
      newQueue.set(id, updatedFile);

      return { ...prev, queue: newQueue };
    });
  };

  /**
   * Set backend connection status
   */
  const setBackendConnected = (connected: boolean) => {
    if (!isMountedRef.current) return;

    setState((prev) => ({ ...prev, backendConnected: connected }));
  };

  /**
   * Set auth token
   */
  const setAuthToken = (token: string | null) => {
    if (!isMountedRef.current) return;

    setState((prev) => ({ ...prev, authToken: token }));
  };

  /**
   * Set currently processing file
   */
  const setCurrentlyProcessing = (id: string | null) => {
    if (!isMountedRef.current) return;

    setState((prev) => ({ ...prev, currentlyProcessing: id }));
  };

  /**
   * Clear completed and failed files
   */
  const clearCompleted = () => {
    if (!isMountedRef.current) return;

    setState((prev) => {
      const newQueue = new Map(prev.queue);
      for (const [id, file] of newQueue.entries()) {
        if (file.status === "completed" || file.status === "failed") {
          newQueue.delete(id);
        }
      }
      return { ...prev, queue: newQueue };
    });
  };

  return {
    state,
    addFile,
    removeFile,
    updateFile,
    setBackendConnected,
    setAuthToken,
    setCurrentlyProcessing,
    clearCompleted,
    isMounted: isMountedRef,
  };
}
