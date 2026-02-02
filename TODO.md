# Prose Pipeline - TODO

**Last Updated:** 2026-02-02

---

## PRIORITY: Series Memory Layer (Persistent Context)

**Goal:** Build a memory system that persists across generations and works with any model (not just Anthropic's prompt caching). Knowledge accumulates as you write.

### Architecture

```
data/series/{series-id}/
├── series.json              # existing metadata
├── memory/
│   ├── manifest.json        # hashes, last-updated timestamps
│   ├── world_state.md       # summarized lore/rules (auto-generated)
│   ├── character_states.md  # current state of all characters
│   ├── timeline.md          # key plot events in order
│   └── extractions/         # raw extraction logs
```

### Core Concept

**On Generation:**
- Assemble prompt from cached summaries + small delta (current scene + instruction)
- Works with any model (OpenRouter, local, etc.)
- Context stays compact via intelligent summarization

**On Mark as Canon:**
- Run extraction pass: "What changed in this scene?"
- Extract: character state changes, new world facts, plot events
- Merge into series memory
- Regenerate summaries if needed

**On Source File Change:**
- Hash detects staleness
- Auto-regenerate summary before next use

### Implementation Phases

- [x] **Phase 1: Storage Structure** - COMPLETE 2026-02-01
  - Create `memory/` directory structure in series
  - `manifest.json` with hashes and timestamps
  - Initial empty state files
  - API endpoints for memory CRUD

- [x] **Phase 2: Extraction Pass** - COMPLETE 2026-02-01
  - LLM prompt to extract facts from canon scene
  - Hook into "Mark as Canon" flow (background task)
  - Store raw extractions per scene
  - Extracts: character changes, world facts, plot events

- [x] **Phase 3: Summary Generation** - COMPLETE 2026-02-01
  - Generate `character_states.md` from character files + extractions
  - Generate `world_state.md` from world files + extractions
  - Generate `timeline.md` from plot events
  - API endpoints: POST generate-summaries, POST generate-book-summary
  - UI integration pending (API ready)

- [x] **Phase 4: Context Assembly** - COMPLETE 2026-02-01
  - Modified prompt_templates.py: added memory_context parameter to both build_system_prompt functions
  - Updated series_service.get_combined_context() to include memory_context from memory_service
  - Updated generation_service.py: all 3 calls to build_system_prompt_cached now pass memory_context
  - Updated chat_service.py: chat context now includes series memory
  - Updated generation.py direct revision endpoint: passes memory_context
  - Memory summaries appear in "SERIES MEMORY (Accumulated Canon)" section of prompts

- [x] **Phase 5: Staleness Detection** - COMPLETE 2026-02-01
  - Hashing: compute_file_hash() creates SHA256 hashes of character/world files
  - check_staleness() compares current file hashes against stored hashes
  - update_hashes() stores current hashes after summary generation
  - get_context_with_auto_refresh() auto-regenerates summaries when staleness detected
  - series_service now calls auto-refresh version when loading context
  - Staleness API endpoint: GET /{series_id}/memory/staleness

- [x] **Phase 6: Deep Import** - COMPLETE 2026-02-01
  - Added `deep_import` parameter to manuscript import endpoint
  - If deep_import=True and project is in a series:
    - Runs extraction on each imported scene (background task)
    - Auto-generates summaries when done
  - Status endpoint: GET /manuscript/deep-import-status
  - Tracks progress: total scenes, scenes extracted, current scene, status

### Key Decisions

1. **Granularity:** Per-series (not global - different pen names = different voices)
2. **Extraction Trigger:** When marking scene as canon
3. **What Gets Extracted:** Character state changes, world facts, plot events (NOT style - that's the style guide)
4. **Summary Regeneration:** Auto when source files change
5. **Hybrid Approach for Previous Books:**
   - Quick manual Book Summary for fast bootstrapping (existing feature)
   - "Deep Import" option for thorough extraction from manuscripts (future)
   - "Generate Summary from Memory" to compile extractions into readable summary

---

## PRIORITY: Series-Aware Generation (Book 2 Ready)

**Goal:** Write book 2 of a series with full continuity from books 0 (novella) and 1 (novel).

### Critical Bugs (Context Loss in Revisions) - FIXED 2026-01-30

Audit revealed: Initial generation has full context, but **revisions lose everything**.

- [x] **Fix revision context loading** - `_run_revision()` now calls `get_combined_context()`
  - Now includes: series characters, series worlds, previous books, references
  - Location: `generation_service.py:608`
- [x] **Fix selection revision context** - `_run_selection_revision()` now has full context
  - Location: `generation_service.py:721`
- [x] **Fix direct selection revision** - API endpoint now builds full system prompt
  - Location: `generation.py:433`
- [x] **Style guide in revision prompts** - Now included via combined context
- [x] **References in revisions** - Now passed to `build_system_prompt()` in all revision flows

### Series Continuity Features

- [x] **Book-level summaries** - Structured synopsis of previous books fed to generation
  - What happened, character arcs, world state changes
  - IMPLEMENTED 2026-02-01: Book Summary section in Structure tab
  - API: GET/PUT/DELETE `/api/projects/{id}/summary`
  - Stored as `summary.md` in project directory
  - `_load_previous_book_summaries()` loads these for later books
- [ ] **Series Timeline** - Chronological tracking across books (Sudowrite has this)
  - AI knows book order, what happened when
  - Track major events with timestamps/book references
- [x] **Import Novel → Auto-populate Story Bible** - COMPLETE 2026-02-01
  - **Series-Level Entity Extraction implemented:**
    - Deep import extracts characters/world to SERIES level, not book level
    - Merge strategy: Always additive, never overwrite
    - Each fact tagged with `book_number` where established
    - On import: find existing entity by name → APPEND new facts
    - Books can be imported out of order - `book_number` determines chronology
    - Entity service: `backend/app/services/entity_service.py`
    - Markdown files with YAML frontmatter: `books_appeared`, `first_seen_book`, `last_updated`
  - **Separation of concerns:**
    - Character sheets: cumulative truth across series (WHO)
    - Memory layer: time-weighted context for generation (WHAT MATTERS NOW)
- [ ] **Chapter Continuity Linking** - Explicit links between chapters
  - We have `depends_on` for scenes but it's optional/manual
  - Should auto-link sequential chapters

### Current Implementation Priorities

**Priority 1: Series-Level Entities** - COMPLETE 2026-02-01
- [x] Entities extract to series level, not book level
- [x] Merge logic: additive, never overwrite
- [x] `book_number` tagging for chronology
- [x] Markdown files with YAML frontmatter

**Priority 2: Memory Enhancement (Drift-inspired)** - COMPLETE 2026-02-01
- [x] Memory decay: older facts have lower weight (relevance_score, DecayConfig)
- [x] Learn from corrections: user edits → extract preferences (StyleLearningService)
- [x] Causal chains: trace WHY through plot events (causes, consequences, trace_causal_chain)
- Implementation: memory_service.py, style_learning_service.py, memory.py models

**Priority 3: Chico (Series-Level AI Assistant)** - COMPLETE 2026-02-01
- [x] Floating chat widget (minimizable, bottom-right corner)
- [x] Series-level: knows all books, characters, world, memory layer
- [x] Persistent conversation history per series
- [x] Configurable name in settings (default: "Chico")
- [x] Continuity guardian: can catch contradictions across books
- [x] Storage: `data/series/{series-id}/chat/chico_history.json`
- [x] Personality options: helpful, direct, enthusiastic
- [x] Draggable widget (drag header to reposition anywhere)
- [x] Auto-appears when opening any book in a series
- [x] Resizable window (drag corner to resize)
- [x] Adjustable text size (A-/A+ buttons, saved to localStorage)

**Priority 6: Agentic Chico** - FUTURE
- [ ] **Tool/function calling** - Give Chico actions to execute:
  - `generate_chapter(chapter_id)` - Generate all scenes in a chapter
  - `evaluate_scene(scene_id)` - Run critique on a scene
  - `mark_as_canon(scene_id)` - Accept scene as canon
  - `run_deep_import(file)` - Import manuscript with extraction
- [ ] **Task queue with status** - Background jobs with progress tracking
- [ ] **Notification system** - Alert when tasks complete:
  - Browser notifications (simple, requires tab open)
  - Discord webhook (leverage existing Clawdbot infrastructure)
  - Email (optional)
- [ ] **Batch operations** - "Generate chapters 1-5 overnight"
- [ ] **Proactive suggestions** - Notice gaps, suggest fixes

**Priority 7: Chico History Management** - FUTURE
- [ ] **New Chat + Archive** - Start fresh conversation, access past chats
- [ ] **Auto-compress** - Summarize older messages in long conversations
- [ ] **Session indicator** - Show conversation age/length
- [ ] **Chico everywhere** - Show Chico for ALL projects, not just series (project-level context for standalones)

**Priority 8: UX Improvements** - FUTURE
- [ ] **Clarify import types** - Better labels for Manuscript vs Outline import:
  - Manuscript: "I have written prose to import"
  - Outline: "I have a structure/outline to generate from"
- [ ] **Import type tooltips** - Explain when to use each
- [ ] **Customizable critique criteria** - Let user control what critique focuses on:
  - Preset modes: Structural, Line Edit, Polish, Full
  - Category checkboxes: pacing, dialogue, prose style, continuity, etc.
  - Custom prompt option for specific instructions
  - Per-project defaults (different genres need different criteria)
  - Word count targets: flag under/over without encouraging fluff ("add substance, not padding")
- [x] **Generation queue labels** - Show "Chapter X, Scene Y" in queue items (sorted by book order)
- [ ] **Word count on revision screen** - Show current word count while reviewing/revising
- [x] **Critique interaction** - Editor can add inline annotations to AI critique (styled distinctly), passed to revision as guidance
- [x] **Maximize/minimize buttons missing** - BUG: fixed, added expand buttons to queue review panel
- [ ] **Theme support** - Dark/light/system theme switching (CSS variables ready: `--editor-note-color`, `--editor-note-bg`)

**Priority 9: Outline Import Overhaul** - FUTURE
- [ ] **File upload support** - Import .md, .txt, .docx outlines (not just paste)
- [ ] **Series selector** - Assign to series during import (not just after)
- [ ] **Preview before import** - Show parsed structure for confirmation
- [ ] **Format detection** - Auto-detect outline format (standard vs Claude/em-dash)
- [ ] **Partial import** - Import specific acts/chapters, not just whole book
- [ ] **Merge/update mode** - Update existing project structure from revised outline
- [ ] **Character linking** - Match character mentions to existing series characters
- [ ] **World linking** - Match location/world mentions to existing world elements
- [ ] **Validation warnings** - Show issues before import (missing scenes, orphaned chapters)
- [ ] **Import templates** - Save outline format preferences per user/series

**Priority 4: Token Optimization** - COMPLETE 2026-02-01
- [x] Scene-relevant entity filtering (filter characters/world by scene mentions)
- [x] Tiered book summaries (essential 500 words vs full 2500 words)

**Priority 5: Quality of Life** - COMPLETE 2026-02-01
- [x] GUI for manuscript import with extraction (deep import progress tracking)
- [x] Series dashboard (stats, memory status, books grid, quick actions)
- [x] Continuity warnings (LLM-based contradiction detection)
- [x] Book summary modal (full-width, 900px, proper sizing)
- [x] Style guide toast notifications (visible save feedback)
- [x] Series-level data hierarchy (characters/world load from series when book is in series)
- [x] Flexible outline parser (supports em-dash separators, multiple heading levels, bold scene format)

### Research & Exploration

- [ ] **Explore Drift/Drift Cortex** - https://github.com/dadbodgeoff/drift
  - Codebase intelligence tool with persistent memory for AI assistants
  - Memory decay (half-life by importance), learns from corrections, causal narratives
  - Could inspire: memory decay for older plot events, learning from prose edits
  - Token-efficient compression based on priority
  - **Application to prose-pipeline:**
    - Memory that decays: prequel facts have lower weight by Book 3
    - Learn from corrections: user edits prose → extract style preferences
    - Causal chains: not just "Elias is broken" but trace WHY through plot events

### Competitive Feature Gaps (from Sudowrite/Novelcrafter research)

- [ ] **Shared Codex across series** - Verify series characters/world flow into all prompts
  - Currently works for initial gen, broken for revisions
- [ ] **POV & Tense enforcement** - Automatic consistency checking
  - We have fields but not enforced validation
- [ ] **Per-scene reference selection** - Override which references apply to specific scenes
  - Currently: global `use_in_generation` flag only
- [ ] **128K+ context window** - Sudowrite reads nearly full novel
  - Currently: 10 previous scenes max, truncated references
  - Consider: configurable context depth, smart summarization
- [ ] **Visual timeline/storyboard** - Novelcrafter has this
  - Low priority but nice for planning

### Token Optimization

Research showed competitors burn tokens by re-sending full context every call.
Our approach: prompt caching + smart filtering.

- [x] **Prompt caching (Anthropic)** - IMPLEMENTED 2026-01-30
  - New `build_system_prompt_cached()` returns content blocks with cache_control
  - Static content (style, characters, world, refs, previous books) = cached
  - Dynamic content (previous scene summaries) = not cached, placed at end
  - LLM service handles format conversion for OpenRouter compatibility
  - Cache stats tracking in LLMService
  - Estimated 70% reduction in input token costs for Anthropic

- [x] **Scene-relevant entity filtering** - COMPLETE 2026-02-01
  - Parse scene outline + beats for names/locations
  - String match against file names
  - Skip unmentioned entities (keep first 5 as fallback)
  - Include foundational world elements (magic, rules) regardless
  - Implementation: series_service._filter_by_relevance(), generation_service uses filter
- [x] **Tiered book summaries** - COMPLETE 2026-02-01
  - Essential (~500 words): key plot points, major changes, critical facts
  - Full (~2500 words): complete plot, all character arcs, detailed world
  - Stored in memory.book_summaries (keyed by book_id)
  - Previous book loading uses essential tier by default
  - API endpoints: generate-tiered-summary, book-summary/{book_id}, book-summaries

### Quality of Life - COMPLETE 2026-02-01

- [x] **GUI for manuscript import with extraction** - Deep import with progress tracking
- [x] **Series dashboard** - Stats, memory status, books grid, quick actions
- [x] **Continuity warnings** - LLM-based contradiction detection with severity levels
- [x] **Book summary modal** - Full-width modal for editing book summaries
- [x] **Series-level data hierarchy** - Characters/world load from series level for books in series

### Chico In-App (Floating AI Assistant) - COMPLETE 2026-02-01

- [x] **Floating chat window** - Draggable persistent chat with AI co-author
  - Knows ALL series context (characters, world, memory layer, style)
  - Conversation history persists per-series
  - Full story awareness across all books in series
  - **Implementation:**
    - Floating draggable widget (minimize/close buttons, drag by header)
    - Storage: `data/series/{series-id}/chat/chico_history.json`
    - System prompt = memory layer + character sheets + personality
    - Auto-appears when opening any book in a series
  - **Capabilities:**
    - Answer questions: "Who is Elias's dragon?"
    - Suggest next steps: "What should happen in Chapter 3?"
    - Brainstorm: "Give me 3 ways the betrayal could be revealed"
    - Continuity check: "Does this contradict anything established?"
    - Character voice: "How would Elena say this?"
  - **Personality options:** helpful, direct, enthusiastic
  - **Customizable name** in settings (default: "Chico")

---

## DEPRIORITIZED: Clawdbot/Discord Integration

*Leaving API for future use, but not actively developing Discord integration. Just another layer of token usage.*

**Goal:** Control prose-pipeline through Discord via Clawdbot (Moltbot), enabling autonomous editing workflows and conversational interaction with the pipeline.

### Architecture
```
Discord (Clawdbot) ──API──► prose-pipeline backend
       │                          │
       │                          ▼
       │                   Analyze / Extract / Generate
       │                          │
       ◄──────────────────────────┘
       Reports back, discusses changes
```

### Phase 1: Manuscript Analysis & Extraction (COMPLETE)
When given an existing manuscript, AI should:
- [x] **Evaluate manuscript** - Overall quality assessment, pacing, structure
- [x] **Extract characters** → Auto-populate character cards
  - Names, roles, physical descriptions, personality traits
  - Relationships between characters
  - Voice/dialogue patterns
- [x] **Extract world/lore** → Auto-populate world context
  - Locations, magic systems, technology
  - Historical events, political structures
  - Rules and constraints of the world
- [x] **Generate style guide** from author's voice
  - Sentence rhythm patterns (short/long variance)
  - Vocabulary tendencies (formal/casual, period-specific)
  - POV habits (deep/shallow, tense preferences)
  - Dialogue style (tags, beats, dialect handling)
  - Descriptive preferences (sparse vs lush)

**Implemented Endpoints:**
- `POST /api/extract/characters` - Extract character data from prose
- `POST /api/extract/world` - Extract world/lore elements
- `POST /api/extract/style` - Generate style guide from prose
- `POST /api/extract/analyze` - Full analysis (all three combined)
- `POST /api/extract/evaluate` - Quality evaluation with scores

### Phase 2: Editing Workflow via Discord (IN PROGRESS)
- [x] **LanguageTool integration** - Grammar, punctuation, passive voice detection
  - Endpoints: `/api/tools/languagetool`, `/api/tools/languagetool/correct`
  - CLI: `grammar-check`, `grammar-check-scene`, `grammar-correct`
  - Local server (no rate limits), requires Java
- [x] **CLI commands for full workflow** - Create characters/world from extractions, save style, import manuscripts, generation controls
- [x] **One-shot manuscript import** - Upload .docx → auto-detect chapters → create all
- [x] **Evaluation endpoint** - Get critique/scores without starting revision
- [ ] **One critique pass** (conservative until comfortable with models)
- [ ] **One revision pass**
- [ ] **Report to Discord** - Summary of changes made, areas of concern

**New Endpoints (2026-01-29):**
- `POST /api/projects/{id}/manuscript/import-full` - One-shot: upload file → detect chapters → import all
- Improved chapter detection: "Chapter X", "Part X", standalone numbers (One, Two), digits, roman numerals

**TOOLS.md on Clawdbot updated with:**
- Series creation (create BEFORE projects that reference them)
- One-shot import workflow
- Evaluation/critique workflow
- Overnight batch processing pattern

### Phase 3: Creation Workflow via Discord
For new works that continue existing series/world:
- [ ] Load existing style guide, characters, world
- [ ] Match author's voice from style guide
- [ ] Maintain continuity with previous work
- [ ] Generate new scenes matching established patterns

### Phase 4: Discord Bot Integration
- [x] Identify Clawdbot code location (192.168.2.197, /home/john/clawd)
- [x] Add prose-pipeline API client functions (prose_api.py)
- [x] Create Clawdbot skill (~/.clawdbot/skills/prose-pipeline/)
- [x] Update TOOLS.md with prose-pipeline connection info
- [x] Test API connectivity from Clawdbot VM
- [x] **First successful import!** - "Flesh Worn Stone" imported with 10 chapters, 11 characters, 1 world entry
- [x] Conversation flows working:
  - [x] "Here's my manuscript, analyze it" → extracts characters, world, style
  - [x] "Import this as book 1 in The Game series" → creates series + project + imports
  - [x] "Evaluate chapter 1" → CLI commands: evaluate-scene, evaluate-chapter, evaluate-act, evaluate-book
  - [ ] "Edit chapters 1-5 overnight" → needs testing
- [ ] User ID restriction (only owner can command)

### Cost Optimization
- [x] Change default generation model to DeepSeek V3 (deepseek/deepseek-chat-v3.1)
- [x] Change default critique model to DeepSeek V3 (deepseek/deepseek-chat-v3.1)
- [ ] Update TOOLS.md to use cheaper models by default
- [ ] Add model cost estimates to documentation

**Model cost comparison:**
| Model | Input/Output per M tokens | Use case |
|-------|---------------------------|----------|
| Claude Opus 4 | $15/$75 | Final polish only |
| Claude Sonnet 4 | $3/$15 | Quality critique |
| Claude Haiku 3.5 | $0.25/$1.25 | Extraction, orchestration |
| DeepSeek V3 | $0.27/$1.10 | Great for generation/critique |
| Llama 3.1 70B | $0.50/$0.75 | Good all-rounder |

### Security Notes (2026-01-29)
- prose-pipeline has **no shell execution** - safe from RCE attacks
- Discord bot in private server (single user) - minimal prompt injection risk
- Network secured via OPNsense + AdGuard
- Consider adding user ID check to Discord bot for defense-in-depth

### API Endpoints (Implemented)
- [x] `POST /api/extract/analyze` - Full manuscript analysis (characters + world + style)
- [x] `POST /api/extract/characters` - Extract characters from text
- [x] `POST /api/extract/world` - Extract world/lore from text
- [x] `POST /api/extract/style` - Generate style guide from text
- [x] `POST /api/extract/evaluate` - Quality evaluation with scores
- [x] `POST /api/tools/languagetool` - Run LanguageTool checks (grammar, spelling, style)
- [x] `POST /api/tools/languagetool/correct` - Auto-correct text

---

## NEW: Backlist Revival Project (Playwright Integration)

**Context:** Owner has 10-15 published novels on Kindle from a "past life" before corporate America and military service. These are sitting assets that could be refreshed and relaunched.

### The Vision: Automated Backlist Management

**Pipeline:**
```
KDP Dashboard ──Playwright──► Pull manuscripts
                                    │
                                    ▼
                            prose-pipeline
                            (Edit Mode)
                                    │
                                    ▼
                        Critique → Revise → Polish
                                    │
                                    ▼
KDP Dashboard ◄──Playwright──── Republish updated versions
```

### Phase 1: KDP Integration (Future)
- [ ] Build `scrapers/kdp.py` - Kindle Direct Publishing automation
  - [ ] Login with session persistence
  - [ ] List all published books
  - [ ] Download manuscript files (.doc, .docx)
  - [ ] Pull sales data and reviews
  - [ ] Pull current metadata (description, keywords, categories)
- [ ] Import into prose-pipeline projects automatically
- [ ] Track KDP-linked projects (store ASIN, KDP book ID)

### Phase 2: Revision Workflow
- [ ] Import existing novel to prose-pipeline
- [ ] Run through chapter-by-chapter critique
- [ ] Tighten prose, fix pacing issues
- [ ] Update anything dated
- [ ] Use original as style reference for consistency

### Phase 3: Republish Automation
- [ ] Push updated manuscript back to KDP via Playwright
- [ ] Update metadata (new keywords, refreshed description)
- [ ] Trigger "relaunch" workflow
- [ ] Update pricing if desired

### Phase 4: Monitoring
- [ ] Scrape sales rank and reviews
- [ ] Alert on new reviews (respond quickly to negative)
- [ ] Track performance before/after refresh
- [ ] Competitor monitoring in same categories

### Business Angle
- Refreshed backlist with tightened prose can spike sales
- Authors do "relaunches" all the time - this automates 80%
- Could become **BacklistBot** product for other authors

---

## Related Project: HIWC-assistant

See `/root/HIWC-assistant/` for e-commerce automation work.
Same Playwright-first philosophy being applied there for:
- Etsy/Shopify order scraping
- Google Ads automation
- Competitor monitoring

Shared infrastructure potential:
- Common Playwright utilities
- Session management patterns
- Notification system (Discord)

---

## Roadmap

The full creative workflow: **OUTLINE → GENERATE → EDIT**

| Module | Status | Priority |
|--------|--------|----------|
| **Continuity System** | Complete | Done |
| **Generation** | Working | Done |
| **Editing Module** | Paused | Later |
| **UX Simplification** | Complete | Done |
| **Outlining Module** | **In Progress** | **NOW** |

---

## CURRENT: Outlining Module

**See `outline_plan.md` for full design document.**

### Phase 1: Core Structure (COMPLETE)
- [x] Core prose philosophy implemented (no AI tells, banned vocabulary)
- [x] Planning document created (`outline_plan.md`)
- [x] UX decision: Outline is a tab within projects
- [x] Data models extended:
  - Scene: `beats`, `depends_on`, `outline_status`
  - Project: `outline_only` flag
  - New Beat model: `id`, `text`, `notes`, `tags`, `order`
- [x] Beat CRUD API endpoints
- [x] Frontend: Outline tab in project view
- [x] Frontend: Beat editor UI within scenes
- [x] Story structure templates (3-act, 4-act, 5-act, hero's journey, etc.)

### Phase 5: Auto Mode (COMPLETE)
- [x] Auto-generate outline from seed premise
- [x] Scope selection (quick/standard/detailed)
- [x] AI generates full structure: Acts → Chapters → Scenes → Beats
- [x] Progress modal with spinner and indeterminate progress bar
- [x] Clear All structure button (nuclear delete with confirmation)
- [x] JSON parsing fixes for AI responses (extract_json helper)
- [x] LLMService.generate() method for structured responses

### Next Up: Phase 2 - Guided Mode
- [ ] Conversational outline building
- [ ] AI asks questions, user answers
- [ ] Progressive structure building based on user input
- [ ] Human decides, AI proposes

### Future Phases
- Phase 3: Series Continuity (arc tracking, book summaries as canon)
- Phase 4: Dependency System (tag-based linking, change flagging)

---

## Completed

- [x] Fix generation prompt - add "output only prose, no preamble"
- [x] Post-processing cleanup - `clean_prose_output()` strips AI preambles
- [x] Data directory picker - UI to configure project storage location with migration option
- [x] Full data backup download - ZIP export of all projects, series, and settings
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
- [x] Floating AI revision bubble - select text for inline AI editing
- [x] Canon toggle from reading view - mark/unmark scenes as canon without entering edit mode
- [x] Inline accept/reject in diff view - cherry-pick AI changes before applying
- [x] Polish mode - lighter touch revision (line edits vs structural)
- [x] Generation dropdown sorted by chapter/scene order
- [x] Global settings on start page - API keys, default models, credits display
- [x] Unified Scene Workspace - merged Generate tab and Reading View into one adaptive workspace
- [x] Removed hamburger menu settings modal (settings now on start page)
- [x] Fixed floating AI bubble - uses getComputedStyle() for reliable visibility detection
- [x] Fixed sidebar refresh after canon toggle - workspace functions now call render functions
- [x] Evaluate-only mode - floating panel shows critique, "Start Revision" reuses critique (no duplicate API call)
- [x] Action buttons moved to workspace header (Evaluate, Mark as Canon, Edit, review actions)
- [x] Floating AI bubble works in review state (prose column during critique review)
- [x] **Core Prose Philosophy** - embedded "no AI tells" rules in all prompts (generation, critique, revision, quick actions)
- [x] Banned vocabulary list (delve, tapestry, myriad, whilst, etc.) enforced across all prose operations
- [x] Critique prompts now flag AI tells as top-priority issues
- [x] Quick action instructions updated to prevent AI vocabulary
- [x] **Auto-generate outline** - AI generates full structure from seed premise (Acts → Chapters → Scenes → Beats)
- [x] Floating AI bubble works in queue review panel
- [x] Workspace loads active generations from queue on scene click
- [x] New `/revise-selection-direct` endpoint for synchronous inline edits (no new iteration)

---

## BUGS: Fix First

- [ ] .docx files not appearing in file picker for manuscript import (user had to download as .txt)
- [x] Floating AI bubble inconsistent - fixed with getComputedStyle() and proper event listeners
- [x] Sidebar not updating after canon toggle - fixed by removing invalid updateWordCount() call
- [x] Word count in header not updating after marking scene as canon - fixed by sending prose when marking as canon
- [x] Sidebar (green scene name) and cumulative word count not updating after Accept as Canon from review state - fixed by awaiting loadScenes() and calling updateStats()
- [x] Collapsible critique panel in review state - toggle button to hide/show critique for more prose space
- [x] Accept as Canon broken in workspace header after loading from queue - fixed by setting workspaceGenId
- [x] Accept as Canon broken after bubble revision in queue - fixed with new synchronous revision endpoint
- [ ] Show Changes button in review state shows blank - diff view not populating

---

## NOW: Editing Module

*Revise existing prose through the critique loop.*

**What exists:**
- Single-scene edit mode (import prose, skip to critique)
- Critique → revise loop works
- **Manuscript import** - upload .docx/.txt/.md files (mammoth for .docx)
- **Auto chapter detection** - improved patterns (2026-01-29):
  - "Chapter 1", "CHAPTER ONE", "Chapter 1: Title"
  - "Part 1", "Part One"
  - Standalone number words: "One", "Two", "Three" (preceded by blank lines)
  - Standalone digits: "1", "2", "3" (preceded by blank lines)
  - Roman numerals: "I", "II", "III" (preceded by blank lines)
  - Auto-detects prologue content before first chapter
- **One-shot import endpoint** - `POST /manuscript/import-full` does upload → detect → import
- **Bulk scene creation** - each chapter becomes a Chapter + Scene in edit mode
- **Edit mode display** - imported prose visible in reading pane with "Edit Mode - Ready for Critique" status
- **Backup on prose edit** - auto-backup before manual prose changes

**GUI Gap:**
- [ ] Add manuscript upload with chapter preview to GUI (currently API-only via Clawdbot)
- **Polish mode** - choose between full structural revision or light line edits
- **Unified workspace** - click any scene to open adaptive workspace

### Remaining Editing Features

- [ ] Consistency pass - critique focused on continuity errors across scenes
- [ ] Side-by-side version comparison (pick any two versions)
- [x] Evaluate-only mode - get critique report without entering revision loop (with token-efficient "Start Revision" option)
- [x] Project-level evaluation - evaluate-book CLI command evaluates entire project (with word count warnings)

---

## COMPLETED: UX Simplification

*Simplified the interface by unifying workflows and moving global settings.*

### Global Settings to Start Page (DONE)

- [x] Move API configuration to start page (collapsible settings panel)
- [x] API key entry (OpenRouter and Anthropic)
- [x] Default model selection
- [x] Credit balance display (OpenRouter)
- [x] Data directory configuration
- [x] Removed hamburger menu (settings only on start page now)

### Unified Scene Workspace (DONE)

- [x] Removed separate Generate tab
- [x] Click any scene in sidebar → opens unified workspace
- [x] Workspace adapts based on scene state:
  - No prose: show outline + "Generate" / "Import Prose" buttons
  - Has prose (not canon): show prose + floating bubble + Evaluate/Mark Canon/Edit
  - Has prose (canon): show prose + "Remove from Canon" button
  - Generating: show progress bar
  - Awaiting approval: show prose + critique + Approve & Revise/Accept/Reject
- [x] Model selection and revision mode in collapsible settings panel
- [x] Floating AI bubble works in workspace
- [x] "Evaluate" button for critique-only feedback

### Import Organization

- [x] Manuscript import stays in Structure → Import
- [x] Single-scene prose import in unified workspace ("Import Existing Prose" button)
- [x] Character/Reference imports stay in their respective tabs

---

## FUTURE: Character & Series Management

- [ ] Promote book characters to series level
- [ ] Visual distinction between series vs book-only characters
- [ ] When creating character in series book: prompt for "Series-wide" vs "This book only"

---

## Outlining Module (Detailed Plan)

**See `outline_plan.md` for complete design document.**

Summary:
- Two modes: Guided (quality-focused) and Auto (speed-focused)
- Beats as planning artifacts within scenes
- Dependency tracking via tags
- Series continuity via structured reference docs
- Human decides, AI proposes

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
- [ ] Status badges in sidebar (empty, has prose, canon, generating)

---

## Project Notes

- **The Jade Vow** - Book 1, published on KDP
- **The Crimson Rites** - Book 2, 160+ scenes imported, ready for generation
- **On Storms and Tides** - Series name
- **Magnet novella** - needs to be uploaded to reference materials

---

## Session Notes (2026-01-21)

**Cross-Project Planning Session:**

Discussed business product opportunities combining prose-pipeline and HIWC-assistant:

1. **ProseForge** - SaaS version of prose-pipeline for writers ($19-149/month)
2. **BacklistBot** - Automated backlist management for authors (KDP integration)
3. **ContentEngine** - Combine prose generation with Playwright publishing

**Key Insight:** Owner has 10-15 published novels sitting on KDP. Playwright can:
- Pull manuscripts from KDP dashboard
- Feed into prose-pipeline edit mode
- Push refreshed versions back to KDP
- Monitor sales and reviews

**Priority:** E-commerce (HIWC) is bread and butter right now. Backlist revival is future project but documented here for continuity.

**Shared Playwright Philosophy:** If you can log in and see it, Playwright can automate it. APIs optional.

---

## Session Notes (2026-01-30)

**Features Added:**

1. **Optional beats toggle** - Checkbox to include/exclude scene beats in generation prompts
2. **Delete buttons in series view** - Can now delete individual books from series list (hover to show ×)
3. **UI refresh fix** - Manuscript import now properly refreshes sidebar/structure view
4. **Evaluation CLI commands** - Clawdbot can now evaluate prose at multiple levels:
   - `evaluate-scene <project> <scene-id>` - Single scene
   - `evaluate-chapter <project> <chapter-id>` - All scenes in chapter
   - `evaluate-act <project> <act-id>` - All scenes in act
   - `evaluate-book <project>` - Entire book
5. **Configurable word count warning** - `eval_word_count_warning` setting (default 6000)

**Clawdbot Integration:**
- Evaluation commands use prose-pipeline's OpenRouter connection (not Clawdbot's AI)
- Returns structured scores: pacing, structure, character development, dialogue, prose quality
- Fetches prose from `prose` field (canon) or `original_prose` (imports/drafts)
- SKILL.md updated with new evaluation commands

**Books Imported:**
- "The Game" series: Books 1, 2, 3 imported via manuscript import
- Chapter detection working well on all three

**LanguageTool Integration:**
- Backend: `/api/tools/languagetool` and `/api/tools/languagetool/correct` endpoints
- CLI: `grammar-check`, `grammar-check-scene`, `grammar-correct` commands
- Uses local LanguageTool server (no rate limits, requires Java)
- Categories: TYPOS, GRAMMAR, PUNCTUATION, STYLE
- Returns offsets, suggestions, and context for each issue

---

## Session Notes (2026-01-30 continued)

**Data Management Features:**

1. **Data directory migration** - When changing data directory, option to migrate existing data:
   - Checkbox: "Migrate existing data to new location"
   - Copies projects, series, settings.json to new location
   - Won't overwrite existing files (merges instead)
   - `PUT /api/settings/data-dir` with `migrate_data: true`

2. **Full backup download** - Download all data as ZIP:
   - Button: "Download Backup" in settings
   - Downloads timestamped ZIP (e.g., `prose-pipeline-backup-20260130_143022.zip`)
   - Includes: all projects, all series, settings.json
   - `GET /api/settings/backup` endpoint

---

## Competitive Research (2026-01-30)

**Major Players Analyzed:**
- [Sudowrite](https://sudowrite.com/) - $19-59/mo, proprietary "Muse" model, Story Bible, series support
- [Novelcrafter](https://www.novelcrafter.com/) - $4-20/mo + BYOK, Codex wiki, highly configurable
- [Squibler](https://www.squibler.io/) - More automated "generate whole novel"
- [NovelAI](https://novelistai.com/) - Falling behind, 70B model outdated

**What They Do Well:**
1. **Sudowrite Series Timeline** - Chronological tracking, AI knows book order
2. **Shared Codex/Story Bible** - Auto-available across all books in series
3. **Import Novel → Auto-populate** - Extract characters/world/style on import
4. **128K context** - Reads nearly full novel for continuity
5. **Chapter Continuity Linking** - Explicit links for smoother arcs
6. **POV & Tense controls** - Automatic consistency enforcement

**Common User Complaints (from Reddit/forums):**
- Memory loss - characters forget, plot threads vanish
- AI tells - generic, clichéd prose (we already address)
- Expensive burns - "$30 in 2 days of normal use"
- Loss of creative control - AI writes its own story
- Repetitive suggestions

**Our Advantages:**
- Anti-AI-tells philosophy (banned vocabulary, critique flags)
- BYOK via OpenRouter (cost control, model choice)
- Style extraction from existing work
- Reference library for published examples
- Enhanced outline import with full metadata

**Key Insight:** Most tools focus on generation but break on revision.
Our revision flow loses context - fixing this is the critical differentiator.
