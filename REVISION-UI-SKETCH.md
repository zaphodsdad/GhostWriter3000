# Revision UI Design Sketch

## Current Pain Points

1. **Blind revisions** - AI rewrites prose, you see the result but not *what changed*
2. **All-or-nothing** - Can't say "revise just this paragraph"
3. **No hybrid editing** - Can't mix manual edits with AI revisions
4. **Lost context** - Hard to compare versions during the revision loop

---

## Proposed UI: Three-Panel Revision View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Scene: Into the Temple]                    [Version 3 of 5]  [Close] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐ │
│  │   CURRENT PROSE     │  │    DIFF VIEW        │  │   CRITIQUE      │ │
│  │                     │  │                     │  │                 │ │
│  │ The temple doors    │  │ The temple doors    │  │ ## Issues       │ │
│  │ groaned as Elena    │  │ groaned as Elena    │  │                 │ │
│  │ pushed them open.   │  │ pushed them open.   │  │ 1. Opening      │ │
│  │ Inside, shadows     │  │ Inside, [-shadows-] │  │ paragraph is    │ │
│  │ pooled like ink     │  │ [+darkness+]        │  │ generic         │ │
│  │ between the         │  │ pooled like ink     │  │                 │ │
│  │ columns.            │  │ between the         │  │ 2. "Shadows     │ │
│  │                     │  │ [-columns-]         │  │ pooled" is      │ │
│  │ She stepped         │  │ [+ancient pillars+] │  │ cliché          │ │
│  │ forward, her        │  │                     │  │                 │ │
│  │ footsteps echoing   │  │ She stepped         │  │ 3. Missing      │ │
│  │ in the vast         │  │ forward, her        │  │ sensory detail  │ │
│  │ emptiness.          │  │ footsteps echoing   │  │ (smell, temp)   │ │
│  │                     │  │ in the vast         │  │                 │ │
│  │ [Select text to     │  │ emptiness.          │  │ ## Strengths    │ │
│  │  request revision]  │  │                     │  │                 │ │
│  │                     │  │ [+The air tasted    │  │ - Good pacing   │ │
│  │                     │  │ of dust and         │  │ - Clear POV     │ │
│  │                     │  │ centuries.+]        │  │                 │ │
│  │                     │  │                     │  │                 │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Revision Instructions (optional):                                 │  │
│  │ [Focus on the second paragraph - make the imagery less cliché   ]│  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  [Apply All Changes]  [Revise Again]  [Revise Selection]  [Accept Canon]│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. Diff View (Center Panel)

Shows changes between current version and AI's proposed revision:
- **Deletions**: Red background, strikethrough
- **Insertions**: Green background
- **Unchanged**: Normal text

User can:
- See exactly what AI changed
- Click individual changes to accept/reject them (future enhancement)

### 2. Selection-Based Revision (Left Panel)

User selects text in the current prose panel:
- Selection highlighted in blue
- "Revise Selection" button becomes active
- Only selected portion sent to AI for revision
- Rest of prose preserved exactly

**API Addition Needed:**
```
POST /api/projects/{id}/generations/{gen_id}/revise-selection
{
  "start_index": 145,
  "end_index": 312,
  "instructions": "Make this less cliché"
}
```

### 3. Revision Instructions Box

Optional text field to guide the revision:
- "Focus on dialogue"
- "Add more sensory details"
- "Shorten this section"
- "Match the tone of chapter 1"

Instructions appended to the critique when requesting revision.

### 4. Version Navigation

Simple version history:
```
[< Prev]  Version 3 of 5  [Next >]
```
- Jump between iterations
- Compare any two versions (future)

---

## Workflow Changes

### Before (Current)
```
Generate → See prose → See critique → "Approve & Revise" → See new prose → Repeat
                                              ↓
                                     (No idea what changed)
```

