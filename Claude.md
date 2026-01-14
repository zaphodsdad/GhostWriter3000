# Prose Pipeline Project - Claude Context

## Project Overview

The **Prose Pipeline** is an automated prose generation system built with Claude AI that implements a critique-revision loop for high-quality creative writing. It features a clean web interface for managing characters, world-building, and scene generation with automatic continuity tracking.

**Core Concept**: Generate prose from scene outlines, automatically critique it, and iteratively revise based on feedback until the user accepts the final version.

## Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript (no build tooling)
- **AI**: Claude API (via OpenRouter or direct)
  - **Opus 4.5** (`claude-opus-4-5-20251101`) for prose generation
  - **Sonnet 4.5** (`claude-sonnet-4-5-20250929`) for critique
- **Storage**: File-based (markdown for characters/world, JSON for scenes/generations)
- **Deployment**: Docker + docker-compose support

## Architecture

```
prose-pipeline/
├── backend/
│   ├── app/
│   │   ├── models/          # Pydantic data models
│   │   ├── services/        # Business logic & Claude API
│   │   ├── api/routes/      # REST endpoints
│   │   └── utils/           # Prompt templates
│   └── requirements.txt
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html
└── data/
    ├── series/
    │   └── {series-id}/
    │       ├── series.json       # Series metadata
    │       ├── characters/       # Shared characters (all books)
    │       ├── world/            # Shared world building
    │       ├── style.json        # Series-wide style guide
    │       └── references/       # Series reference library
    └── projects/
        └── {project-id}/
            ├── project.json      # Book metadata (includes series_id, book_number)
            ├── characters/       # Book-specific characters
            ├── world/            # Book-specific world additions
            ├── scenes/           # Scene definitions (JSON)
            ├── acts/             # Act structure
            ├── chapters/         # Chapter structure
            ├── generations/      # Generation state files
            ├── chat/             # Chat history
            ├── style.json        # Book style (overrides series)
            └── references/       # Book-specific references
```

### Layered Architecture
- **Models Layer**: Pydantic schemas for validation
- **Services Layer**: Business logic and Claude integration
- **API Layer**: FastAPI route handlers
- **Utils**: Shared prompts and utilities

## Key Features

### 1. Series System
Group related books with shared resources:
- **Shared Characters**: Characters available across all books in series
- **Shared World**: World-building context inherited by all books
- **Series Style Guide**: Consistent voice/tone across books
- **Series References**: Style guides, published books for context

Books can be:
- Created directly in a series
- Moved into/out of series after creation
- Standalone (no series association)

### 2. Reference Library
Import documents as AI context:
- **Document Types**: Style references, published books, world notes, etc.
- **Scope**: Project-level or series-level
- **Toggle Controls**: Use in generation, use in chat (independently)
- **Format**: Plain text, markdown supported

### 3. Edit Mode
Revise existing manuscripts instead of generating from scratch:
1. Import existing prose into a scene
2. Scene marked as `edit_mode: true`
3. Start revision - skips to critique step
4. Critique analyzes existing prose
5. Approve revisions as normal

### 4. Character Management
Characters stored as markdown files with YAML frontmatter:
```yaml
---
name: Jane Doe
age: 30
role: protagonist
personality_traits: [Brave, Curious]
skills: [Sword fighting, Ancient languages]
portrait: jane-doe.jpg
---

# Background
Jane grew up in...
```

**Portrait Support**: Characters can have portrait images (JPEG, PNG, GIF, WebP, max 5MB). Portraits are stored alongside character files and served via API.

**Bulk Import**: Import multiple characters at once:
- **YAML format** (auto-detected): Instant local parsing, 100% accurate
- **Free-form text**: AI-powered extraction via Claude

### 5. World Building
World context stored similarly to characters:
```yaml
---
name: The Kingdom of Aldoria
era: Medieval fantasy
magic_system: Elemental magic
---

# History
The kingdom was founded...
```

### 6. Scene-Based Generation
Scenes defined as JSON with:
- Scene outline/description
- Character references
- World context references
- Tone, POV, target length
- **Previous scene references** (for continuity)
- **Edit mode fields** (original_prose, edit_mode flag)

### 7. Critique-Revision Loop

**Workflow**:
```
1. User creates scene outline (or imports prose for edit mode)
2. Generate prose (using Opus) - skipped in edit mode
3. Critique prose (using Sonnet)
4. User reviews critique
5. Choose action:
   - Approve & Revise: Triggers revision
   - Accept as Canon: Finalizes scene
   - Reject: Cancels generation
6. Repeat up to MAX_ITERATIONS (default: 5)
```

**State Machine**:
```
PENDING → GENERATING → AWAITING_APPROVAL
                           ↓
                      [User Decision]
                           ↓
         ┌─────────────────┼─────────────────┐
    REVISING           GENERATING_SUMMARY    REJECTED
    (loop back)              ↓
                        COMPLETED
```

### 8. Dynamic Model Selection
Models are fetched dynamically from OpenRouter API:
- **Live model list**: Queries OpenRouter for available models
- **Filtered selection**: Shows models from preferred providers (Anthropic, OpenAI, Google, Meta, Mistral, Cohere)
- **Fallback list**: Default models shown if API unavailable
- **Pricing info**: Model costs displayed for informed selection

