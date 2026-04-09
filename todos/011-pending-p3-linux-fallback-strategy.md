---
status: pending
priority: p3
issue_id: "011"
tags: [code-review, cross-platform, linux, usability]
dependencies: ["001", "003"]
---

# Implement Linux Fallback Strategy for File Managers

## Problem Statement

The `open_folder` command assumes `xdg-open` is available on Linux, but not all distributions or environments have it (minimal containers, headless servers, alternative desktop environments). This can cause silent failures or confusing errors.

**Location**: `frontend/src-tauri/src/commands.rs` (Linux cfg block)

**Why It Matters**: Linux is fragmented with different desktop environments and file managers. A robust implementation should try multiple fallbacks to maximize compatibility.

## Findings

### From Architecture Strategist Agent

**Current Implementation**:
```rust
#[cfg(target_os = "linux")]
{
    Command::new("xdg-open")
        .arg(&path)
        .spawn()
        .map_err(|e| format!("Failed to open folder: {}", e))?;
}
```

**Issues**:
- Assumes `xdg-open` is installed
- No fallback for alternative desktop environments
- Fails silently if `xdg-open` is missing

**Linux File Manager Variations**:
- **xdg-open**: Universal (but not always installed)
- **nautilus**: GNOME default
- **dolphin**: KDE Plasma default
- **thunar**: XFCE default
- **nemo**: Cinnamon default
- **pcmanfm**: LXDE default
- **caja**: MATE default

### From Performance Oracle Agent

**Performance Consideration**: Trying multiple commands sequentially adds latency (10-50ms per attempt), but only on failure paths.

## Proposed Solutions

### Solution 1: Fallback Chain with Detection (Recommended)

**Implementation**:
```rust
#[cfg(target_os = "linux")]
{
    use std::process::Command;

    // Try xdg-open first (most compatible)
    // Then try desktop-specific file managers
    let commands = vec![
        ("xdg-open", vec![&path]),
        ("nautilus", vec![&path]),           // GNOME
        ("dolphin", vec![&path]),            // KDE
        ("thunar", vec![&path]),             // XFCE
        ("nemo", vec![&path]),               // Cinnamon
        ("pcmanfm", vec![&path]),            // LXDE
        ("caja", vec![&path]),               // MATE
    ];

    let mut last_error = String::new();

    for (cmd, args) in commands {
        match Command::new(cmd).args(&args).spawn() {
            Ok(_) => return Ok(()),
            Err(e) => {
                last_error = format!("{}: {}", cmd, e);
                continue;  // Try next command
            }
        }
    }

    // All commands failed
    Err(format!(
        "No file manager found on this system. Tried: xdg-open, nautilus, dolphin, thunar, nemo, pcmanfm, caja. \
        Last error: {}. Install xdg-utils or configure a default file manager.",
        last_error
    ))
}
```

**Pros**:
- Maximum compatibility across Linux distros
- Clear error message if all fail
- Graceful degradation

**Cons**:
- Tries multiple commands (slower on failure)
- More complex code

**Effort**: 1-2 hours
**Risk**: Low

---

### Solution 2: Detect Desktop Environment First (Optimized)

**Implementation**:
```rust
#[cfg(target_os = "linux")]
{
    // Detect desktop environment from environment variables
    let desktop = std::env::var("XDG_CURRENT_DESKTOP")
        .or_else(|_| std::env::var("DESKTOP_SESSION"))
        .unwrap_or_default()
        .to_lowercase();

    let cmd = match desktop.as_str() {
        "gnome" | "ubuntu" | "ubuntu:gnome" => "nautilus",
        "kde" | "plasma" => "dolphin",
        "xfce" => "thunar",
        "cinnamon" => "nemo",
        "lxde" => "pcmanfm",
        "mate" => "caja",
        _ => "xdg-open",  // Default fallback
    };

    Command::new(cmd)
        .arg(&path)
        .spawn()
        .map_err(|e| {
            format!(
                "Failed to open folder with {} (detected desktop: {}). Error: {}. \
                Try installing xdg-utils or your desktop's file manager.",
                cmd, desktop, e
            )
        })?;
}
```

**Pros**:
- Faster (tries correct command first)
- Smarter detection
- Single command attempt in happy path

**Cons**:
- Environment variables may be wrong or missing
- No fallback if detected command doesn't exist

**Effort**: 2 hours
**Risk**: Medium (detection may fail)

---

### Solution 3: Hybrid Approach (Best of Both)

**Implementation**:
```rust
#[cfg(target_os = "linux")]
{
    // Detect desktop environment
    let desktop = std::env::var("XDG_CURRENT_DESKTOP")
        .unwrap_or_default()
        .to_lowercase();

    // Build priority list based on desktop
    let mut commands = match desktop.as_str() {
        "gnome" | "ubuntu" => vec!["nautilus", "xdg-open"],
        "kde" | "plasma" => vec!["dolphin", "xdg-open"],
        "xfce" => vec!["thunar", "xdg-open"],
        "cinnamon" => vec!["nemo", "xdg-open"],
        _ => vec!["xdg-open", "nautilus", "dolphin", "thunar"],
    };

    // Try commands in priority order
    for cmd in commands {
        if let Ok(_) = Command::new(cmd).arg(&path).spawn() {
            return Ok(());
        }
    }

    Err("No file manager found. Install xdg-utils.".to_string())
}
```

**Pros**:
- Fast on happy path (tries likely command first)
- Fallback chain for reliability
- Best of both worlds

**Cons**:
- Most complex solution

**Effort**: 2-3 hours
**Risk**: Low

---

## Recommended Action

**Implement Solution 1 (Fallback Chain)** after security fixes (issues #001-#003) are complete.

This provides maximum compatibility without being overly complex. Solution 3 (Hybrid) can be considered in Phase 3 if performance becomes a concern.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (Linux cfg block)

**Testing Requirements**:
- Test on Ubuntu (GNOME)
- Test on KDE Neon (KDE Plasma)
- Test on Xubuntu (XFCE)
- Test on minimal Debian (no desktop environment)
- Verify fallback chain works
- Verify error messages are helpful

**Performance Impact**:
- Happy path: 0.5ms (immediate success)
- Failure path: 5-10ms per failed command
- Worst case: 50-70ms (all 7 commands fail)
- User-facing: negligible

## Acceptance Criteria

- [ ] Fallback chain implemented for Linux
- [ ] Works on GNOME (nautilus or xdg-open)
- [ ] Works on KDE (dolphin or xdg-open)
- [ ] Works on XFCE (thunar or xdg-open)
- [ ] Works on minimal systems (xdg-open)
- [ ] Clear error message if all commands fail
- [ ] No performance regression on happy path
- [ ] Tests pass on multiple Linux distros (CI)

## Work Log

### 2026-02-13
- **Discovery**: Architecture review identified Linux fragmentation concerns
- **Assessment**: P3 - nice-to-have for better Linux support
- **Decision**: Implement after core functionality is stable

## Resources

- **XDG Desktop Environments**: https://specifications.freedesktop.org/
- **Linux File Managers**: https://wiki.archlinux.org/title/File_manager
- **Desktop Environment Detection**: https://unix.stackexchange.com/questions/116539/
