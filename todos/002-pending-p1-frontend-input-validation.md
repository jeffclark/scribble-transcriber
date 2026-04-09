---
status: pending
priority: p1
issue_id: "002"
tags: [code-review, security, typescript, frontend]
dependencies: ["001"]
---

# Missing Frontend Input Validation

## Problem Statement

The TypeScript frontend passes `folderPath` directly to the Rust backend without client-side validation. While server-side validation is critical (see issue #001), defense-in-depth requires client-side checks to catch malformed input early and provide better user feedback.

**Location**: `frontend/src/App.tsx` (lines 86-102, handleOpenFolder function)

**Why It Matters**: Client-side validation provides the first line of defense against malicious or malformed input, reduces unnecessary backend calls, and improves user experience with immediate feedback.

## Findings

### From Security Sentinel Agent

**Current Vulnerable Code**:
```typescript
const handleOpenFolder = async (folderPath: string) => {
  try {
    console.log(`🔍 Attempting to open folder: ${folderPath}`);
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('open_folder', { path: folderPath });
    console.log(`✅ Opened folder: ${folderPath}`);
  } catch (err) {
    console.error("❌ Failed to open folder:", err);
    console.error("Error details:", err);
    alert(`Could not open folder automatically. Path: ${folderPath}`);
  }
};
```

**Issues**:
- No null/empty checks
- No suspicious pattern detection
- Generic error type without type checking
- Double error logging
- Alert exposes path (information disclosure)

### From Pattern Recognition Agent

**Additional Findings**:
- Inconsistent with other error handling in the codebase (see line 171 for better pattern)
- Dynamic import adds unnecessary overhead
- Should use static import like FileUpload.tsx does

## Proposed Solutions

### Solution 1: Basic Client-Side Validation (Recommended)

**Implementation**:
```typescript
import { invoke } from '@tauri-apps/api/core';

const handleOpenFolder = async (folderPath: string) => {
  try {
    // Input validation
    if (!folderPath || folderPath.trim() === '') {
      console.error("Invalid folder path: empty or null");
      return;
    }

    // Basic sanity checks to catch obvious attack attempts
    const suspiciousPatterns = [
      /[;&|`$()]/,  // Shell metacharacters
      /\.\./,        // Directory traversal
      /\x00/,        // Null bytes
    ];

    for (const pattern of suspiciousPatterns) {
      if (pattern.test(folderPath)) {
        console.error("Invalid folder path: contains suspicious characters");
        alert("Invalid folder path");
        return;
      }
    }

    console.log(`Attempting to open folder: ${folderPath}`);
    await invoke('open_folder', { path: folderPath });
    console.log(`Successfully opened folder`);
  } catch (err) {
    console.error("Failed to open folder:", err);
    // Don't expose path in user-facing message
    alert("Could not open folder. Please check the path and try again.");
  }
};
```

**Pros**:
- Catches common attacks early
- Reduces backend load
- Better user feedback
- Defense in depth
- Static import improves performance

**Cons**:
- Client-side checks can be bypassed (why backend validation is critical)
- Adds ~15 lines of code

**Effort**: 30 minutes
**Risk**: Low - purely additive

---

### Solution 2: Type-Safe Error Handling (Best Practice)

**Implementation**:
```typescript
import { invoke } from '@tauri-apps/api/core';

interface OpenFolderError {
  message: string;
  code?: string;
}

const validatePath = (path: string): boolean => {
  if (!path?.trim()) return false;

  const dangerous = /[;&|`$()]/;
  const traversal = /\.\./;
  const nullByte = /\x00/;

  return !(dangerous.test(path) || traversal.test(path) || nullByte.test(path));
};

const handleOpenFolder = async (folderPath: string) => {
  try {
    if (!validatePath(folderPath)) {
      console.error("Invalid folder path format");
      alert("Invalid folder path");
      return;
    }

    await invoke('open_folder', { path: folderPath });
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err);
    console.error("Failed to open folder:", errorMessage);

    // User-friendly error without exposing internals
    if (errorMessage.includes("does not exist")) {
      alert("The folder was not found. It may have been moved or deleted.");
    } else if (errorMessage.includes("not a directory")) {
      alert("The path is not a valid folder.");
    } else {
      alert("Could not open folder. Please try again.");
    }
  }
};
```

**Pros**:
- Type-safe error handling (matches line 171 pattern)
- Extracted validation function (reusable)
- User-friendly error messages
- Consistent with codebase conventions

**Cons**:
- More code than Solution 1

**Effort**: 45 minutes
**Risk**: Low

---

## Recommended Action

**Implement Solution 2 (Type-Safe Error Handling)** after backend validation (issue #001) is complete.

This provides defense in depth and aligns with the project's existing error handling patterns.

## Technical Details

**Affected Files**:
- `frontend/src/App.tsx` (lines 86-102)

**Related Files**:
- `frontend/src/components/FileQueue.tsx` (lines 172-191) - calls handleOpenFolder

**Testing Requirements**:
- Test with valid paths
- Test with empty/null paths
- Test with paths containing shell metacharacters
- Test with paths containing `..`
- Test with paths containing null bytes
- Verify error messages are user-friendly

## Acceptance Criteria

- [ ] Empty/null path validation implemented
- [ ] Suspicious pattern detection implemented
- [ ] Type-safe error handling implemented
- [ ] User-friendly error messages (no internal details exposed)
- [ ] Static import replaces dynamic import
- [ ] Consistent with codebase error handling patterns (line 171)
- [ ] No alert with path exposure
- [ ] Tests added for validation logic

## Work Log

### 2026-02-13
- **Discovery**: Security review identified missing client-side validation
- **Assessment**: High priority - complements backend validation (issue #001)
- **Decision**: Implement after backend validation for defense in depth
- **Implementation**: Applied Solution 2 (Type-Safe Error Handling)
  - Added static import: `import { invoke } from "@tauri-apps/api/core"`
  - Created validatePath() helper function
  - Added validation for empty/null paths
  - Added suspicious pattern detection (shell metacharacters, .., null bytes)
  - Implemented type-safe error handling (matches line 171 pattern)
  - User-friendly error messages without path exposure
  - Removed excessive logging (emojis, duplicate logs)
- **Status**: ✅ Implemented, awaiting testing
- **Next**: Test validation with valid paths, invalid paths, and injection attempts

## Resources

- **Frontend Security Best Practices**: https://owasp.org/www-project-web-security-testing-guide/
- **Input Validation Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- **Example**: App.tsx line 171 shows proper error handling pattern
