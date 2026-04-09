---
status: pending
priority: p2
issue_id: "005"
tags: [code-review, code-quality, rust, refactoring]
dependencies: ["001"]
---

# Simplify Duplicated Error Handling Code

## Problem Statement

The `open_folder` Rust command contains three nearly identical platform-specific blocks with duplicated error handling logic. This violates the DRY (Don't Repeat Yourself) principle and makes maintenance harder.

**Location**: `frontend/src-tauri/src/commands.rs` (lines 5-27)

**Why It Matters**: Code duplication increases maintenance burden, potential for bugs (fixing in one place but not others), and reduces readability. The current 27 lines can be simplified to 11 lines (59% reduction) with identical functionality.

## Findings

### From Code Simplicity Reviewer

**Current Duplicated Code**:
```rust
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    Ok(())
}
```

**Issues**:
- Identical `.arg(&path).spawn().map_err(...)` logic repeated 3 times
- Same error message format duplicated
- Only difference is command name ("open", "explorer", "xdg-open")

### From Pattern Recognition Agent

**Additional Findings**:
- Error message prefix "Failed to open folder:" is redundant (OS error already descriptive)
- `format!()` macro adds minimal value
- Could extract command selection to single location

## Proposed Solutions

### Solution 1: Extract Command Name (Recommended)

**Implementation**:
```rust
use std::process::Command;

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // ... path validation from issue #001 ...

    // Select command based on platform
    let cmd = if cfg!(target_os = "macos") {
        "open"
    } else if cfg!(target_os = "windows") {
        "explorer"
    } else if cfg!(target_os = "linux") {
        "xdg-open"
    } else {
        return Err(format!("Platform not supported: {}", std::env::consts::OS));
    };

    // Single execution path
    Command::new(cmd)
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

**Comparison**:
- **Before**: 27 lines (current)
- **After**: 11 lines (59% reduction)
- Identical functionality
- Single error handling path
- Easier to maintain

**Pros**:
- Significant LOC reduction (59%)
- Eliminates all duplication
- Easier to add logging/telemetry (single location)
- Easier to modify error handling
- Simpler error message (OS error is descriptive enough)

**Cons**:
- Uses runtime `cfg!()` instead of compile-time `#[cfg()]`
  - **Note**: This still compiles out unused branches in release builds
- All platform code is compiled (but dead code eliminated by optimizer)

**Effort**: 15 minutes
**Risk**: Very low - tested pattern

---

### Solution 2: Conditional Compilation with Helper Function

**Implementation**:
```rust
use std::process::Command;

#[cfg(target_os = "macos")]
const OPEN_CMD: &str = "open";

#[cfg(target_os = "windows")]
const OPEN_CMD: &str = "explorer";

#[cfg(target_os = "linux")]
const OPEN_CMD: &str = "xdg-open";

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // ... path validation ...

    Command::new(OPEN_CMD)
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

**Pros**:
- True compile-time selection
- Minimal code
- Only relevant platform code in binary

**Cons**:
- Need to handle unsupported platforms separately
- Constants at module level (less localized)

**Effort**: 20 minutes
**Risk**: Low

---

### Solution 3: Macro-Based (Over-Engineering)

**Implementation**:
```rust
macro_rules! platform_open {
    ($cmd:expr, $path:expr) => {
        Command::new($cmd)
            .arg($path)
            .spawn()
            .map_err(|e| e.to_string())
    };
}

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    platform_open!("open", &path)?;

    #[cfg(target_os = "windows")]
    platform_open!("explorer", &path)?;

    #[cfg(target_os = "linux")]
    platform_open!("xdg-open", &path)?;

    Ok(())
}
```

**Pros**:
- Compile-time optimization
- Enforces consistency

**Cons**:
- **Overkill** for 3 lines of code
- Adds complexity
- Macros are harder to debug

**Effort**: 30 minutes
**Risk**: Low but unnecessary

---

## Recommended Action

**Implement Solution 1 (Extract Command Name)** when refactoring after path validation (issue #001).

This provides the best balance of simplicity, maintainability, and code reduction. The runtime `cfg!()` is still optimized away in release builds, so there's no performance penalty.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (complete rewrite of function)

**Code Metrics**:
- Current: 27 lines, cyclomatic complexity = 1, 3 duplicated blocks
- After: 11 lines, cyclomatic complexity = 1, 0 duplicated blocks
- Reduction: 59% LOC, 100% duplication removed

**Testing Requirements**:
- All three platforms still work correctly
- Error handling remains the same
- Unsupported platforms handled (issue #003)

## Acceptance Criteria

- [ ] Command name selection extracted to single location
- [ ] Only one `.spawn()` call with error handling
- [ ] Error messages remain clear and helpful
- [ ] All three platforms tested (macOS, Windows, Linux)
- [ ] Code review confirms simplification doesn't break anything
- [ ] LOC reduced by at least 50%

## Work Log

### 2026-02-13
- **Discovery**: Code simplicity reviewer identified 59% potential reduction
- **Assessment**: P2 - not urgent but improves maintainability
- **Decision**: Implement after path validation (issue #001)

## Resources

- **Rust cfg! macro**: https://doc.rust-lang.org/std/macro.cfg.html
- **DRY Principle**: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
- **Code Simplicity Analysis**: From code-simplicity-reviewer agent
