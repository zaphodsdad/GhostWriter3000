# Prose Pipeline - TODO

**Last Updated:** 2026-01-15

---

## Roadmap

The full creative workflow: **OUTLINE → GENERATE → EDIT**

| Module | Status | Priority |
|--------|--------|----------|
| **Continuity System** | Complete | Done |
| **Generation** | Working | Done |
| **Editing Module** | In Progress | **NOW** |
| **UX Simplification** | Planned | **NEXT** |
| **Outlining Module** | Not started | Future |

---

## Completed

- [x] Fix generation prompt - add "output only prose, no preamble"
- [x] Post-processing cleanup - `clean_prose_output()` strips AI preambles
- [x] Data directory picker - UI to configure project storage location
- [x] Word count goals and tracking with progress bar
- [x] Dynamic model selection - fetch available models from OpenRouter API
- [x] Default model settings - configure preferred generation/critique models
- [x] Editable generation preview - tweak scene outline before generating
- [x] Scene form modal - better UX for scene editing
- [x] OpenRouter credits display - show remaining balance near word count
- [x] Credit low alerts - configurable threshold, toast notifications
- [x] UI refresh after Accept as Canon - sidebar/structure updates immediately
- [x] Series system - group books, share characters/world
- [x] Reference library - import documents as AI context
- [x] Basic edit mode - import prose, run through critique loop
- [x] Continuity system - auto-include last 10 scene summaries
- [x] Manuscript import - upload .docx/.txt/.md, auto-split chapters, create scenes in edit mode
- [x] Floating AI revision bubble - select text in reading view for inline AI editing
- [x] Canon toggle from reading view - mark/unmark scenes as canon without entering edit mode
- [x] Inline accept/reject in diff view - cherry-pick AI changes before applying
- [x] Polish mode - lighter touch revision (line edits vs structural)
- [x] Generation dropdown sorted by chapter/scene order

---

## NOW: Editing Module

*Revise existing prose through the critique loop.*

**What exists:**
- Single-scene edit mode (import prose, skip to critique)
- Critique → revise loop works
- **Manuscript import** - upload .docx/.txt/.md files (mammoth for .docx)
- **Auto chapter detection** - splits by "Chapter 1", "CHAPTER ONE", etc.
- **Bulk scene creation** - each chapter becomes a Chapter + Scene in edit mode
- **Edit mode display** - imported prose visible in reading pane with "Edit Mode - Ready for Critique" status
- **Backup on prose edit** - auto-backup before manual prose changes
- **Polish mode** - choose between full structural revision or light line edits

### Remaining Editing Features

- [ ] Consistency pass - critique focused on continuity errors across scenes
- [ ] Side-by-side version comparison (pick any two versions)
- [ ] Evaluate-only mode - get critique report without entering revision loop

---

## NEXT: UX Simplification

*Simplify the interface by unifying workflows and moving global settings.*

### Global Settings to Start Page

- [ ] Move API configuration to start page (not buried in project settings)
- [ ] API provider selection (Anthropic vs OpenRouter)
- [ ] API key entry with validation
- [ ] Default model selection
- [ ] Credit balance display (OpenRouter)
- [ ] Data directory configuration

### Unified Scene Workspace

*Merge Generate tab and Reading View into one adaptive workspace.*

- [ ] Remove separate Generate tab
- [ ] Click any scene in sidebar → opens unified workspace
- [ ] Workspace adapts based on scene state:
  - No prose: show outline + "Generate" / "Import Prose" buttons
  - Has prose (not canon): show prose + floating bubble + revision options
  - Has prose (canon): show prose + "Evaluate" (mostly read-only)
  - Currently generating: show progress
  - Awaiting approval: show prose + critique + approve/revise/accept
- [ ] Model selection and revision mode in collapsible settings panel
- [ ] Floating AI bubble works everywhere
- [ ] "Evaluate" button for critique-only feedback
- [ ] Status badges in sidebar (empty, has prose, canon, generating)

### Import Reorganization

- [ ] Manuscript import stays in Structure → Import
- [ ] Single-scene prose import moves to unified workspace ("Import Prose" button)
- [ ] Character/Reference imports stay in their respective tabs

---

## FUTURE: Character & Series Management

- [ ] Promote book characters to series level
- [ ] Visual distinction between series vs book-only characters
- [ ] When creating character in series book: prompt for "Series-wide" vs "This book only"

---

## FUTURE: Outlining Module

*AI-assisted story planning. Currently outlines are imported manually.*

**Potential features:**
- [ ] Synopsis → Structure - expand premise into acts/chapters/scenes
- [ ] Beat sheet expansion - flesh out plot beats to scene outlines
- [ ] Pacing analysis - flag pacing issues, suggest beats
- [ ] POV planning - suggest POV character for each scene
- [ ] What-if exploration - explore alternate plot paths
- [ ] Scene card view - visual outline manipulation

---

## FUTURE: Export Module

- [ ] Export - compile project to markdown/docx/epub

---

## Backlog: Infrastructure & Polish

*Nice to have, not blocking main workflow.*

### Structural
- [ ] Startup validation - check API key on boot, fail fast
- [ ] Error recovery - retry logic, stuck-state recovery
- [ ] Cost tracking - tokens per generation, running totals

### Robustness
- [x] Backup system - auto-backup before overwrites
- [x] Version history for prose iterations
- [ ] Unit tests for services
- [ ] Integration tests for API

### Frontend Polish
- [ ] Subtle animations/transitions
- [ ] Typography refinement
- [ ] Visual hierarchy improvements
- [ ] Accent color options / theme variants

### Additional Features
- [ ] Search across scenes/characters/world
- [ ] Websockets for real-time generation status
- [ ] Undo/redo for prose edits
- [ ] Drag-and-drop reordering (chapters and scenes)
- [ ] (Future) Chapter-level summaries for longer books

---

## Project Notes

- **The Jade Vow** - Book 1, published on KDP
- **The Crimson Rites** - Book 2, 160+ scenes imported, ready for generation
- **On Storms and Tides** - Series name
- **Magnet novella** - needs to be uploaded to reference materials
