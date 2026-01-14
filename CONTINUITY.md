# Scene Summary & Continuity System

## Overview

The prose pipeline includes a **scene summary system** inspired by Novelcrafter's approach. When a scene's prose is accepted as canon, the system automatically generates a concise summary. Future scenes can reference these summaries to maintain continuity without consuming massive token budgets.

## Why Scene Summaries?

### The Problem
- A full novel scene is 1,500-2,000 words (~2,500 tokens)
- Including 10 previous scenes = ~25,000 tokens
- This quickly fills Claude's context window
- Leaves little room for character sheets, world context, and generation

### The Solution
- Compress each scene into a 300-500 word summary (~600 tokens)
- Include 10 previous summaries = ~6,000 tokens
- Maintain continuity while saving ~19,000 tokens
- Scale to dozens of scenes without token explosion

## How It Works

### The Complete Workflow

```
1. User creates scene outline
   ↓
2. Generate prose (with previous scene summaries in context)
   ↓
3. Critique prose
   ↓
4. User approves & revises (repeat N times)
   ↓
5. User clicks "Accept as Canon"
   ↓
6. ✨ System auto-generates scene summary
   ↓
7. Scene marked as canon, prose & summary saved
   ↓
8. Future scenes automatically include this summary
```

### State Flow Diagram

```
AWAITING_APPROVAL
     ├─ Approve → REVISING → ... (loop back)
     │
     └─ Accept as Canon → GENERATING_SUMMARY
                              ↓
                          COMPLETED
                          (prose + summary saved)
```

## Scene Model Structure

Each scene tracks:

```json
{
  "id": "scene-002",
  "title": "Into the Temple",
  "scene_number": 2,
  "outline": "...",
  "character_ids": ["elena-blackwood"],
  "world_context_ids": ["shattered-empire"],
  "previous_scene_ids": ["scene-001"],  // ← Continuity tracking
  "is_canon": false,                     // ← Becomes true when accepted
  "prose": null,                          // ← Saved when accepted
  "summary": null,                        // ← Auto-generated when accepted
  ...
}
```

### Key Fields

- **scene_number**: Sequential ordering (1, 2, 3...)
- **previous_scene_ids**: Which scenes come before this one
- **is_canon**: Whether this scene has been finalized
- **prose**: The final accepted prose text
- **summary**: Auto-generated 300-500 word summary

## Summary Generation

### What Goes in a Summary

The AI generates summaries that capture:

1. **Key Events** - What happened? What plot advanced?
2. **Character Development** - How did characters change or reveal themselves?
3. **Emotional Beats** - Key emotional moments
4. **World State Changes** - Changes to the world or setting
5. **Open Threads** - Unresolved questions or conflicts
6. **Continuity Details** - Specific facts that future scenes must remember

### Example Summary

**Scene: "Discovery in the Wastes"**

```
Elena's expedition team finally located the Lost Temple entrance buried
beneath the Wastes' shifting sands after weeks of following her late uncle's
cryptic journal entries. The discovery came at a cost - mid-excavation, Elena
spotted Cult of the Flame scouts watching from a distant ridge, their red
banners unmistakable against the desert sky.

Faced with the choice between retreating to safety or entering the temple
before the zealots could interfere, Elena made the impulsive decision her
team feared: she ordered immediate entry. Her uncle's compass pendant grew
warm against her skin as she approached the ancient doorway.

Key details: The temple entrance features three interlocking circles carved
in stone. The Cult is now aware of the location and will likely arrive within
hours. Elena's team includes three members (names TBD in future scenes). The
expedition is funded by the Archivist Council with a six-month deadline.
```

## Context Building for Future Scenes

When generating scene N, the system includes:

### In System Prompt:
```
# STORY SO FAR

## Discovery in the Wastes
[Summary from scene-001]

## Into the Temple
[Summary from scene-002]

... (other previous scenes)

# CHARACTER INFORMATION
[Character sheets]

# WORLD CONTEXT
[World building]
```

### Token Budget Example

```
Previous summaries (10 scenes): ~6,000 tokens
Character sheets (3 chars):     ~3,000 tokens
World context (2 contexts):     ~4,000 tokens
Scene outline:                  ~1,000 tokens
System/instruction prompts:     ~2,000 tokens
-------------------------------------------
Total context used:            ~16,000 tokens
Remaining for generation:     ~184,000 tokens ✅
```

## Scene Dependencies

### Linear Progression
Most scenes follow sequentially:

```
scene-001 (no previous scenes)
    ↓
scene-002 (previous: scene-001)
    ↓
scene-003 (previous: scene-002)
    ↓
scene-004 (previous: scene-003)
```

### Branching Narratives
Some scenes can reference multiple previous scenes:

```
       scene-001
         ↓   ↓
    scene-002 scene-003
         ↓   ↓
        scene-004
   (previous: scene-002, scene-003)
```

### Skipping Scenes
You can skip irrelevant scenes for continuity:

```
scene-010 (Fantasy battle)
scene-011 (Political intrigue)  ← Skip this
scene-012 (Return to battle)
(previous: scene-010)  ← References scene 10, not 11
```

## Implementation Details

### When Summary is Generated

