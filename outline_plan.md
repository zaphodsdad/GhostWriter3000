# Outline Module - Planning Document

**Last Updated:** 2026-01-16

---

## Executive Summary

The Outline Module enables structured story planning before prose generation. Two modes serve different users:

- **Guided Mode**: Conversational, human-driven creation for quality-focused writers
- **Auto Mode**: Seed-to-structure generation for speed-focused users

Both modes share the same engine and benefit from the core prose philosophy (no AI tells, human-quality output).

---

## Core Philosophy

### Human-AI Boundary

| AI CAN | AI CANNOT |
|--------|-----------|
| Propose options | Make final decisions |
| Analyze/critique | Lock anything as canon |
| Expand drafts | Advance series state |
| Flag dependencies | Generate prose from uncommitted outline |

### Design Principles

1. **Buttons over prompts** - Constrained actions ("Propose Act Turn") beat open-ended chat
2. **Scene-first** - Allow orphan scenes; placement comes later
3. **Outlines are fluid** - No rigid canon-locking during planning
4. **Quality foundation** - Prose philosophy applies to outline generation too

---

## Data Model

### Hierarchy

```
Series (optional)
  └── Book (Project)
        └── Act
              └── Chapter
                    └── Scene
                          └── Beat (planning only)
```

### New/Extended Fields

**Scene gains:**
```
- beats: []           # Ordered list of beat objects (planning phase)
- depends_on: []      # Scene IDs or tags this depends on
- status: string      # idea, draft, ready (for generation)
```

**Beat object:**
```
- id: string
- text: string        # What happens
- notes: string       # Writer's notes
- tags: []            # For dependency tracking
```

### Key Insight: Beat Lifecycle

- Beats exist in the **Outline Module** for planning
- Beats are **accessible** to the Writing/Editing Module (inform generation)
- Beats are **not displayed** in Writing/Editing Module (scene is atomic unit there)

---

## Series Continuity

### What Becomes Canon

- **Written book summaries** - After completing a book, chapter/book summaries become canon
- **Series bible** - Maintained reference doc with arcs, threads, rules

### Storage Approach

Start with structured markdown in the existing References system:

```markdown
## Active Arcs
- Elena's revenge (started Book 1, unresolved)
- The succession crisis (Book 2 setup)

## Open Threads
- Who killed Marcus? (Book 1, Chapter 3)
- What's in the sealed vault? (Book 1, Chapter 12)

## World Rules
- Magic requires blood price
- No one can enter the Dead City twice
```

Human-readable + parseable. Can evolve to structured JSON later if needed.

---

## Workflow

### Guided Mode (Primary)

```
1. SEED
   - Import prior-book summaries + active arcs
   - User provides premise/hook/characters

2. PROPOSE
   - AI suggests options (beats, turns, scenes)
   - NOT decisions - multiple alternatives presented

3. STRESS-TEST
   - Continuity checks (does this contradict earlier events?)
   - Stakes audit (are stakes escalating?)
   - Promise-keeping (are setups getting payoffs?)

4. SELECT
   - Human picks option(s) from proposals
   - Human can modify, combine, or reject all

5. EXPAND
   - AI elaborates chosen elements
   - Scene → Beats, Beat → Details

6. ITERATE
   - Repeat as needed
   - Outlines are fluid, changes are normal
```

### Auto Mode (Secondary)

```
1. SEED
   - User provides hook/premise/synopsis
   - More seed material = better output

2. GENERATE
   - AI produces full structure as PROPOSALS
   - Acts → Chapters → Scenes (staged, not all at once)

3. REVIEW
   - Human reviews each element
   - Accept / Reject / Modify
   - Nothing commits without human approval

4. REFINE
   - Use guided mode to improve accepted elements
```

**Auto mode is essentially guided mode with AI answering its own questions.**

---

## Automation Features (Priority Order)

### Ship First

1. **Context assembly** - Auto-select relevant series canon per scene
2. **Continuity checks** - Flag timeline/arc contradictions
3. **Option generation** - 3-5 alternatives per decision point

