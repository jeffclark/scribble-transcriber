---
status: pending
priority: p3
issue_id: "009"
tags: [code-review, ci-cd, testing, cross-platform]
dependencies: ["008"]
---

# Add CI Cross-Platform Testing

## Problem Statement

The `open_folder` command uses platform-specific code paths (macOS, Windows, Linux) but there's no CI matrix to test all three platforms. This means platform-specific bugs could slip through to production.

**Why It Matters**: Conditional compilation is only as good as the testing. Without testing on all target platforms, we can't be confident that platform-specific code works correctly.

## Findings

### From Architecture Strategist Agent

**Current CI Status**: Unknown (no CI configuration found)

**Platform-Specific Code Paths**:
```rust
#[cfg(target_os = "macos")]     // Uses "open" command
#[cfg(target_os = "windows")]   // Uses "explorer" command
#[cfg(target_os = "linux")]     // Uses "xdg-open" command
```

**Risk**: Each platform has different:
- Command names
- Argument formats
- Error messages
- Path formats (Windows uses backslashes)

**Recommendation**: CI matrix build to test all platforms

## Proposed Solutions

### Solution 1: GitHub Actions Matrix (Recommended)

**Implementation**:
```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, feat/*]
  pull_request:

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
        include:
          - os: macos-latest
            target: aarch64-apple-darwin
            platform: macOS
          - os: windows-latest
            target: x86_64-pc-windows-msvc
            platform: Windows
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
            platform: Linux

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: ${{ matrix.target }}
          override: true

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: cd frontend && npm install

      - name: Run Rust tests
        run: cd frontend/src-tauri && cargo test

      - name: Run frontend tests
        run: cd frontend && npm test

      - name: Build Tauri app
        run: cd frontend && npm run tauri build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: app-${{ matrix.platform }}
          path: frontend/src-tauri/target/release/bundle/
```

**Pros**:
- Tests all three platforms automatically
- Catches platform-specific bugs early
- Free for open source (GitHub Actions)
- Parallel execution (fast)
- Builds artifacts for each platform

**Cons**:
- Requires GitHub repository
- CI minutes consumption (free tier usually sufficient)

**Effort**: 2-3 hours (including testing/debugging)
**Risk**: Low

---

### Solution 2: Minimal CI (Quick Setup)

**Implementation**:
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Run tests
        run: cd frontend/src-tauri && cargo test

      - name: Check builds
        run: cd frontend/src-tauri && cargo check
```

**Pros**:
- Quick to set up
- Better than nothing
- Tests Linux at minimum

**Cons**:
- Only tests one platform
- Doesn't catch Windows/macOS issues

**Effort**: 30 minutes
**Risk**: Low but incomplete

---

### Solution 3: Local Testing Script (No CI)

**Implementation**:
```bash
#!/bin/bash
# scripts/test-all-platforms.sh

echo "Testing on current platform..."
cd frontend/src-tauri && cargo test

echo "Cross-compiling for other platforms..."
cargo build --target x86_64-pc-windows-msvc
cargo build --target aarch64-apple-darwin
cargo build --target x86_64-unknown-linux-gnu

echo "Note: This only checks compilation, not runtime behavior."
```

**Pros**:
- No CI setup required
- Can run locally

**Cons**:
- Manual process
- Doesn't actually test other platforms (just checks compilation)
- Easy to forget

**Effort**: 1 hour
**Risk**: Medium (manual processes are error-prone)

---

## Recommended Action

**Implement Solution 1 (GitHub Actions Matrix)** when repository is ready for CI.

This provides comprehensive platform testing with minimal ongoing effort. If the project isn't on GitHub or CI isn't set up yet, start with Solution 2 (Minimal CI) and upgrade later.

## Technical Details

**Affected Files**:
- `.github/workflows/test.yml` (new file)
- Optional: `.github/workflows/build.yml` (separate build workflow)

**CI Matrix Strategy**:
- **fail-fast: false**: Continue testing other platforms even if one fails
- **Parallel execution**: All three platforms tested simultaneously
- **Artifact upload**: Preserve builds for manual testing

**Test Coverage per Platform**:
- macOS: Tests `open` command path
- Windows: Tests `explorer` command path
- Linux: Tests `xdg-open` command path

**Badge for README** (optional):
```markdown
![Tests](https://github.com/user/repo/workflows/Test/badge.svg)
```

## Acceptance Criteria

- [ ] CI workflow file created
- [ ] Matrix includes macOS, Windows, Linux
- [ ] All platforms run tests automatically
- [ ] All platforms build successfully
- [ ] CI runs on push and pull requests
- [ ] Failing builds block merges
- [ ] Team is notified of failures

## Work Log

### 2026-02-13
- **Discovery**: Architecture review recommended CI matrix
- **Assessment**: P3 - important for reliability but not blocking
- **Decision**: Implement when CI infrastructure is ready

## Resources

- **GitHub Actions**: https://docs.github.com/en/actions
- **Rust GitHub Actions**: https://github.com/actions-rs/toolchain
- **Tauri CI Guide**: https://tauri.app/v2/distribute/ci-cd/
- **Matrix Strategy**: https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