Summary generation happens **automatically** when:
1. User clicks "Accept as Canon" button
2. Status changes from `AWAITING_APPROVAL` → `GENERATING_SUMMARY`
3. Claude API called with summary generation prompt
4. Summary saved to scene record
5. Scene marked as `is_canon: true`
6. Status changes to `COMPLETED`

### Summary Generation Prompt

```python
def build_summary_prompt(scene_title: str, prose: str) -> str:
    """Generate concise scene summary for continuity tracking."""
    # Prompts Claude to create 300-500 word summary
    # Captures key events, character development, emotional beats
    # Includes continuity details for future reference
```

### Retrieving Previous Summaries

```python
# When generating scene N
scene = load_scene("scene-N")
previous_scenes = []

for prev_id in scene.previous_scene_ids:
    prev_scene = load_scene(prev_id)
    if prev_scene.is_canon and prev_scene.summary:
        previous_scenes.append({
            "title": prev_scene.title,
            "summary": prev_scene.summary
        })

# Include in system prompt
system_prompt = build_system_prompt(
    characters=characters,
    world_contexts=world_contexts,
    previous_scene_summaries=previous_scenes  # ← Key addition
)
```

## Best Practices

### 1. Scene Numbering
Use sequential numbers even if you write out of order:
- `scene_number: 1, 2, 3, 4...`
- Helps sort scenes chronologically
- Makes reordering easier

### 2. Previous Scene IDs
**Always specify** which scenes come before:
- Even if it's just the previous number
- Empty array `[]` only for the very first scene
- Include all relevant previous scenes for continuity

### 3. Canon Status
**Only mark canon when truly final:**
- Once canon, the summary is generated
- Other scenes may start referencing it
- Changing canon scenes breaks continuity

### 4. Summary Review
**Check the auto-generated summary:**
- Ensure key details are captured
- Verify names, places, and facts are correct
- Edit if needed before moving to next scene

### 5. Token Budget Awareness
**Monitor context usage:**
- Each scene summary adds ~600 tokens
- Character sheets add ~1,000 tokens each
- World contexts add ~2,000 tokens each
- Keep total context under ~50,000 tokens for safety

## API Endpoints (Phase 4)

### Accept Scene as Canon
```
POST /api/generations/{id}/accept

Response:
{
  "status": "generating_summary",
  "message": "Generating scene summary..."
}

# Poll for completion
GET /api/generations/{id}
{
  "status": "completed",
  "final_prose": "...",
  "scene_summary": "..."
}
```

### Update Scene with Canon Data
```
PUT /api/scenes/{id}
{
  "is_canon": true,
  "prose": "...",
  "summary": "..."
}
```

## Future Enhancements

### Smart Summary Selection
Instead of including ALL previous scenes:
- Analyze current scene outline
- Identify which previous scenes are relevant
- Only include those summaries
- Further reduces token usage

### Summary Compression
For very long stories (100+ scenes):
- Generate chapter-level summaries
- Compress older scene summaries
- Keep recent scenes detailed, distant scenes brief

### Manual Summary Editing
Allow users to:
- Edit auto-generated summaries
- Add continuity notes
- Mark key details for emphasis

### Continuity Checking
AI assistant that:
- Checks new prose against previous summaries
- Flags continuity errors
- Suggests corrections

## Examples

### Example 1: Simple Sequence

**Scene 1:** "Discovery in the Wastes"
- `previous_scene_ids: []`
- Generate → Critique → Accept as Canon
- Summary auto-generated ✓

**Scene 2:** "Into the Temple"
- `previous_scene_ids: ["scene-001"]`
- System includes Scene 1 summary in context
- Generate prose that references the discovery
- Accept as Canon
- Summary auto-generated ✓

**Scene 3:** "The Guardian's Chamber"
- `previous_scene_ids: ["scene-002"]`
- System includes Scene 2 summary (Scene 1 is older, may skip)
- Or include both for stronger continuity
- Generate → Accept
- Summary auto-generated ✓

### Example 2: Multi-Book Series

**Book 1** (complete, all canon)
- Create book-level summary document
- Store in `data/continuity/book-summaries/book-01.md`
- Include in system prompt for Book 2

**Book 2 Scene 1**
- References Book 1 summary (not individual scenes)
- Start fresh scene numbering: 1, 2, 3...
- `previous_scene_ids: []` (first of new book)
- Include book-1 summary in world context

## Migration Path

### Current Projects
If you have scenes already generated:
1. Mark them as `is_canon: true`
2. Manually create summaries (or use Claude)
3. Add to scene records
4. Set up `previous_scene_ids`
5. Future scenes will automatically use them

### From Other Tools
Importing from Novelcrafter, Scrivener, etc:
1. Create scene JSON files
2. Add prose to `prose` field
3. Create summaries (manually or via API)
4. Set `is_canon: true`
5. Link scenes with `previous_scene_ids`

---

## Summary

The scene summary system provides **scalable continuity** for long-form prose generation:

✅ Compress 2,000-word scenes into 400-word summaries
✅ Save ~80% tokens while maintaining continuity
✅ Automatically generated when scenes are accepted
✅ Scale to dozens or hundreds of scenes
✅ Support multi-book series
✅ Preserve key details without token explosion

This is a **core feature**, not an afterthought. Built into the pipeline from day one.
