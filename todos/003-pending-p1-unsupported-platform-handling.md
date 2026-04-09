---
status: pending
priority: p1
issue_id: "003"
tags: [code-review, rust, tauri, cross-platform]
dependencies: ["001"]
---

# Handle Unsupported Platforms Explicitly

## Problem Statement

The `open_folder` command currently only has implementations for macOS, Windows, and Linux. On other platforms (BSD, Android, iOS, etc.), the code compiles to a no-op that silently succeeds, misleading users into thinking the operation worked when it didn't.

**Location**: `frontend/src-tauri/src/commands.rs:5-28`

**Why It Matters**: Silent failures are confusing for users and difficult to debug. Explicit error messages for unsupported platforms provide clarity and prevent false positives.

## Findings

### From Architecture Strategist Agent

**Current Code Issues**:
```rust
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    { /* ... */ }

    #[cfg(target_os = "windows")]
    { /* ... */ }

    #[cfg(target_os = "linux")]
    { /* ... */ }

    Ok(())  // ❌ Always returns Ok even if no platform matched!
}
```

**Problem**: On FreeBSD, Android, iOS, or other platforms:
- Code compiles successfully
- All three cfg blocks are excluded
- Function immediately returns `Ok(())`
- User thinks folder opened, but nothing happened

### From Pattern Recognition Agent

**Missing Compile-Time Guard**:
No compile-time error or warning for unsupported platforms. The code silently accepts being built for platforms it doesn't support.

## Proposed Solutions

### Solution 1: Runtime Error for Unsupported Platforms (Recommended)

**Implementation**:
```rust
use std::process::Command;

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // ... path validation from issue #001 ...

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder (macOS): {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder (Windows): {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder (Linux): {}", e))?;
    }

    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    {
        return Err(format!(
            "Opening folders is not supported on this platform ({}). Path: {}",
            std::env::consts::OS,
            path
        ));
    }

    Ok(())
}
```

**Pros**:
- Clear error message at runtime
- User knows exactly what's wrong
- Includes platform name in error
- Still compiles on all platforms
- Can be deployed and will work gracefully

**Cons**:
- Runtime error vs compile-time (but better than silent failure)

**Effort**: 10 minutes
**Risk**: Very low - purely additive

---

### Solution 2: Compile-Time Error (Strictest)

**Implementation**:
```rust
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    compile_error!("open_folder is not supported on this platform");

    // ... rest of implementation ...
}
```

**Pros**:
- Fails at compile time - impossible to ship broken builds
- Enforces platform support explicitly

**Cons**:
- Prevents building on unsupported platforms entirely
- May complicate CI/CD if you need to build for multiple targets
- Blocks development on BSD/etc.

**Effort**: 5 minutes
**Risk**: Low - may break builds on unexpected platforms

---

### Solution 3: Feature Flag Approach (Most Flexible)

**Implementation**:
```rust
// Cargo.toml
[features]
open-folder = ["macos", "windows", "linux"]

// commands.rs
#[cfg(feature = "open-folder")]
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // ... implementation ...
}

#[cfg(not(feature = "open-folder"))]
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    Err("This feature is not available on your platform".to_string())
}
```

**Pros**:
- Most flexible
- Can conditionally enable/disable based on platform
- Clear separation of concerns

**Cons**:
- Adds complexity to Cargo.toml
- Overkill for single command

**Effort**: 30 minutes
**Risk**: Low

---

## Recommended Action

**Implement Solution 1 (Runtime Error) immediately** after path validation (issue #001).

This provides clear error messages without breaking builds on non-standard platforms. Solution 2 can be added later if strict compile-time guarantees are needed.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (add after line 27, before Ok(()))

**Currently Supported Platforms**:
- macOS (uses `open` command)
- Windows (uses `explorer` command)
- Linux (uses `xdg-open` command)

**Unsupported Platforms** (will now get explicit error):
- FreeBSD, OpenBSD, NetBSD
- Android
- iOS (though Tauri doesn't target mobile yet)
- Any future platforms

**Testing Requirements**:
- Test on macOS (should work)
- Test on Windows (should work)
- Test on Linux (should work)
- Mock test for unsupported platform (should return clear error)

## Acceptance Criteria

- [ ] Unsupported platform guard added
- [ ] Error message includes platform name
- [ ] Error message includes the path (for debugging)
- [ ] All supported platforms still work
- [ ] Unsupported platforms get clear error (not silent success)
- [ ] CI passes on all target platforms

## Work Log

### 2026-02-13
- **Discovery**: Architecture review identified silent success on unsupported platforms
- **Assessment**: P1 - misleading behavior, poor user experience
- **Decision**: Add runtime error with clear message
- **Implementation**: Applied Solution 1 (Runtime Error) in conjunction with issue #001 fix
  - Added `#[cfg(not(any(...)))]` guard
  - Returns clear error with platform name and path
  - Includes std::env::consts::OS for debugging
- **Status**: ✅ Implemented, awaiting testing
- **Next**: Mock test for unsupported platform behavior

## Resources

- **Rust cfg attributes**: https://doc.rust-lang.org/reference/conditional-compilation.html
- **Tauri platform support**: https://tauri.app/v1/references/architecture/
- **std::env::consts**: https://doc.rust-lang.org/std/env/consts/
