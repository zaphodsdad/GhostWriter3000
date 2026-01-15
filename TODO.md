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

---

## DONE: Continuity System ✅

*Foundation for multi-scene generation. Without this, scene 50 doesn't know what happened in scenes 1-49.*

- [x] Auto-calculate previous scenes based on act → chapter → scene order
- [x] Include last 10 canon scene summaries in generation context
- [x] Works for both normal generation and edit mode
- [ ] (Future) Add chapter-level summaries for longer books

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

**To add:**
- [ ] Side-by-side view - original vs revised
- [ ] Selective revision - apply some critique points, ignore others
- [ ] Consistency pass - critique focused on continuity errors across scenes
- [ ] Polish mode - lighter touch revision (line edits vs structural)
- [ ] Track changes style diff view

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

## Backlog: Infrastructure & Polish

*Nice to have, not blocking main workflow.*

### Structural
- [ ] Startup validation - check API key on boot, fail fast
- [ ] Error recovery - retry logic, stuck-state recovery
- [ ] Cost tracking - tokens per generation, running totals

### Robustness
- [ ] Backup system - auto-backup before overwrites
- [ ] Version history for prose iterations
- [ ] Unit tests for services
- [ ] Integration tests for API

### Frontend Polish
- [ ] Subtle animations/transitions
- [ ] Typography refinement
- [ ] Visual hierarchy improvements
- [ ] Accent color options / theme variants

### Additional Features
- [ ] Search across scenes/characters/world
- [ ] Export - compile project to markdown/docx/epub
- [ ] Websockets for real-time generation status
- [ ] Undo/redo for prose edits
- [ ] Drag-and-drop scene reordering

---

## Project Notes

- **The Jade Vow** - Book 1, published on KDP
- **The Crimson Rites** - Book 2, 160+ scenes imported, ready for generation
- **On Storms and Tides** - Series name
- **Magnet novella** - needs to be uploaded to reference materials
