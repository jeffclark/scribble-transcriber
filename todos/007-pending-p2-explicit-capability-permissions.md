---
status: pending
priority: p2
issue_id: "007"
tags: [code-review, security, tauri, permissions]
dependencies: []
---

# Add Explicit Capability Permissions

## Problem Statement

The current Tauri capabilities configuration removed shell permissions but doesn't explicitly declare permissions needed for custom commands. This creates an implicit security model that's harder to audit and may break in future Tauri versions.

**Location**: `frontend/src-tauri/capabilities/default.json`

**Why It Matters**: Explicit permissions make the security model clear, auditable, and maintainable. Implicit permissions may work now but could break with Tauri updates or create security vulnerabilities.

## Findings

### From Architecture Strategist Agent

**Current Configuration**:
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default permissions for the application",
  "windows": ["main"],
  "permissions": [
    "dialog:default"
  ]
}
```

**Issues**:
- No explicit permission for `core:default` (needed for invoke() IPC)
- No explicit permission for `path:default` (needed for path operations)
- Relying on Tauri's implicit allowlist

**Security Implications**:
| Aspect | Before (Plugin) | After (Custom) |
|--------|----------------|----------------|
| **Permission Granularity** | Fine-grained (`shell:allow-open`) | Coarse (`core:default` implied) |
| **Audit Trail** | Plugin version pinned | Direct system command |
| **Explicit Declaration** | Clear in capabilities file | Implicit |

### From Security Sentinel Agent

**Recommendation**: Make all permissions explicit for defense in depth and clear security model.

## Proposed Solutions

### Solution 1: Add Core and Path Permissions (Recommended)

**Implementation**:
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default permissions for the application",
  "windows": ["main"],
  "permissions": [
    "dialog:default",
    "core:default",
    "path:default"
  ]
}
```

**Explanation**:
- `dialog:default`: File picker dialogs (already present)
- `core:default`: IPC invoke() mechanism for custom commands
- `path:default`: Path validation and canonicalization in Rust

**Pros**:
- Explicit security model
- Clear documentation of required permissions
- Easier security audits
- Future-proof against Tauri changes

**Cons**:
- None (purely additive, clarifies existing implicit permissions)

**Effort**: 5 minutes
**Risk**: Very low

---

### Solution 2: Granular Command-Specific Permissions (Future-Proof)

**Implementation**:
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default permissions for the application",
  "windows": ["main"],
  "permissions": [
    "dialog:default",
    "core:default",
    "path:default"
  ],
  "commands": {
    "allow": [
      "open_folder"
    ],
    "deny": []
  }
}
```

**Pros**:
- Most explicit
- Can allowlist/denylist specific commands
- Best for audit trails
- Follows principle of least privilege

**Cons**:
- More verbose
- May not be supported in Tauri 2.0 (check docs)
- Overkill for single command

**Effort**: 15 minutes
**Risk**: Low (check Tauri docs for support)

---

### Solution 3: Add Documentation Only (Minimal)

**Implementation**:
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default permissions for the application. Custom commands use core:default for IPC.",
  "windows": ["main"],
  "permissions": [
    "dialog:default"
    // Note: core:default and path:default are implicitly granted
    // for custom Tauri commands in Tauri 2.0
  ]
}
```

**Pros**:
- Zero code changes
- Documents the implicit model

**Cons**:
- Still implicit (harder to audit)
- Comment may confuse JSON parsers

**Effort**: 2 minutes
**Risk**: Low but not recommended

---

## Recommended Action

**Implement Solution 1 (Add Core and Path Permissions)** immediately.

This makes the security model explicit and clear. If Tauri 2.0 supports granular command permissions (Solution 2), upgrade to that in a future iteration.

## Technical Details

**Affected Files**:
- `frontend/src-tauri/capabilities/default.json` (add 2 permissions)

**Tauri 2.0 Permission System**:
- Capabilities files declare what frontend can access
- Custom commands may require `core:default` for IPC
- Path operations may require `path:default`
- Check Tauri docs for current best practices

**Testing Requirements**:
- App still starts correctly
- Custom command still works
- Dialog picker still works
- No permission errors in console

## Acceptance Criteria

- [ ] `core:default` permission added
- [ ] `path:default` permission added
- [ ] All existing functionality works
- [ ] No permission warnings in console
- [ ] Documentation updated if needed
- [ ] Security audit confirms explicit model

## Work Log

### 2026-02-13
- **Discovery**: Architecture review identified implicit permission model
- **Assessment**: P2 - not urgent but improves security clarity
- **Decision**: Add explicit permissions for auditability

## Resources

- **Tauri 2.0 Capabilities**: https://tauri.app/v2/reference/config/#capabilities
- **Tauri Security Best Practices**: https://tauri.app/v2/security/
- **Principle of Least Privilege**: https://en.wikipedia.org/wiki/Principle_of_least_privilege
