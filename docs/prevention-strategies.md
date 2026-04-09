# Prevention Strategies: Platform-Specific Code Duplication

## Overview

This document outlines prevention strategies and best practices for avoiding code duplication in platform-specific implementations, based on the refactoring of the `open_folder` command which eliminated 34 lines of duplicated code.

## 1. Prevention Strategies

### 1.1 Compile-Time Platform Selection Pattern

**Anti-Pattern to Avoid:**
```rust
// DON'T: Duplicate logic across platform-specific code blocks
#[cfg(target_os = "macos")]
pub fn open_folder(path: String) -> Result<(), String> {
    let path_buf = PathBuf::from(&path);
    if !path_buf.exists() { return Err("..."); }
    if !path_buf.is_dir() { return Err("..."); }
    let canonical_path = path_buf.canonicalize()?;
    let safe_path = canonical_path.to_str()?;
    Command::new("open").arg(safe_path).spawn()?;
    Ok(())
}

#[cfg(target_os = "windows")]
pub fn open_folder(path: String) -> Result<(), String> {
    let path_buf = PathBuf::from(&path);
    if !path_buf.exists() { return Err("..."); }
    if !path_buf.is_dir() { return Err("..."); }
    let canonical_path = path_buf.canonicalize()?;
    let safe_path = canonical_path.to_str()?;
    Command::new("explorer").arg(safe_path).spawn()?;
    Ok(())
}

#[cfg(target_os = "linux")]
pub fn open_folder(path: String) -> Result<(), String> {
    let path_buf = PathBuf::from(&path);
    if !path_buf.exists() { return Err("..."); }
    if !path_buf.is_dir() { return Err("..."); }
    let canonical_path = path_buf.canonicalize()?;
    let safe_path = canonical_path.to_str()?;
    Command::new("xdg-open").arg(safe_path).spawn()?;
    Ok(())
}
```

**Recommended Pattern:**
```rust
// DO: Single function with compile-time platform selection
pub fn open_folder(path: String) -> Result<(), String> {
    // Shared validation logic (runs on all platforms)
    let path_buf = PathBuf::from(&path);
    if !path_buf.exists() { return Err("..."); }
    if !path_buf.is_dir() { return Err("..."); }
    let canonical_path = path_buf.canonicalize()?;
    let safe_path = canonical_path.to_str()?;

    // Platform-specific command selection (compile-time)
    let cmd = if cfg!(target_os = "macos") {
        "open"
    } else if cfg!(target_os = "windows") {
        "explorer"
    } else if cfg!(target_os = "linux") {
        "xdg-open"
    } else {
        return Err(format!("Unsupported platform: {}", std::env::consts::OS));
    };

    // Shared execution logic (runs on all platforms)
    Command::new(cmd).arg(safe_path).spawn()?;
    Ok(())
}
```

### 1.2 Code Review Checklist

When reviewing platform-specific code, check for:

- [ ] **Duplication Detection**: Are the same validation, transformation, or error-handling steps repeated across `#[cfg]` blocks?
- [ ] **Shared Logic Extraction**: Can common logic be moved outside platform-specific sections?
- [ ] **cfg!() Opportunities**: Is `cfg!()` macro more appropriate than `#[cfg()]` attribute?
- [ ] **Test Coverage**: Are all platforms tested? Are shared behaviors tested once, not per-platform?
- [ ] **Error Messages**: Do platform-specific errors include the actual platform name for debugging?
- [ ] **Unsupported Platform Handling**: Is there a fallback or clear error for unsupported platforms?
- [ ] **Security Validation**: Is security-critical validation (like path sanitization) in shared code, not duplicated per-platform?

### 1.3 Linting and Tooling Suggestions

#### Clippy Configuration

Add to `.cargo/config.toml` or run with CI:
```toml
[target.'cfg(all())']
rustflags = ["-D", "warnings"]

# Enforce clippy lints that catch duplication
[lints.clippy]
# Warn about duplicated code patterns
similar_names = "warn"
# Encourage using cfg!() in function bodies
non_minimal_cfg = "warn"
```

