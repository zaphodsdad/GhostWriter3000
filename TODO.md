# Prose Pipeline - TODO

**Last Updated:** 2026-01-14

---

## Completed

- [x] **1.1** Fix generation prompt - add "output only prose, no preamble"
- [x] **1.2** Post-processing cleanup - `clean_prose_output()` strips AI preambles
- [x] **2.1** Data directory picker - UI to configure project storage location
- [x] **6.3** Word count goals and tracking with progress bar
- [x] Dynamic model selection - fetch available models from OpenRouter API
- [x] Default model settings - configure preferred generation/critique models
- [x] Editable generation preview - tweak scene outline before generating
- [x] Scene form modal - better UX for scene editing
- [x] OpenRouter credits display - show remaining balance near word count
- [x] Credit low alerts - configurable threshold, toast notifications
- [x] UI refresh after Accept as Canon - sidebar/structure updates immediately

---

## Phase 1: Quick Wins

- [ ] **1.3** Clean up Scene 2's existing artifact in The Garden project (manual fix)

---

## Phase 2: Structural Improvements

- [ ] **2.2** Startup validation - check API key validity on boot, fail fast with clear error
- [ ] **2.3** Error recovery - retry logic for LLM failures, stuck-state recovery

---

## Phase 3: Frontend Polish

- [ ] **3.1** Subtle animations/transitions
- [ ] **3.2** Typography refinement
- [ ] **3.3** Visual hierarchy improvements
- [ ] **3.4** Accent color options / theme variants

---

## Phase 4: Continuity System Activation

- [ ] **4.1** Wire up `previous_scene_ids` in scene form (UI exists, needs linking)
- [ ] **4.2** Auto-suggest scene linking based on chapter/scene order
- [ ] **4.3** Display previous scene summaries in generation context
- [ ] **4.4** Add characters/world to The Garden project

---

## Phase 5: Robustness

- [ ] **5.1** Cost tracking - tokens per generation, running totals (credits balance done, per-gen tracking remaining)
- [ ] **5.2** Backup system - auto-backup before overwrites
- [ ] **5.3** Version history for prose iterations
- [ ] **5.4** Unit tests for services
- [ ] **5.5** Integration tests for API

---

## Phase 6: Additional Features

- [ ] **6.1** Search across scenes/characters/world
- [ ] **6.2** Export - compile project to markdown/docx/epub
- [ ] **6.4** Websockets for real-time generation status (currently polling)
- [ ] **6.5** Undo/redo for prose edits
- [ ] **6.6** Drag-and-drop scene reordering

---

## Ideas / Future

*Add new feature ideas here for later consideration*

---

## Notes

- The Garden: Test project with 6 scenes, 2 canon
- The Crimson Rites: Book 2 in "On Storms and Tides" series, 160+ scenes imported, no prose yet
- Continuity system (Phase 4) is key for generating prose with proper context