### 9. Default Model Settings
User preferences for AI models:
- **Settings panel**: Configure default generation and critique models
- **Per-generation override**: Can still select different models for individual generations
- **Persistent**: Settings saved to `data/settings.json`

### 10. Word Count Goals
Track writing progress:
- **Project goals**: Set target word count per project
- **Progress bar**: Visual indicator of progress toward goal
- **Click to edit**: Click word count display to set/update goal
- **Percentage tracking**: Shows completion percentage

### 11. Generation Preview Editing
Fine-tune before generating:
- **Editable outline**: Modify scene outline in generation preview
- **Last-minute tweaks**: Adjust wording without editing the scene record
- **Scene modal**: Scene editing now in modal overlay for better UX

## Scene Summary & Continuity System

### The Problem
- Full scenes are ~1,500-2,000 words (~2,500 tokens)
- Including 10 previous scenes = ~25,000 tokens
- Quickly exhausts context window

### The Solution
- Compress scenes into 300-500 word summaries (~600 tokens)
- Include 10 previous summaries = ~6,000 tokens
- Saves ~19,000 tokens while maintaining continuity

### How It Works

**When a scene is accepted as canon**:
1. System automatically generates a concise summary
2. Scene marked as `is_canon: true`
3. Prose and summary saved to scene record
4. Future scenes automatically include this summary in context

**Scene Model**:
```json
{
  "id": "scene-002",
  "title": "Into the Temple",
  "scene_number": 2,
  "outline": "...",
  "character_ids": ["elena-blackwood"],
  "world_context_ids": ["shattered-empire"],
  "previous_scene_ids": ["scene-001"],
  "is_canon": false,
  "prose": null,
  "summary": null,
  "edit_mode": false,
  "original_prose": null
}
```

### Summary Content
Summaries capture:
1. Key events and plot advancement
2. Character development and revelations
3. Emotional beats
4. World state changes
5. Open threads and unresolved conflicts
6. Continuity details for future reference

### Token Budget Example
```
Previous summaries (10 scenes): ~6,000 tokens
Character sheets (3 chars):     ~3,000 tokens
World context (2 files):        ~4,000 tokens
Scene outline:                  ~1,000 tokens
Reference documents:            ~3,000 tokens
System prompts:                 ~2,000 tokens
-------------------------------------------
Total context:                 ~19,000 tokens
Remaining for output:         ~181,000 tokens ✅
```

## API Endpoints

### Health
- `GET /api/health` - Health check

### Series
- `GET /api/series/` - List all series
- `POST /api/series/` - Create series
- `GET /api/series/{series_id}` - Get series
- `PUT /api/series/{series_id}` - Update series
- `DELETE /api/series/{series_id}` - Delete series
- `POST /api/series/{series_id}/books` - Add book to series
- `DELETE /api/series/{series_id}/books/{project_id}` - Remove book
- `GET/POST/PUT/DELETE /api/series/{series_id}/characters/` - Series characters
- `GET/POST/PUT/DELETE /api/series/{series_id}/world/` - Series world
- `GET/PUT /api/series/{series_id}/style` - Series style guide
- `GET/POST/PUT/DELETE /api/series/{series_id}/references/` - Series references

### Projects (Books)
- `GET /api/projects/` - List all projects
- `POST /api/projects/` - Create project
- `GET /api/projects/{project_id}` - Get project
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project
- `DELETE /api/projects/{project_id}/structure` - Clear acts/chapters/scenes
- `PUT /api/projects/{project_id}/series` - Move to/from series

### Characters (Project-scoped)
- `GET /api/projects/{project_id}/characters/` - List all
- `GET /api/projects/{project_id}/characters/{id}` - Get by ID
- `POST /api/projects/{project_id}/characters/` - Create
- `PUT /api/projects/{project_id}/characters/{id}` - Update
- `DELETE /api/projects/{project_id}/characters/{id}` - Delete
- `POST /api/projects/{project_id}/characters/{id}/portrait` - Upload portrait
- `GET /api/projects/{project_id}/characters/{id}/portrait` - Get portrait image
- `DELETE /api/projects/{project_id}/characters/{id}/portrait` - Remove portrait
- `POST /api/projects/{project_id}/characters/import/parse` - Parse characters from text (AI)
- `POST /api/projects/{project_id}/characters/import/confirm` - Confirm and create parsed characters

### World Contexts (Project-scoped)
- `GET /api/projects/{project_id}/world/` - List all
- `GET /api/projects/{project_id}/world/{id}` - Get by ID
- `POST /api/projects/{project_id}/world/` - Create
- `PUT /api/projects/{project_id}/world/{id}` - Update
- `DELETE /api/projects/{project_id}/world/{id}` - Delete

### Scenes (Project-scoped)
- `GET /api/projects/{project_id}/scenes/` - List all
- `GET /api/projects/{project_id}/scenes/{id}` - Get by ID
- `POST /api/projects/{project_id}/scenes/` - Create
- `PUT /api/projects/{project_id}/scenes/{id}` - Update
- `DELETE /api/projects/{project_id}/scenes/{id}` - Delete
- `POST /api/projects/{project_id}/scenes/{id}/edit-mode` - Enable edit mode
- `DELETE /api/projects/{project_id}/scenes/{id}/edit-mode` - Disable edit mode