#### Custom Clippy Lint Script

Create a script to detect potential platform duplication:
```bash
#!/bin/bash
# check-platform-duplication.sh

echo "Checking for potential platform-specific code duplication..."

# Find files with multiple #[cfg(target_os)] attributes
rg "#\[cfg\(target_os" --type rust -c | awk -F: '$2 > 2 { print $1 }' | while read file; do
    echo "⚠️  $file has multiple #[cfg(target_os)] blocks - review for duplication"
done

# Suggest using cfg!() for simple selections
rg "#\[cfg\(target_os.*\)\]\s*\n.*Command::new" --type rust -U | while read match; do
    echo "💡 Consider using cfg!() macro instead of #[cfg()] attribute for command selection"
done
```

#### GitHub Actions CI Check

Add to `.github/workflows/rust.yml`:
```yaml
- name: Check for platform code duplication
  run: |
    # Count lines in cfg blocks
    cargo expand | grep -A 50 "#\[cfg(target_os" | \
      awk '/^#\[cfg/ { block++ } block > 0 { lines++ } /^}/ {
        if (lines > 20) print "Warning: Large cfg block detected"
        lines=0; block=0
      }'
```

## 2. Best Practices

### 2.1 When to Use `cfg!()` vs `#[cfg()]`

#### Use `cfg!()` Macro (Runtime Evaluation, Compile-Time Selection)

**When to use:**
- Selecting between different values (strings, constants, enums)
- Small platform-specific logic within a larger function
- When you want to keep code in a single function
- When the surrounding logic is identical across platforms

**Benefits:**
- Single code path = easier testing
- DRY principle: shared validation runs once
- Better for code reviewers to see entire flow
- Compiler optimizes away branches for target platform

**Example:**
```rust
let command = if cfg!(target_os = "windows") {
    "cmd.exe"
} else {
    "sh"
};
```

#### Use `#[cfg()]` Attribute (Conditional Compilation)

**When to use:**
- Entirely different implementations required
- Platform-specific types or imports
- Large blocks of platform-specific code
- When implementations have different signatures or dependencies

**Benefits:**
- Code not compiled for other platforms (reduces binary size)
- Can use platform-specific crates/types
- Compile errors on unsupported platforms

**Example:**
```rust
#[cfg(target_os = "windows")]
use winapi::um::shellapi::ShellExecuteW;

#[cfg(target_os = "windows")]
fn open_with_native_api(path: &str) -> Result<(), String> {
    // Windows-specific implementation using winapi
}

#[cfg(not(target_os = "windows"))]
fn open_with_native_api(path: &str) -> Result<(), String> {
    Err("Not implemented on this platform".to_string())
}
```

### 2.2 How to Structure Platform-Specific Code

#### Pattern 1: Facade with Platform Selection (Recommended for Simple Cases)

```rust
pub fn platform_operation(input: Input) -> Result<Output, Error> {
    // 1. Shared validation
    validate_input(&input)?;

    // 2. Platform-specific selection
    let platform_value = if cfg!(target_os = "macos") {
        "macos-value"
    } else if cfg!(target_os = "windows") {
        "windows-value"
    } else {
        return Err(Error::UnsupportedPlatform);
    };

    // 3. Shared execution
    execute_operation(platform_value, input)
}
```

#### Pattern 2: Strategy Pattern with Trait (Complex Cases)

```rust
trait PlatformStrategy {
    fn execute(&self, input: &Input) -> Result<Output, Error>;
}

struct MacOSStrategy;
impl PlatformStrategy for MacOSStrategy {
    fn execute(&self, input: &Input) -> Result<Output, Error> {
        // macOS implementation
    }
}

struct WindowsStrategy;
impl PlatformStrategy for WindowsStrategy {
    fn execute(&self, input: &Input) -> Result<Output, Error> {
        // Windows implementation
    }
}

pub fn platform_operation(input: Input) -> Result<Output, Error> {
    validate_input(&input)?;

    let strategy: Box<dyn PlatformStrategy> = if cfg!(target_os = "macos") {
        Box::new(MacOSStrategy)
    } else if cfg!(target_os = "windows") {
        Box::new(WindowsStrategy)
    } else {
        return Err(Error::UnsupportedPlatform);
    };

    strategy.execute(&input)
}
```

