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

---

## Series Memory Layer

The **Series Memory Layer** complements scene summaries with accumulated knowledge extracted from canon scenes. While scene summaries provide a narrative recap of "what happened," the memory layer tracks structured facts about characters, world, and plot.

### Overview

```
Scene Summaries (above):     "What happened in each scene"
Series Memory Layer (below): "What we know about characters, world, and timeline"
```

### Storage Structure

```
data/series/{series-id}/
├── series.json              # Series metadata
├── memory/
│   ├── manifest.json        # Hashes, timestamps, extraction tracking
│   ├── character_states.md  # Current state of all characters
│   ├── world_state.md       # Established world facts by category
│   ├── timeline.md          # Chronological plot events
│   └── extractions/         # Raw extraction logs per scene
│       ├── {scene-id}.json
│       └── ...
```

### How It Works

#### 1. Extraction (Automatic on Mark as Canon)

When a scene is marked as canon, the system automatically extracts:

- **Character State Changes**: Emotional, physical, relational, knowledge, status changes
- **World Facts**: Locations, rules, history, culture elements established
- **Plot Events**: Key events for timeline tracking with ordering metadata

```json
{
  "scene_id": "scene-042",
  "book_id": "the-crimson-rites",
  "character_changes": [
    {
      "character": "Elena",
      "change_type": "emotional",
      "before": "Hopeful about the expedition",
      "after": "Wary after seeing the Cult scouts"
    }
  ],
  "world_facts": [
    {
      "category": "location",
      "fact": "The Lost Temple entrance features three interlocking circles carved in stone"
    }
  ],
  "plot_events": [
    {
      "event": "Elena's team discovered the Lost Temple",
      "significance": "major"
    }
  ]
}
```

#### 2. Summary Generation

The `/generate-summaries` endpoint synthesizes all extractions into readable markdown:

- **character_states.md**: Current state of each character across the series
- **world_state.md**: Organized world facts by category (locations, rules, culture, etc.)
- **timeline.md**: Chronological plot events

#### 3. Context Assembly

When generating new prose, the memory layer is automatically included:

```
System Prompt includes:
├── Style Guide
├── Characters (sheets)
├── World Context (documents)
├── References
├── Previous Books (summaries)
├── SERIES MEMORY ← NEW
│   ├── Character States
│   ├── World State
│   └── Timeline
└── Story So Far (scene summaries)
```

#### 4. Staleness Detection

When character or world files are modified, the system:
1. Detects hash changes via `check_staleness()`
2. Auto-regenerates summaries before next generation
3. Updates stored hashes

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/{series_id}/memory` | GET | Get complete memory state |
| `/{series_id}/memory/initialize` | POST | Initialize memory structure |
| `/{series_id}/memory/context` | GET | Get compact summaries for prompts |
| `/{series_id}/memory/staleness` | GET | Check if summaries are stale |
| `/{series_id}/memory/generate-summaries` | POST | Generate all summaries from extractions |
| `/{series_id}/memory/generate-book-summary` | POST | Generate book summary from memory |
| `/{series_id}/memory/extract` | POST | Save extraction results |
| `/{series_id}/memory/refresh-hashes` | POST | Refresh stored file hashes |
| `/{series_id}/memory` | DELETE | Clear all memory |

### Scene Summaries vs Memory Layer

| Aspect | Scene Summaries | Memory Layer |
|--------|-----------------|--------------|
| **Scope** | Per-scene narrative recap | Accumulated series knowledge |
| **Format** | Prose paragraph | Structured facts |
| **Generated** | On accept as canon | Synthesized from extractions |
| **Purpose** | "What happened in Scene 5?" | "What do we know about Elena?" |
| **Token Cost** | ~600 per scene | ~1,000-2,000 total for series |

### Best Practices

1. **Let Extraction Run**: Don't skip the background extraction when marking canon
2. **Regenerate Periodically**: Call `/generate-summaries` after marking several scenes
3. **Check Staleness**: Before major generation sessions, verify summaries aren't stale
4. **Use for Series**: Memory layer is most valuable for multi-book series continuity

### Deep Import (Implemented)

For importing existing manuscripts with full memory extraction:

**How to use:**
```bash
# Via API with deep_import=true
curl -X POST "http://localhost:8000/api/projects/{project_id}/manuscript/import-full" \
  -F "file=@manuscript.docx" \
  -F "deep_import=true"
```

**What happens:**
1. Manuscript is imported normally (chapters → scenes)
2. Background task starts extracting from each scene
3. Extractions run sequentially (1 sec delay to avoid rate limits)
4. When all scenes processed, auto-generates summaries

**Check progress:**
```bash
curl "http://localhost:8000/api/projects/{project_id}/manuscript/deep-import-status"
```

Returns:
```json
{
  "project_id": "my-book",
  "series_id": "my-series",
  "total_scenes": 20,
  "scenes_extracted": 15,
  "current_scene": "chapter-16-scene-1",
  "status": "running",
  "started_at": "2026-02-01T01:00:00"
}
```

**Requirements:**
- Project must be in a series (series_id set)
- Manuscript should have detectable chapter markers

**Cost consideration:**
- Each scene = 1 LLM extraction call
- 20-chapter book ≈ 20 API calls
- Use a cost-effective model for extraction

### Series-Level Entity Extraction (Implemented)

Deep import now extracts **characters and world elements** to the **series level**, not the book level.

**How it works:**

1. **Entity Extraction Phase** (once per book):
   - Gathers all prose from imported scenes
   - Extracts characters and world elements via LLM
   - Saves to `data/series/{series-id}/characters/` and `data/series/{series-id}/world/`

2. **Merge Logic** (always additive):
   - If character/world element already exists (by name), appends new facts
   - Never overwrites existing information
   - Tags each fact with `book_number` for chronology

3. **Memory Extraction Phase** (per scene):
   - Extracts plot events, character state changes, world facts
   - Saves to memory layer as before

**File format:**
```markdown
---
name: Elias
role: protagonist
first_seen_book: 0
books_appeared: [0, 1, 2]
created_from: her-majestys-dragon-lancer
last_updated: '2026-02-01T02:54:59'
---

## Physical Description
Tall, dark hair, grey eyes

## Personality
Brooding, strategic, protective

## Relationships
- **Beatrix**: dragon companion
- **Kira**: former love interest (deceased Book 0)
- **Atla**: new love interest (Book 2)

---
*Initial extraction from Book 0 (her-majestys-dragon-lancer)*

## Book 1 Updates (the-jade-vow)
**Traits**: grieving, determined
**Relationship with Atla**: growing trust
**Notes**: Still healing from Kira's death

## Book 2 Updates (the-crimson-rites)
**Traits**: conflicted, protective
**Relationship with Atla**: romantic tension
**Notes**: Must choose between duty and love
```

**Benefits:**
- Characters defined once, evolve across series
- No duplicate entity files per book
- `book_number` enables chronological understanding
- Memory layer handles "what matters now" via decay (future)