### References (Project-scoped)
- `GET /api/projects/{project_id}/references/` - List all
- `POST /api/projects/{project_id}/references/` - Create
- `GET /api/projects/{project_id}/references/{ref_id}` - Get by ID
- `PUT /api/projects/{project_id}/references/{ref_id}` - Update
- `DELETE /api/projects/{project_id}/references/{ref_id}` - Delete

### Generations (Project-scoped)
- `POST /api/projects/{project_id}/generations/start` - Start generation
- `POST /api/projects/{project_id}/generations/start-edit` - Start edit mode generation
- `GET /api/projects/{project_id}/generations/{id}` - Get state
- `POST /api/projects/{project_id}/generations/{id}/approve` - Approve & revise
- `POST /api/projects/{project_id}/generations/{id}/accept` - Accept as canon
- `POST /api/projects/{project_id}/generations/{id}/reject` - Reject

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Claude API key |
| `OPENROUTER_API_KEY` | (optional) | OpenRouter API key |
| `LLM_PROVIDER` | anthropic | Provider: anthropic or openrouter |
| `MAX_ITERATIONS` | 5 | Max revision loops |
| `GENERATION_MODEL` | claude-opus-4-5-20251101 | Prose model |
| `CRITIQUE_MODEL` | claude-sonnet-4-5-20250929 | Critique model |
| `GENERATION_TEMPERATURE` | 0.7 | Generation creativity |
| `CRITIQUE_TEMPERATURE` | 0.3 | Critique precision |
| `GENERATION_MAX_TOKENS` | 4000 | Max tokens for prose |
| `CRITIQUE_MAX_TOKENS` | 2000 | Max tokens for critique |
| `DATA_DIR` | ./data | Storage directory |
| `PORT` | 8000 | Server port |

## Key Design Decisions

### 1. File-Based Storage
**Why**: Simplicity, portability, version control friendly
- No database setup required
- Easy to backup and migrate
- Git-friendly for characters/world building

### 2. Separate Models for Generation vs Critique
**Why**: Cost optimization and quality
- Opus for creative prose generation (higher quality)
- Sonnet for analytical critique (faster, cheaper)

### 3. Manual Approval Loop
**Why**: User control and quality assurance
- User reviews each critique before revision
- Prevents runaway revisions
- User decides when prose is "good enough"

### 4. Scene Summaries (Not Full Text)
**Why**: Token efficiency and scalability
- Saves 80% tokens per previous scene
- Scales to 50+ scenes without context issues
- Maintains continuity without overwhelming context

### 5. Series Inheritance
**Why**: Consistency across multi-book projects
- Series resources cascade to all books
- Book resources can override series defaults
- Shared characters/world maintain consistency

### 6. Markdown for Characters/World
**Why**: Human-readable, easy to edit
- Can edit files directly in any text editor
- YAML frontmatter for structured data
- Markdown body for rich descriptions

### 7. Vanilla Frontend
**Why**: Simplicity, no build step
- No npm, webpack, or bundlers needed
- Instant updates without compilation
- Easy to understand and modify

## Running the Project

### Local Development
```bash
cd prose-pipeline
source venv/bin/activate
cd backend
DATA_DIR=../data uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Access
- Web UI: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## Best Practices

### Scene Numbering
- Use sequential numbers: 1, 2, 3, 4...
- Helps chronological sorting
- Makes reordering easier

### Previous Scene IDs
- Always specify which scenes come before
- Empty array `[]` only for first scene
- Include all relevant previous scenes

### Canon Status
- Only mark canon when truly final
- Once canon, summary is generated
- Other scenes may reference it
- Changing canon scenes breaks continuity

### Token Budget
- Monitor total context usage
- Keep under ~50,000 tokens for safety
- Each summary: ~600 tokens
- Each character: ~1,000 tokens
- Each world context: ~2,000 tokens

### Series Organization
- Group related books in a series
- Use series-level characters for recurring characters
- Book-specific characters for single-book characters
- Reference documents at appropriate scope

## Troubleshooting

### File not found errors
- Check `DATA_DIR` environment variable
- Verify data directories exist
- Check file permissions

### API key errors
- Verify `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` in `.env`
- Ensure key is valid and has credits

### Generation hangs
- Check logs for rate limiting
- Verify internet connectivity
- Consider reducing `MAX_ITERATIONS`

## Project Status

The project is fully functional with:
- Complete backend API
- Working web interface
- Critique-revision loop
- Scene summary system
- **Series system** for multi-book projects
- **Reference library** for importing context documents
- **Edit mode** for revising existing prose
- **Dynamic model selection** - Fetches available models from OpenRouter API
- **Default model settings** - Configure preferred generation/critique models
- **Word count goals** - Track progress with visual progress bar
- **Editable generation preview** - Tweak scene outline before generating
- Docker deployment support

Ready for production use for personal prose generation projects.