#### Pattern 3: Module Hierarchy (Very Complex Cases)

```rust
// lib.rs
mod platform {
    #[cfg(target_os = "macos")]
    pub mod macos;
    #[cfg(target_os = "windows")]
    pub mod windows;
    #[cfg(target_os = "linux")]
    pub mod linux;
}

#[cfg(target_os = "macos")]
use platform::macos as platform_impl;
#[cfg(target_os = "windows")]
use platform::windows as platform_impl;
#[cfg(target_os = "linux")]
use platform::linux as platform_impl;

pub fn platform_operation(input: Input) -> Result<Output, Error> {
    validate_input(&input)?;
    platform_impl::execute(input)
}
```

### 2.3 Testing Strategies for Cross-Platform Code

#### Test Structure

```rust
#[cfg(test)]
mod tests {
    use super::*;

    // 1. Test shared behavior once (not per-platform)
    #[test]
    fn test_validation_logic() {
        assert!(validate_input(&valid_input).is_ok());
        assert!(validate_input(&invalid_input).is_err());
    }

    // 2. Test platform-specific behavior on current platform
    #[test]
    fn test_platform_operation_success() {
        let result = platform_operation(valid_input);
        assert!(result.is_ok());
    }

    // 3. Test error cases that are platform-agnostic
    #[test]
    fn test_invalid_input_rejected() {
        let result = platform_operation(invalid_input);
        assert!(result.is_err());
    }

    // 4. Platform-specific tests (only run on that platform)
    #[cfg(target_os = "macos")]
    #[test]
    fn test_macos_specific_behavior() {
        // Test macOS-only edge cases
    }
}
```

#### Integration Testing with Mock Platforms

For functions that are hard to test across platforms:

```rust
// Refactor to dependency injection for testing
pub fn platform_operation_testable<F>(
    input: Input,
    platform_fn: F
) -> Result<Output, Error>
where
    F: Fn(&str) -> Result<(), Error>
{
    validate_input(&input)?;
    let cmd = get_platform_command();
    platform_fn(cmd)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_with_mock_platform() {
        let mock_platform = |cmd: &str| {
            assert_eq!(cmd, expected_command);
            Ok(())
        };

        let result = platform_operation_testable(input, mock_platform);
        assert!(result.is_ok());
    }
}
```

## 3. Test Cases Documentation

The refactored `open_folder` command includes 4 comprehensive test cases that prevent regression and ensure security:

### Test Case 1: `test_valid_directory`

```rust
#[test]
fn test_valid_directory() {
    let temp_dir = env::temp_dir();
    let result = open_folder(temp_dir.to_string_lossy().to_string());
    assert!(result.is_ok());
}
```

**Purpose**: Verify the happy path - opening a valid, existing directory.

**Why Important**:
- Ensures basic functionality works on all platforms
- Uses `env::temp_dir()` for cross-platform compatibility
- Confirms that the command selection and execution path work correctly
- Validates that path canonicalization doesn't break valid paths

**Security Benefit**: Confirms legitimate use cases aren't blocked by security measures.

---

### Test Case 2: `test_nonexistent_directory`

```rust
#[test]
fn test_nonexistent_directory() {
    let result = open_folder("/nonexistent/path/12345".to_string());
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("does not exist"));
}
```

**Purpose**: Verify rejection of non-existent paths.

**Why Important**:
- Prevents attempts to open paths that don't exist
- Tests the validation layer before platform-specific code executes
- Ensures error messages are informative for debugging
- Prevents potential errors from being passed to OS commands

**Security Benefit**: Prevents potential command injection or information disclosure by validating paths early.

---

### Test Case 3: `test_file_not_directory`

```rust
#[test]
fn test_file_not_directory() {
    // Create temp file
    let temp_file = env::temp_dir().join("test_file.txt");
    std::fs::write(&temp_file, "test").unwrap();

    let result = open_folder(temp_file.to_string_lossy().to_string());
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("not a directory"));

    // Cleanup
    std::fs::remove_file(temp_file).ok();
}
```

