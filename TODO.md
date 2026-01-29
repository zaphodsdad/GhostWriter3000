# Prose Pipeline - TODO

**Last Updated:** 2026-01-29

---

## NEW: Clawdbot/Discord Integration

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

### Phase 1: Manuscript Analysis & Extraction (PRIORITY)
When given an existing manuscript, AI should:
- [ ] **Evaluate manuscript** - Overall quality assessment, pacing, structure
- [ ] **Extract characters** → Auto-populate character cards
  - Names, roles, physical descriptions, personality traits
  - Relationships between characters
  - Voice/dialogue patterns
- [ ] **Extract world/lore** → Auto-populate world context
  - Locations, magic systems, technology
  - Historical events, political structures
  - Rules and constraints of the world
- [ ] **Generate style guide** from author's voice
  - Sentence rhythm patterns (short/long variance)
  - Vocabulary tendencies (formal/casual, period-specific)
  - POV habits (deep/shallow, tense preferences)
  - Dialogue style (tags, beats, dialect handling)
  - Descriptive preferences (sparse vs lush)

### Phase 2: Editing Workflow via Discord
- [ ] **LanguageTool integration** - Grammar, punctuation, passive voice detection
- [ ] **One critique pass** (conservative until comfortable with models)
- [ ] **One revision pass**
- [ ] **Report to Discord** - Summary of changes made, areas of concern

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
- [ ] Implement conversation flows:
  - "Here's my manuscript, analyze it"
  - "Extract characters from chapter 3"
  - "Generate style guide from this book"
  - "Edit chapters 1-5 and tell me what you changed"
  - "Write the next scene matching my style"
- [ ] User ID restriction (only owner can command)

### Security Notes (2026-01-29)
- prose-pipeline has **no shell execution** - safe from RCE attacks
- Discord bot in private server (single user) - minimal prompt injection risk
- Network secured via OPNsense + AdGuard
- Consider adding user ID check to Discord bot for defense-in-depth

### API Endpoints Needed
- [ ] `POST /api/analyze/manuscript` - Full manuscript analysis
- [ ] `POST /api/extract/characters` - Extract characters from text
- [ ] `POST /api/extract/world` - Extract world/lore from text
- [ ] `POST /api/extract/style` - Generate style guide from text
- [ ] `POST /api/tools/languagetool` - Run LanguageTool checks

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
- **Auto chapter detection** - splits by "Chapter 1", "CHAPTER ONE", etc.
- **Bulk scene creation** - each chapter becomes a Chapter + Scene in edit mode
- **Edit mode display** - imported prose visible in reading pane with "Edit Mode - Ready for Critique" status
- **Backup on prose edit** - auto-backup before manual prose changes
- **Polish mode** - choose between full structural revision or light line edits
- **Unified workspace** - click any scene to open adaptive workspace

### Remaining Editing Features

- [ ] Consistency pass - critique focused on continuity errors across scenes
- [ ] Side-by-side version comparison (pick any two versions)
- [x] Evaluate-only mode - get critique report without entering revision loop (with token-efficient "Start Revision" option)
- [ ] Project-level evaluation - evaluate entire book once manuscript is complete

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