### Ship Second

4. **Dependency tracking** - Tag-based linking (like Obsidian)
   - Explicit tags: `#letter-discovery`, `#marcus-death`
   - System tracks what touches what
   - Editing upstream flags downstream for review

5. **Escalation audit** - Are stakes rising through the story?

### Ship Later

6. **AI-detected dependencies** - Implicit linking based on shared elements
7. **What-if exploration** - Branch outlines to explore alternatives

---

## Interaction Patterns

### Specific Action Buttons

- "Propose Act Turn"
- "List risks/conflicts"
- "Generate 3 beat variants"
- "What threads does this touch?"
- "Expand scene → beats"
- "Check continuity"
- "Stress-test this choice"

### NOT a "Generate Outline" Button

Auto mode exists but is clearly labeled as scaffold generation requiring review.

---

## UX Rules

1. **Scene-first** - Can create orphan scenes, place them later
2. **Drag/reorder freely** - Structure is malleable
3. **Visual indicators**:
   - Uncommitted decisions count
   - Dependency links
   - Scenes ready for prose generation
4. **All entry points supported**:
   - Top-down (Act → Chapter → Scene → Beat)
   - Bottom-up (Scene idea → place later)
   - Import existing (add beats to flesh out)

---

## Exit Criteria to Prose

Scene is ready for prose generation when it has:

- [ ] Purpose (why does this scene exist?)
- [ ] Stakes (what's at risk?)
- [ ] Beats (what happens, in order)
- [ ] Dependencies resolved (no broken links)

No strict "lock" - if minimum criteria met, generate button works.

---

## Build Order

### Phase 1: Foundation
- Extend Scene model with beats, depends_on, status
- Beat CRUD operations
- Basic UI for viewing/editing beats within scenes

### Phase 2: Guided Mode
- Outline-aware chat context
- Structured question flows
- AI can propose/create outline elements
- Action buttons for common operations

### Phase 3: Series Continuity
- Series bible reference document support
- Book summary → canon flow after completion
- Context assembly for cross-book awareness

### Phase 4: Dependencies
- Tag-based linking system
- Dependency visualization
- Upstream change → downstream flag

### Phase 5: Auto Mode
- Seed input UI
- Staged generation (acts, then chapters, then scenes)
- Review/approval flow
- Proposal → accepted structure

### Phase 6: Advanced Analysis
- Continuity checking
- Escalation audit
- AI-detected dependencies

---

## Two Audiences

### Quality-Focused Writers (Primary)
- Use guided mode
- Approve everything manually
- Iterate and revise
- Care about craft
- **This is what we build first and use ourselves**

### Speed-Focused Users (Secondary)
- Use auto mode
- Generate scaffolds quickly
- May or may not refine
- Care about output volume
- **This is what sells**

Both benefit from the prose philosophy foundation. The quality layer helps everyone.

---

## UX Decision: Start Page & Navigation

**Decided:** Option A - Outline is a view within a project

```
Start Page: [Projects] [Series] [+ New Project] [+ New Series]
                                      ↓
                         "Start from outline" checkbox
     ↓
Open Project → Tabs: [Structure] [Outline] [Workspace] [References]
```

- Outline is a tab/view within a project (same project, different mode)
- New projects can start in "Outline Only" mode via checkbox
- Series get an "Arc Planning" section (series-level outline as reference doc)
- Standalone outlines = projects with "outline only" flag, can be promoted later

---

## Open Questions

1. **Beat editor UI** - Inline in scene view? Separate panel? Modal?
2. **Dependency visualization** - Graph view? List view? Both?
3. **Auto mode pricing** - More tokens = more cost. Tier it?
4. **Guided mode prompts** - What's the ideal question sequence?

---

## Related Documents

- `CLAUDE.md` - Full project context and architecture
- `TODO.md` - Current task tracking
- `backend/app/utils/prompt_templates.py` - Prose philosophy constants