**Purpose**: Verify that files are rejected (only directories allowed).

**Why Important**:
- Enforces the function contract: only directories can be opened
- Tests the type-checking validation layer
- Ensures appropriate error messages for wrong input types
- Prevents unexpected behavior from OS file managers

**Security Benefit**: Prevents attempts to open arbitrary files which could trigger unwanted actions (e.g., opening executables).

**Note**: Test properly cleans up temporary resources to avoid pollution.

---

### Test Case 4: `test_empty_path`

```rust
#[test]
fn test_empty_path() {
    let result = open_folder("".to_string());
    assert!(result.is_err());
    // Should fail at path validation
}
```

**Purpose**: Verify rejection of empty/malformed input.

**Why Important**:
- Tests edge case handling
- Ensures input validation catches minimal/degenerate inputs
- Prevents passing empty strings to OS commands
- Documents expected behavior for invalid input

**Security Benefit**: Prevents potential command injection via edge cases like empty strings, which might be interpreted unexpectedly by shell commands.

---

### Test Coverage Summary

| Validation Layer | Tests Covering It |
|-----------------|-------------------|
| Path existence | Test 2 (nonexistent) |
| Path type (dir vs file) | Test 3 (file not directory) |
| Path validity | Test 4 (empty path) |
| Path canonicalization | Test 1 (valid directory) |
| Command execution | Test 1 (valid directory) |

**Coverage Strategy**:
- Happy path: 1 test
- Error paths: 3 tests
- Security validations: All 4 tests verify different security checks
- Platform-agnostic: All tests run on any platform

**What's NOT Tested** (and why):
- Platform command selection logic: Tested implicitly via successful execution
- Actual OS behavior: Out of scope (we test our code, not the OS)
- Symlinks: Could be added but requires complex setup
- Permission errors: Environment-dependent, hard to test reliably

## 4. Migration Guide

### Identifying Duplication Candidates

Run this analysis on your codebase:

```bash
# Find files with multiple platform-specific blocks
rg "#\[cfg\(target_os" -t rust -c | awk -F: '$2 >= 3'

# Find duplicated function signatures across cfg blocks
rg "^#\[cfg.*\n.*fn \w+\(" -U -t rust
```

### Refactoring Steps

1. **Extract Common Logic**: Identify validation, transformation, and error handling that's identical across platforms
2. **Identify Differences**: What actually differs? Usually just command names, paths, or constants
3. **Create Single Function**: Move common logic outside platform selection
4. **Use cfg!() for Selection**: Replace `#[cfg()]` attributes with `cfg!()` macro where appropriate
5. **Add Comprehensive Tests**: Cover shared validation and platform-agnostic error cases
6. **Document Unsupported Platforms**: Add explicit error for platforms you don't support

### Before/After Metrics

From the `open_folder` refactoring:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Lines of code | ~124 | 90 | -27% |
| Duplicated logic | 3 copies | 1 copy | -66% duplication |
| Test coverage | 0 tests | 4 tests | +100% coverage |
| Platform support | Implicit | Explicit error for unsupported | Better UX |
| Maintainability | Low (3 places to update) | High (1 place to update) | 3x easier |

## 5. References and Resources

### Rust Documentation
- [Conditional Compilation](https://doc.rust-lang.org/reference/conditional-compilation.html)
- [cfg! Macro](https://doc.rust-lang.org/std/macro.cfg.html)
- [Platform-specific APIs](https://doc.rust-lang.org/std/env/consts/index.html)

### Related Patterns
- DRY Principle (Don't Repeat Yourself)
- Strategy Pattern for platform abstraction
- Facade Pattern for unified interfaces

### Tools
- `cargo expand`: See what code looks like after macro expansion
- `cargo clippy`: Lint for common anti-patterns
- `rg` (ripgrep): Find patterns across codebase

---

**Document Version**: 1.0
**Last Updated**: 2026-02-13
**Based on**: Refactoring commit `11b6ba4`
