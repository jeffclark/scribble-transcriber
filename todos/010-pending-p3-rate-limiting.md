---
status: pending
priority: p3
issue_id: "010"
tags: [code-review, security, rust, performance]
dependencies: []
---

# Add Rate Limiting to open_folder Command

## Problem Statement

The `open_folder` command has no rate limiting, allowing potential abuse through rapid repeated calls. An attacker or buggy code could spawn excessive processes, causing denial of service or system resource depletion.

**Location**: `frontend/src-tauri/src/commands.rs`

**Why It Matters**: While this is a low-severity security issue (no data at risk), excessive process spawning can degrade system performance or crash the application.

## Findings

### From Security Sentinel Agent

**CVSS Score**: 3.1 (Low severity)

**Vulnerability**:
- No rate limiting on command invocations
- Rapid calls could spawn 100+ processes before system responds
- Each process consumes memory and file descriptors
- Potential denial of service

**Attack Scenario**:
```typescript
// Malicious or buggy code
for (let i = 0; i < 1000; i++) {
  invoke('open_folder', { path: '/tmp' });
}
// Spawns 1000 Finder/Explorer windows
```

**Impact**:
- System resource depletion
- UI becomes unresponsive
- User frustration
- Potential system crash on low-memory devices

## Proposed Solutions

### Solution 1: Token Bucket Rate Limiter (Recommended)

**Implementation**:
```rust
use std::sync::Mutex;
use std::time::{Duration, Instant};

struct RateLimiter {
    last_call: Instant,
    min_interval: Duration,
}

lazy_static::lazy_static! {
    static ref RATE_LIMITER: Mutex<RateLimiter> = Mutex::new(RateLimiter {
        last_call: Instant::now() - Duration::from_secs(1),
        min_interval: Duration::from_millis(500),  // Max 2 calls per second
    });
}

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    // Check rate limit
    {
        let mut limiter = RATE_LIMITER.lock().unwrap();
        let now = Instant::now();
        if now.duration_since(limiter.last_call) < limiter.min_interval {
            return Err("Rate limit exceeded. Please wait before trying again.".to_string());
        }
        limiter.last_call = now;
    }

    // ... rest of implementation (path validation, spawn) ...

    Ok(())
}
```

**Pros**:
- Simple to implement
- Effective against abuse
- Clear error message to user
- Low overhead (mutex lock ~1μs)
- Configurable rate (500ms = 2 calls/sec)

**Cons**:
- Requires `lazy_static` crate
- Global state (but acceptable for rate limiting)

**Effort**: 2-3 hours (including testing)
**Risk**: Low

---

### Solution 2: Sliding Window Rate Limiter (More Sophisticated)

**Implementation**:
```rust
use std::sync::Mutex;
use std::collections::VecDeque;
use std::time::Instant;

struct SlidingWindowLimiter {
    calls: VecDeque<Instant>,
    window: Duration,
    max_calls: usize,
}

lazy_static::lazy_static! {
    static ref RATE_LIMITER: Mutex<SlidingWindowLimiter> = Mutex::new(SlidingWindowLimiter {
        calls: VecDeque::new(),
        window: Duration::from_secs(10),  // 10-second window
        max_calls: 5,  // Max 5 calls per 10 seconds
    });
}

#[tauri::command]
pub fn open_folder(path: String) -> Result<(), String> {
    {
        let mut limiter = RATE_LIMITER.lock().unwrap();
        let now = Instant::now();

        // Remove old calls outside the window
        limiter.calls.retain(|&t| now.duration_since(t) < limiter.window);

        // Check if limit exceeded
        if limiter.calls.len() >= limiter.max_calls {
            return Err(format!(
                "Rate limit exceeded. Max {} calls per {} seconds.",
                limiter.max_calls,
                limiter.window.as_secs()
            ));
        }

        // Record this call
        limiter.calls.push_back(now);
    }

    // ... rest of implementation ...

    Ok(())
}
```

**Pros**:
- More accurate rate limiting
- Allows short bursts (5 calls quickly, then wait)
- Better UX (users can click rapidly if needed)

**Cons**:
- More complex
- Slightly higher memory usage (tracks last N calls)
- Overkill for this use case

**Effort**: 3-4 hours
**Risk**: Low

---

### Solution 3: Frontend Debouncing (Complementary)

**Implementation**:
```typescript
import { debounce } from 'lodash';

const handleOpenFolderDebounced = debounce(
  async (folderPath: string) => {
    try {
      await invoke('open_folder', { path: folderPath });
    } catch (err) {
      console.error("Failed to open folder:", err);
    }
  },
  500  // Wait 500ms after last call
);

const handleOpenFolder = (folderPath: string) => {
  handleOpenFolderDebounced(folderPath);
};
```

**Pros**:
- Prevents accidental double-clicks
- Simple to implement
- No backend changes

**Cons**:
- Can be bypassed (client-side only)
- Requires lodash or custom debounce
- Doesn't protect against malicious code

**Effort**: 30 minutes
**Risk**: Very low

---

## Recommended Action

**Implement Solution 1 (Token Bucket Rate Limiter)** if abuse becomes a real concern. Otherwise, defer this to Phase 3 or later.

**Rationale**: This is a nice-to-have security hardening, not a critical vulnerability. Users are unlikely to accidentally spam the button, and malicious code could abuse other commands too.

**Immediate Action**: Add Solution 3 (Frontend Debouncing) as a quick win to prevent accidental double-clicks.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/src/commands.rs` (add rate limiter)
- `frontend/src-tauri/Cargo.toml` (add lazy_static if using Solution 1)
- Optional: `frontend/src/App.tsx` (add debouncing)

**Dependencies** (Solution 1):
```toml
# Cargo.toml
[dependencies]
lazy_static = "1.4"
```

**Rate Limit Configuration**:
- **Recommended**: 500ms minimum interval (2 calls/sec)
- **Conservative**: 1 second minimum interval
- **Aggressive**: 5 calls per 10 seconds (sliding window)

**Testing Requirements**:
- Test single call (should work)
- Test rapid calls (should fail after limit)
- Test calls after waiting (should work again)
- Verify error message is clear

## Acceptance Criteria

- [ ] Rate limiter implemented (500ms minimum interval)
- [ ] Rapid calls return clear error message
- [ ] Legitimate use cases still work (single clicks)
- [ ] No memory leaks from rate limiter state
- [ ] Tests added for rate limiting
- [ ] Documentation updated

## Work Log

### 2026-02-13
- **Discovery**: Security sentinel identified lack of rate limiting
- **Assessment**: P3 - low severity, nice-to-have hardening
- **Decision**: Defer to Phase 3 unless abuse observed

## Resources

- **Rate Limiting Strategies**: https://en.wikipedia.org/wiki/Rate_limiting
- **Token Bucket Algorithm**: https://en.wikipedia.org/wiki/Token_bucket
- **lazy_static crate**: https://docs.rs/lazy_static/
