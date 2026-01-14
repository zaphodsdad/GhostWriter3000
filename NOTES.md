# Prose Pipeline - Project Status

**Last Updated:** 2026-01-14 (morning)
**Session:** Continuation from previous session, new Claude instance

---

## What This Is

AI-powered prose generation pipeline for long-form fiction. Write outlines, generate prose with AI, critique/revise loop, build a manuscript scene by scene.

---

## What's Working

### Core Features
- **Project management** - Multiple projects, each with its own data
- **Story structure** - Acts → Chapters → Scenes hierarchy
- **Outline import** - Paste markdown, imports acts/chapters/scenes automatically
- **AI prose generation** - Generate, critique, revise loop with model selection
- **Manual prose editing** - Edit prose directly with auto-save (2 sec debounce)
- **Style guide** - Project-level style guide injected into all AI prompts
- **Chat with AI** - Project-aware chat for brainstorming/editing
- **Characters & World** - Markdown+YAML files, world has sub-categories (Locations, Lore, Factions, Systems)

### Quality of Life
- Auto-save with status indicator (Saved/Unsaved/Saving...)
- Unsaved changes warnings (cancel, close, browser tab)
- Word counts everywhere (scenes, chapters, master count)
- Model selection dropdowns (generation & critique)
- Canon/non-canon scene tracking

### Frontend (Level 3 Writer's Tool - COMPLETE)
- Full SPA with dark theme
- Project selector with create/switch
- Dashboard with stats
- Characters & Worlds CRUD with categories
- Structure tree (Acts → Chapters → Scenes)
- Outline import from markdown with preview
- Style guide editor
- Complete generation workflow (select → progress → review → accept)
- Chat with AI (scoped to project/scene)
- Generation queue with batch review
- Reading view with prose editing
- Reference panel for side-by-side viewing
- Toast notifications
- Responsive design

---

## Tech Stack

- **Backend:** FastAPI (Python 3.11+), no database - just JSON/Markdown files
- **Frontend:** Vanilla HTML/CSS/JS, single page app (feature-complete)
- **AI:** OpenRouter API (can also use Anthropic direct)
- **Data:** `/home/john/prose-pipeline/data/projects/{project-id}/`

---

## Current Project: The Garden

**Location:** `/home/john/prose-pipeline/data/projects/the-garden/`

**Premise:** A mysterious light washes over the world and humankind are killed instantly, along with every animal bigger than the largest insect. In that same instant, all insect life becomes sentient. And then the real war begins.

### Scene Status

| Scene | Title | Status | Notes |
|-------|-------|--------|-------|
| 1 | The Garden | ✅ Canon | Millicent's death, the light, insects awaken |
| 2 | First Thoughts | ✅ Canon | Mantis gains consciousness (HAS AI ARTIFACT - needs cleanup) |
| 3 | The Hive Convenes | ❌ Not started | Bees gather, link minds |
| 4 | The Council of Six | ❌ Not started | Representatives debate |
| 5 | The Silent Cities | ❌ Not started | Scouts explore human infrastructure |
| 6 | First Contact | ❌ Not started | Two factions emerge |

### Known Issues
- Scene 2 prose starts with "Here's a narrative prose draft for Scene 2:" (AI artifact)
- `previous_scene_ids` are empty on all scenes (continuity system dormant)
- `character_ids` and `world_context_ids` are empty (no characters/world defined yet)

---

## How to Start

```bash
cd /home/john/prose-pipeline/backend
source ../venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

Then visit: `http://<vm-ip>:8000`

---

## Project Structure

```
/home/john/prose-pipeline/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic (generation_service, llm_service, state_manager)
│   │   └── utils/           # Helpers (prompt_templates, file_utils, logging)
│   └── .env                 # API keys, model config
├── frontend/
│   ├── index.html           # Main SPA (935 lines, feature-rich)
│   ├── css/styles.css       # Dark theme (1542 lines)
│   └── js/app.js            # Application logic
├── data/
│   └── projects/
│       └── the-garden/      # Current test project
└── venv/                    # Python virtual environment
```

---

## Task List (Prioritized)

### Phase 1: AI Artifact Prevention (Quick Wins)
- [ ] **1.1** Fix generation prompt in `prompt_templates.py` - add "output only prose, no preamble"
- [ ] **1.2** Add post-processing cleanup in `generation_service.py` - strip common AI preambles
- [ ] **1.3** Clean up Scene 2's existing artifact manually

### Phase 2: Structural Improvements
- [ ] **2.1** Data directory picker - UI to configure where projects are stored
- [ ] **2.2** Startup validation - check API key validity on boot, fail fast with clear error
- [ ] **2.3** Error recovery - retry logic for LLM failures, stuck-state recovery

### Phase 3: Frontend Polish
- [ ] **3.1** Subtle animations/transitions
- [ ] **3.2** Typography refinement
- [ ] **3.3** Visual hierarchy improvements
- [ ] **3.4** Accent color options / theme variants

### Phase 4: Continuity System Activation
- [ ] **4.1** Wire up `previous_scene_ids` in scene form (UI exists, needs linking)
- [ ] **4.2** Auto-suggest scene linking based on chapter/scene order
- [ ] **4.3** Display previous scene summaries in generation context
- [ ] **4.4** Add characters/world to The Garden project

### Phase 5: Robustness
- [ ] **5.1** Cost tracking - tokens per generation, running totals
- [ ] **5.2** Backup system - auto-backup before overwrites
- [ ] **5.3** Version history for prose iterations
- [ ] **5.4** Unit tests for services
- [ ] **5.5** Integration tests for API

### Phase 6: Additional Features
- [ ] **6.1** Search across scenes/characters/world
- [ ] **6.2** Export - compile project to markdown/docx/epub
- [ ] **6.3** Word count goals and tracking
- [ ] **6.4** Websockets for real-time generation status (currently polling)
- [ ] **6.5** Undo/redo for prose edits
- [ ] **6.6** Drag-and-drop scene reordering

---

## Key Files for Common Tasks

| Task | File |
|------|------|
| Fix AI prompts | `backend/app/utils/prompt_templates.py` |
| Generation logic | `backend/app/services/generation_service.py` |
| LLM calls | `backend/app/services/llm_service.py` |
| State persistence | `backend/app/services/state_manager.py` |
| Configuration | `backend/app/config.py` |
| API routes | `backend/app/api/routes/*.py` |
| Frontend | `frontend/index.html`, `frontend/js/app.js` |

---

## API Keys

Stored in `/home/john/prose-pipeline/backend/.env`:
- `OPENROUTER_API_KEY` - for AI generation
- Model IDs like `anthropic/claude-sonnet-4`

---

## User Context

- John is accessing Ubuntu VM on Unraid server from Mac Studio (and later iPad/Debian laptop)
- Wants backup solution to Unraid (rsync recommended)
- Building this for real ongoing fiction work, not just The Garden test project
- Values: clean UI, practical features, no over-engineering

---

## Session History

### 2026-01-13 (Evening)
- Major build day - backend and frontend largely complete
- Created The Garden project with 6 scenes
- Generated scenes 1-2 as canon

### 2026-01-14 (Morning)
- New Claude instance, reviewed project state
- Identified AI artifact in Scene 2
- Created comprehensive task list
- Discovered frontend is more complete than docs suggested
- Updated NOTES.md with accurate status
