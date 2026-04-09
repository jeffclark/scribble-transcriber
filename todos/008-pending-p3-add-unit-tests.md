---
status: pending
priority: p3
issue_id: "008"
tags: [code-review, testing, rust, typescript]
dependencies: ["001", "005"]
---

# Add Unit Tests for open_folder Command

## Problem Statement

The `open_folder` Tauri command has zero test coverage. No tests exist for:
- Platform-specific command selection
- Error handling for invalid paths
- Error handling for permission denied
- Error handling for non-existent paths
- Frontend error handling and fallback

**Why It Matters**: Without tests, refactoring is risky and regressions can slip into production. Tests provide confidence when making changes and document expected behavior.

## Findings

### From Pattern Recognition Agent

**Current Test Coverage**: 0%

**Missing Test Coverage**:
1. Platform-specific command selection
2. Error handling for invalid paths
3. Error handling for permission denied
4. Error handling for non-existent paths
5. Frontend error handling and fallback

**Testability Issues**:
- No dependency injection (hard to mock Command::new)
- No abstraction layer on frontend
- Dynamic import makes mocking harder

## Proposed Solutions

### Solution 1: Rust Unit Tests with Mocking (Recommended)

**Implementation**:
```rust
// src/commands.rs
#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_valid_directory() {
        // Create temp directory
        let temp_dir = std::env::temp_dir();

        // Should succeed for valid directory
        let result = open_folder(temp_dir.to_string_lossy().to_string());
        assert!(result.is_ok());
    }

    #[test]
    fn test_nonexistent_directory() {
        let result = open_folder("/nonexistent/path/12345".to_string());
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_file_not_directory() {
        // Create temp file
        let temp_file = std::env::temp_dir().join("test_file.txt");
        std::fs::write(&temp_file, "test").unwrap();

        let result = open_folder(temp_file.to_string_lossy().to_string());
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not a directory"));

        // Cleanup
        std::fs::remove_file(temp_file).ok();
    }

    #[test]
    fn test_command_injection_attempt() {
        let malicious = "/tmp; rm -rf ~/*";
        let result = open_folder(malicious.to_string());

        // Should fail validation before reaching spawn
        assert!(result.is_err());
    }

    #[test]
    fn test_path_traversal_attempt() {
        let traversal = "/tmp/../../../etc/passwd";
        let result = open_folder(traversal.to_string());

        // Canonicalization should normalize this
        // Should either succeed (if /etc/passwd dir exists) or fail gracefully
        assert!(result.is_ok() || result.is_err());
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_platform_specific_command() {
        // This test only runs on macOS
        // Could mock Command to verify "open" is used
    }
}
```

**Pros**:
- Tests path validation logic
- Documents expected behavior
- Catches regressions
- Runs in CI automatically

**Cons**:
- Can't easily test actual folder opening (requires mocking)
- Platform-specific tests only run on that platform

**Effort**: 2-3 hours
**Risk**: Low

---

### Solution 2: Integration Tests (End-to-End)

**Implementation**:
```rust
// tests/integration_test.rs
#[cfg(test)]
mod integration_tests {
    use video_transcriber::commands::open_folder;

    #[test]
    #[ignore] // Mark as integration test (slower)
    fn test_opens_actual_folder() {
        let temp_dir = std::env::temp_dir();
        let result = open_folder(temp_dir.to_string_lossy().to_string());

        assert!(result.is_ok());

        // Could check if process was spawned successfully
        // (hard to verify folder actually opened without UI automation)
    }
}
```

**Pros**:
- Tests real behavior
- More confidence

**Cons**:
- Slower
- Requires actual system commands
- Hard to verify in CI

**Effort**: 1-2 hours
**Risk**: Medium (CI environment may not have GUI)

---

### Solution 3: Frontend Unit Tests

**Implementation**:
```typescript
// src/App.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { handleOpenFolder } from './App';

describe('handleOpenFolder', () => {
  it('should invoke open_folder command with path', async () => {
    const mockInvoke = vi.fn().mockResolvedValue(undefined);
    vi.mock('@tauri-apps/api/core', () => ({
      invoke: mockInvoke
    }));

    await handleOpenFolder('/test/path');

    expect(mockInvoke).toHaveBeenCalledWith('open_folder', {
      path: '/test/path'
    });
  });

  it('should log error on failure', async () => {
    const mockInvoke = vi.fn().mockRejectedValue(new Error('Failed'));
    const consoleErrorSpy = vi.spyOn(console, 'error');

    await handleOpenFolder('/test/path');

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Failed to open folder')
    );
  });
});
```

**Pros**:
- Tests frontend integration
- Fast
- No system dependencies

**Cons**:
- Requires Vitest setup
- Doesn't test Rust code

**Effort**: 1 hour
**Risk**: Low

---

## Recommended Action

**Implement Solution 1 (Rust Unit Tests)** after path validation (issue #001) is complete.

This provides the most value by testing the security-critical path validation logic. Add Solution 3 (Frontend Tests) if time permits.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (add #[cfg(test)] module)
- `frontend/src-tauri/tests/` (optional integration tests)
- `frontend/src/App.test.tsx` (optional frontend tests)

**Test Framework**:
- Rust: Built-in test framework (`#[test]`, `cargo test`)
- TypeScript: Vitest (if configured)

**CI Integration**:
```yaml
# .github/workflows/test.yml
- name: Run Rust tests
  run: cd frontend/src-tauri && cargo test

- name: Run frontend tests
  run: cd frontend && npm test
```

## Acceptance Criteria

- [ ] Tests for valid directory path
- [ ] Tests for non-existent directory
- [ ] Tests for file (not directory)
- [ ] Tests for command injection attempts
- [ ] Tests for path traversal attempts
- [ ] All tests pass
- [ ] CI runs tests automatically
- [ ] Code coverage > 80% for commands.rs

## Work Log

### 2026-02-13
- **Discovery**: Pattern recognition agent identified zero test coverage
- **Assessment**: P3 - not urgent but important for long-term maintainability
- **Decision**: Implement after security fixes (issues #001-#003)

## Resources

- **Rust Testing**: https://doc.rust-lang.org/book/ch11-00-testing.html
- **Tauri Testing Guide**: https://tauri.app/v2/develop/tests/
- **Vitest**: https://vitest.dev/
