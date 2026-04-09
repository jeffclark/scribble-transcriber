---
module: Frontend State Management
date: 2026-02-13
problem_type: developer_experience
component: development_workflow
symptoms:
  - "Backend connected successfully but UI showed 'Backend Disconnected'"
  - "Files selected in native dialog didn't appear in queue"
  - "Console logs showed successful API calls but state didn't update"
  - "isMountedRef.current was false during component lifecycle"
root_cause: logic_error
resolution_type: code_fix
severity: medium
tags: [react, strict-mode, mount-guards, tauri, state-management, useref]
---

# Troubleshooting: React Strict Mode Mount Guards Blocking State Updates

## Problem
In React Strict Mode (development), mount guard checks using `isMountedRef.current` were blocking state updates in a Tauri app. This caused the UI to not reflect successful backend connections and prevented files from appearing in the upload queue despite being successfully selected.

## Environment
- Module: Frontend State Management (React + Tauri)
- React Version: 18.2.0
- TypeScript: 5.3.3
- Tauri: 2.0.0
- Affected Components: `usePersistedQueue` hook, file upload handling
- Date: 2026-02-13

## Symptoms
- Backend API initialization succeeded and returned auth token, but UI showed "Backend Disconnected"
- Native file dialog opened successfully and user selected files, but files didn't appear in queue
- Console logs showed `onFilesAdded` being called successfully with valid file objects
- State updates appeared to be blocked silently - no errors thrown
- Issue only occurred in development mode with React Strict Mode enabled

## What Didn't Work

**Attempted Solution 1:** Tried using HTML file input in browser mode
- **Why it failed:** Browser security restrictions prevented access to full file paths needed for backend transcription

**Attempted Solution 2:** Switched to Tauri native file dialog
- **Why it failed:** Dialog worked and returned file paths, but files still didn't appear in queue due to underlying state update issue

**Attempted Solution 3:** Added extensive debugging with alert() calls
- **Why it failed:** This revealed the issue but wasn't a fix - showed that file processing completed successfully but state wasn't updating

## Solution

Removed `isMountedRef.current` guard checks from state setter functions since React's `setState` is safe to call even after unmount.

**Code changes:**

```typescript
// Before (broken):
// frontend/src/hooks/usePersistedQueue.ts

const addFile = (file: QueuedFile) => {
  if (!isMountedRef.current) return;  // ❌ Blocks updates during Strict Mode remount

  setState((prev) => {
    const newQueue = new Map(prev.queue);
    newQueue.set(file.id, file);
    return { ...prev, queue: newQueue };
  });
};

const setBackendConnected = (connected: boolean) => {
  if (!isMountedRef.current) return;  // ❌ Blocks updates during Strict Mode remount

  setState((prev) => ({ ...prev, backendConnected: connected }));
};

// After (fixed):
const addFile = (file: QueuedFile) => {
  // Note: No mount check here - setState is safe even after unmount
  setState((prev) => {
    const newQueue = new Map(prev.queue);
    newQueue.set(file.id, file);
    return { ...prev, queue: newQueue };
  });
};

const setBackendConnected = (connected: boolean) => {
  // Note: No mount check here - setState is safe even after unmount
  setState((prev) => ({ ...prev, backendConnected: connected }));
};
```

**Additional fixes applied:**
- Removed mount guards from `setAuthToken`, `setCurrentlyProcessing`, and `clearCompleted` functions
- Kept mount guards only on functions that perform actual side effects (like `removeFile`, `updateFile` which modify external state)
- Added comments explaining why mount checks were removed

## Why This Works

1. **Root Cause**: React Strict Mode deliberately mounts components twice in development to help detect side effects. During this process:
   - Component mounts → `isMountedRef.current = true`
   - Component unmounts (Strict Mode) → `isMountedRef.current = false`
   - Component remounts → `isMountedRef.current = true` (but setState might be called before this)

2. **Why the solution works**: React's `setState` is designed to be safe to call even after a component unmounts. The framework simply ignores updates for unmounted components. Mount guards are unnecessary for `setState` and actively harmful in Strict Mode.

3. **When to use mount guards**: Only use `isMountedRef` checks for actual cleanup of side effects:
   - Canceling network requests
   - Clearing timers/intervals
   - Unsubscribing from events
   - Other cleanup that prevents memory leaks

   **Never** use mount guards with `setState` - React handles this internally.

## Prevention

To avoid this problem in future React development:

- **Don't use mount guards with setState**: React's setState is safe after unmount. Mount guards are unnecessary and break in Strict Mode.

- **Understand React Strict Mode behavior**: In development, Strict Mode mounts → unmounts → remounts components to surface side effect issues. This is intentional.

- **Only use cleanup for side effects**: Use `useEffect` cleanup for subscriptions, timers, and async operations - not for state updates.

- **Test in production mode**: `NODE_ENV=production npm run build` to verify behavior without Strict Mode if issues are suspected.

- **Pattern to follow**:
  ```typescript
  // ✅ CORRECT: No mount guard for setState
  const updateState = (value) => {
    setState(value);
  };

  // ✅ CORRECT: Cleanup for side effects
  useEffect(() => {
    const subscription = api.subscribe();
    return () => subscription.unsubscribe();
  }, []);

  // ❌ WRONG: Mount guard with setState
  const updateState = (value) => {
    if (!isMountedRef.current) return;
    setState(value);
  };
  ```

## Related Issues

No related issues documented yet.

## Files Modified

- `frontend/src/hooks/usePersistedQueue.ts` - Removed mount guards from state setters
- `frontend/src/components/FileUpload.tsx` - Switched to Tauri native dialog (unrelated but part of debugging)
- `frontend/src/App.tsx` - Added explicit token refresh logic (unrelated but discovered during same session)
