# Prose Pipeline Project - Claude Context

## Project Overview

The **Prose Pipeline** is an automated prose generation system built with Claude AI that implements a critique-revision loop for high-quality creative writing. It features a clean web interface for managing characters, world-building, and scene generation with automatic continuity tracking.

**Core Concept**: Generate prose from scene outlines, automatically critique it, and iteratively revise based on feedback until the user accepts the final version.

## Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript (no build tooling)
- **AI**: Claude API
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
    ├── characters/          # Character sheets (markdown + YAML)
    ├── world/               # World context (markdown + YAML)
    ├── scenes/              # Scene definitions (JSON)
    └── generations/         # Generation state files
```

### Layered Architecture
- **Models Layer**: Pydantic schemas for validation
- **Services Layer**: Business logic and Claude integration
- **API Layer**: FastAPI route handlers
- **Utils**: Shared prompts and utilities

## Key Features

### 1. Character Management
Characters stored as markdown files with YAML frontmatter:
```yaml
---
name: Jane Doe
age: 30
role: protagonist
personality_traits: [Brave, Curious]
skills: [Sword fighting, Ancient languages]
---

# Background
Jane grew up in...
```

### 2. World Building
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

### 3. Scene-Based Generation
Scenes defined as JSON with:
- Scene outline/description
- Character references
- World context references
- Tone, POV, target length
- **Previous scene references** (for continuity)

### 4. Critique-Revision Loop

**Workflow**:
```
1. User creates scene outline
2. Generate prose (using Opus)
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
  "summary": null
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
System prompts:                 ~2,000 tokens
-------------------------------------------
Total context:                 ~16,000 tokens
Remaining for output:         ~184,000 tokens ✅
```

## API Endpoints

### Health
- `GET /api/health` - Health check

### Characters
- `GET /api/characters` - List all
- `GET /api/characters/{id}` - Get by ID
- `POST /api/characters` - Create
- `PUT /api/characters/{id}` - Update
- `DELETE /api/characters/{id}` - Delete

### World Contexts
- `GET /api/world` - List all
- `GET /api/world/{id}` - Get by ID
- `POST /api/world` - Create
- `PUT /api/world/{id}` - Update
- `DELETE /api/world/{id}` - Delete

### Scenes
- `GET /api/scenes` - List all
- `GET /api/scenes/{id}` - Get by ID
- `POST /api/scenes` - Create
- `PUT /api/scenes/{id}` - Update
- `DELETE /api/scenes/{id}` - Delete

### Generations
- `POST /api/generations/start` - Start generation
- `GET /api/generations/{id}` - Get state
- `POST /api/generations/{id}/approve` - Approve & revise
- `POST /api/generations/{id}/accept` - Accept as canon
- `POST /api/generations/{id}/reject` - Reject

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Claude API key |
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

### 5. Markdown for Characters/World
**Why**: Human-readable, easy to edit
- Can edit files directly in any text editor
- YAML frontmatter for structured data
- Markdown body for rich descriptions

### 6. Vanilla Frontend
**Why**: Simplicity, no build step
- No npm, webpack, or bundlers needed
- Instant updates without compilation
- Easy to understand and modify

## Running the Project

### Local Development
```bash
cd prose-pipeline/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
DATA_DIR=./data python -m backend.app.main
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

## Future Enhancements

### Smart Summary Selection
- Analyze scene outline
- Identify relevant previous scenes
- Only include necessary summaries
- Further reduce token usage

### Summary Compression
For very long stories (100+ scenes):
- Generate chapter-level summaries
- Compress older scene summaries
- Keep recent scenes detailed

### Manual Summary Editing
- Allow users to edit auto-summaries
- Add continuity notes
- Mark key details for emphasis

### Continuity Checking
AI assistant that:
- Checks new prose against summaries
- Flags continuity errors
- Suggests corrections

## Troubleshooting

### File not found errors
- Check `DATA_DIR` environment variable
- Verify data directories exist
- Check file permissions

### API key errors
- Verify `ANTHROPIC_API_KEY` in `.env`
- Ensure key is valid and has credits

### Generation hangs
- Check logs for rate limiting
- Verify internet connectivity
- Consider reducing `MAX_ITERATIONS`

## Additional Documentation

- `README.md` - Full project documentation
- `CONTINUITY.md` - Detailed continuity system explanation
- `QUICKSTART.md` - Quick start guide
- `TEST_GENERATION.md` - Testing documentation
- `TEST_NOW.md` - Current test procedures
- `test_simple.py` - Simple test script

## Project Status

The project is fully functional with:
- Complete backend API
- Working web interface
- Critique-revision loop
- Scene summary system
- Docker deployment support

Ready for production use for personal prose generation projects.
