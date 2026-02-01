# Prose Pipeline - TODO

**Last Updated:** 2026-02-01

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

- [ ] **Phase 6: Deep Import (Future)**
  - Batch-process imported manuscript through extraction
  - Option when importing: "Quick" vs "Deep (builds memory)"
  - Useful for thorough analysis of previous books

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
- [ ] **Import Novel → Auto-populate Story Bible** - Like Sudowrite's import
  - Currently: extraction endpoints exist but not integrated into import flow
  - Should auto-extract characters/world/style on manuscript import
- [ ] **Chapter Continuity Linking** - Explicit links between chapters
  - We have `depends_on` for scenes but it's optional/manual
  - Should auto-link sequential chapters

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

- [ ] **Scene-relevant entity filtering** - Only load mentioned characters/world
  - Parse scene outline for names/locations
  - String match against file names
  - Skip unmentioned entities
- [ ] **Tiered book summaries** - Essential (500 words) vs Full (2500 words)
  - Generate compressed "essential context" once per book
  - Use essential for generation, full available for reference

### Quality of Life

- [ ] **GUI for manuscript import with extraction** - Currently API-only
  - Upload → auto-detect chapters → preview → extract characters/world/style → import
- [ ] **Series dashboard** - See all books, their status, shared resources
- [ ] **Continuity warnings** - Flag when scene contradicts previous canon

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

### Cost Optimization (TODO)
Current defaults are expensive (Claude Opus/Sonnet). Consider:
- [ ] Change default generation model to DeepSeek V3 or Llama 3.1 70B
- [ ] Change default critique model to Haiku or DeepSeek
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
