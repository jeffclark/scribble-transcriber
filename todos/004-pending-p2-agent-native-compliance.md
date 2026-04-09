---
status: pending
priority: p2
issue_id: "004"
tags: [code-review, architecture, agent-native, api]
dependencies: []
---

# Agent-Native Compliance - Make "Open Folder" Accessible to Agents

## Problem Statement

The "Open Folder" feature is UI-only with no agent equivalent. Agents cannot help users navigate to folders, violating the agent-native principle: **any action a user can take, an agent should be able to take**.

**Location**: Entire feature - no agent tool exists

**Why It Matters**: Users may ask agents "show me where my transcripts are" or "I want to see my files", but the agent has no way to help. This creates a capability gap and poor user experience.

## Findings

### From Agent-Native Reviewer

**Current State**:
- ✅ User can click "Open Folder" button in UI
- ❌ Agent cannot trigger folder opening
- ❌ Agent doesn't know what folders exist
- ❌ Agent doesn't know this capability exists
- ❌ No API endpoint for this action

**The "Write to Location" Test**: FAILS
If user says "show me where my transcripts are", agent cannot:
- Open the folder (no tool)
- Even tell user the path (no context injection)

**Agent-Native Score**: 0/1 capabilities accessible

## Proposed Solutions

### Solution 1: Add API Endpoint + Agent Tool (Full Parity)

**Backend API** (`backend/src/routes/folders.py`):
```python
from fastapi import APIRouter, HTTPException
import subprocess
import platform
from pathlib import Path

router = APIRouter()

ALLOWED_PATHS = [
    Path("/Users/jeffclark/projects/video-transcriber/transcripts"),
    Path("/Users/jeffclark/projects/video-transcriber/uploads"),
]

@router.post("/api/folders/open")
async def open_folder(path: str):
    folder_path = Path(path).resolve()

    # Validate path is within allowed directories
    if not any(folder_path.is_relative_to(allowed) or folder_path == allowed
               for allowed in ALLOWED_PATHS):
        raise HTTPException(status_code=403, detail="Path not allowed")

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    # Open folder based on platform
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(folder_path)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", str(folder_path)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(folder_path)], check=True)
        else:
            raise HTTPException(status_code=501, detail="Platform not supported")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {e}")

    return {
        "success": True,
        "message": f"Opened {folder_path.name} in file explorer"
    }
```

**Agent Tool Definition**:
```typescript
// In agent system prompt or tools file
{
  name: "open_folder",
  description: "Opens a folder in the user's native file explorer (Finder/Explorer)",
  input: {
    path: z.string().describe("Absolute path to folder to open")
  },
  execute: async ({ path }) => {
    const response = await fetch('http://localhost:8765/api/folders/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    if (!response.ok) {
      throw new Error(`Failed to open folder: ${await response.text()}`);
    }
    return await response.json();
  }
}
```

**System Prompt Addition**:
```
You can open folders in the user's file explorer using the open_folder tool.

Available folders:
- Transcripts: /Users/jeffclark/projects/video-transcriber/transcripts
- Uploads: /Users/jeffclark/projects/video-transcriber/uploads

Use this when users ask:
- "Where are my transcripts saved?"
- "Show me the upload folder"
- "I want to see the files"
- "Open the folder with my transcriptions"
```

**Pros**:
- Full action parity with UI
- Agents can complete user intent end-to-end
- Better UX: "Show me my transcripts" → Agent opens folder automatically
- Consistent with API-first architecture

**Cons**:
- Requires backend API endpoint
- Security: agents triggering system actions
- May surprise users with unexpected folder openings

**Effort**: 2-3 hours
**Risk**: Medium - adds new attack surface

---

### Solution 2: Hybrid Approach - Suggest Actions (Recommended)

**Agent Tool** (suggests but doesn't execute):
```typescript
{
  name: "suggest_open_folder",
  description: "Suggest opening a folder and provide instructions to user",
  input: {
    path: z.string(),
    reason: z.string().describe("Why this folder would be helpful")
  },
  execute: async ({ path, reason }) => {
    return {
      message: `${reason}\n\nTo view these files, click the "Open Folder" button or navigate to: ${path}`,
      action: {
        type: "open_folder",
        path,
        ui_hint: "show_open_folder_button"
      }
    };
  }
}
```

**System Prompt Addition**:
```
When users ask where files are located, use the suggest_open_folder tool.

Available folders:
- Transcripts: /Users/jeffclark/projects/video-transcriber/transcripts
- Uploads: /Users/jeffclark/projects/video-transcriber/uploads

Example usage:
User: "Where are my transcripts?"
Agent: [calls suggest_open_folder with path and reason]
Response: "Your transcripts are saved to /Users/.../transcripts.
Click the 'Open Folder' button to navigate there."
```

**Pros**:
- Agent has context parity (knows folders exist)
- User stays in control (agent suggests, doesn't execute)
- No security concerns
- Simpler implementation

**Cons**:
- Not full action parity
- User needs to click button

**Effort**: 1-2 hours
**Risk**: Low

---

### Solution 3: Minimum Viable - Context Injection Only

**System Prompt Addition**:
```
The app has an "Open Folder" button that opens folders in the native file explorer.

Folder locations:
- Transcripts: /Users/jeffclark/projects/video-transcriber/transcripts
- Uploads: /Users/jeffclark/projects/video-transcriber/uploads

When users ask where files are, provide the path and mention they can use
the "Open Folder" button to navigate there.
```

**Additional Tool** (list folders):
```typescript
{
  name: "list_folders",
  description: "Get paths to important app folders",
  execute: async () => ({
    transcripts: "/Users/jeffclark/projects/video-transcriber/transcripts",
    uploads: "/Users/jeffclark/projects/video-transcriber/uploads"
  })
}
```

**Pros**:
- Zero code changes
- Agents have context (can tell users where files are)
- No security concerns

**Cons**:
- No action parity at all
- Weakest solution

**Effort**: 30 minutes
**Risk**: Very low

---

## Recommended Action

**Implement Solution 2 (Hybrid Approach)** for balance between functionality and security.

This gives agents the ability to help users find folders while keeping the user in control of system actions.

Consider upgrading to Solution 1 (full API) in Phase 3 if user feedback shows agents should trigger actions directly.

## Technical Details

**Affected Files** (Solution 2):
- System prompt or agent configuration (add context about folders)
- Agent tools definition (add suggest_open_folder tool)
- Optional: Frontend to render suggested actions as clickable buttons

**Testing Requirements**:
- Agent can tell user where folders are
- Agent suggests opening folder when appropriate
- Paths are accurate
- Works for both transcripts and uploads folders

## Acceptance Criteria

- [ ] Agent knows what folders exist
- [ ] Agent can suggest opening folders
- [ ] Agent provides accurate paths
- [ ] User receives clear instructions
- [ ] Optional: UI renders action suggestions as buttons
- [ ] Agent doesn't trigger system actions without user confirmation

## Work Log

### 2026-02-13
- **Discovery**: Agent-native review identified capability gap
- **Assessment**: P2 - not security critical but impacts UX
- **Decision**: Implement hybrid approach (Solution 2)

## Resources

- **Agent-Native Architecture**: docs/agent-native-principles.md
- **System Prompt Template**: .claude/system-prompt.md
- **Agent Tools API**: docs/agent-tools.md