### After (Proposed)
```
Generate → See prose + critique side-by-side
              ↓
         See DIFF of proposed changes
              ↓
         Choose: Accept All | Revise Again | Revise Selection | Manual Edit
              ↓
         If revising: Add optional instructions
              ↓
         See new DIFF → Repeat until satisfied
              ↓
         Accept as Canon
```

---

## Technical Components Needed

### 1. Diff Library
**jsdiff** (small, focused):
```javascript
import * as Diff from 'diff';

const changes = Diff.diffWords(oldText, newText);
// Returns array: [{value: "text", added: true/false, removed: true/false}, ...]
```

### 2. Diff Renderer
Convert diff output to HTML:
```javascript
function renderDiff(changes) {
  return changes.map(part => {
    if (part.added) return `<ins class="diff-add">${part.value}</ins>`;
    if (part.removed) return `<del class="diff-del">${part.value}</del>`;
    return `<span>${part.value}</span>`;
  }).join('');
}
```

### 3. Selection Tracking
Capture user's text selection:
```javascript
const selection = window.getSelection();
const range = selection.getRangeAt(0);
const selectedText = selection.toString();
// Map back to character indices in original prose
```

### 4. Backend Changes

**Store revision history in generation state:**
```json
{
  "iterations": [
    {
      "prose": "...",
      "critique": "...",
      "revision_instructions": "Focus on dialogue",
      "revised_prose": "...",
      "diff_summary": {
        "additions": 45,
        "deletions": 23,
        "changes": 12
      }
    }
  ]
}
```

**New endpoint for selective revision:**
```python
@router.post("/{generation_id}/revise-selection")
async def revise_selection(
    project_id: str,
    generation_id: str,
    request: SelectionRevisionRequest
):
    """Revise only a portion of the prose."""
    # Extract selection from current prose
    # Send selection + context to Claude
    # Splice revised selection back into full prose
    # Return diff
```

---

## CSS Styling

```css
/* Diff highlighting */
.diff-add {
  background: rgba(46, 160, 67, 0.2);
  text-decoration: none;
}

.diff-del {
  background: rgba(248, 81, 73, 0.2);
  text-decoration: line-through;
}

/* Selection for revision */
.revision-selection {
  background: rgba(56, 139, 253, 0.2);
  border-bottom: 2px solid var(--primary);
}

/* Three-panel layout */
.revision-view {
  display: grid;
  grid-template-columns: 1fr 1fr 300px;
  gap: 20px;
  height: calc(100vh - 200px);
}

.revision-panel {
  overflow-y: auto;
  padding: 20px;
  background: var(--bg-card);
  border-radius: 8px;
}
```

---

## Implementation Phases

### Phase 1: Diff View (Immediate Value)
- Add jsdiff library
- Show diff between current prose and revision in generation view
- No backend changes needed

### Phase 2: Revision Instructions
- Add text input for guiding revisions
- Pass instructions to revision prompt
- Minor backend change

### Phase 3: Selection-Based Revision
- Track text selection in prose panel
- New API endpoint for partial revision
- Claude prompt engineering for preserving context

### Phase 4: Inline Accept/Reject
- Click individual changes to toggle
- Build "merged" prose from accepted changes
- More complex state management

---

## Questions to Resolve

1. **Diff granularity**: Word-level or sentence-level? Paragraph-level?
   - Word-level: More precise but noisy
   - Sentence-level: Cleaner but may miss small changes
   - Recommendation: Word-level with option to toggle

2. **Selection revision scope**: How much context to send to Claude?
   - Just the selection? (Fast, but may lose voice consistency)
   - Selection + surrounding paragraphs? (Better results)
   - Full scene with selection marked? (Most context, most tokens)
   - Recommendation: Selection + 1 paragraph before/after

3. **Version storage**: Keep all iterations or just last N?
   - Current: Stores all in generation state
   - Could get large with many revisions
   - Recommendation: Keep all, they're useful for comparison

---

## Next Steps

1. Prototype Phase 1 (diff view) in current generation modal
2. Test with real revision workflow
3. Iterate on UX before building selection features
