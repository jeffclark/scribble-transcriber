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
    // Note: No mount check here - setState is safe even after unmount
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
    // Note: No mount check here - setState is safe even after unmount
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
    // Note: No mount check here - setState is safe even after unmount
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
    // Note: No mount check here - setState is safe even after unmount
    setState((prev) => ({ ...prev, backendConnected: connected }));
  };

  /**
   * Set auth token
   */
  const setAuthToken = (token: string | null) => {
    // Note: No mount check here - setState is safe even after unmount
    setState((prev) => ({ ...prev, authToken: token }));
  };

  /**
   * Set currently processing file
   */
  const setCurrentlyProcessing = (id: string | null) => {
    // Note: No mount check here - setState is safe even after unmount
    setState((prev) => ({ ...prev, currentlyProcessing: id }));
  };

  /**
   * Clear completed and failed files
   */
  const clearCompleted = () => {
    // Note: No mount check here - setState is safe even after unmount
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

  /**
   * Clear all files from queue (including processing)
   * Completely resets the queue state
   */
  const clearAll = () => {
    // Note: No mount check here - setState is safe even after unmount
    setState((prev) => ({
      ...prev,
      queue: new Map(),
      currentlyProcessing: null,
    }));
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
    clearAll,
    isMounted: isMountedRef,
  };
}
