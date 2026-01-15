# Prose Generation Pipeline

An automated prose generation pipeline with critique-revision loop powered by Claude AI. Features a clean web interface for managing characters, world context, and scene generation.

## Features

- **Web-based Interface**: Clean, modern UI for managing all aspects of prose generation
- **Character Management**: Store character sheets as markdown files with YAML frontmatter, with portrait support and bulk import
- **World Building**: Maintain world context files for consistent story elements
- **Scene-based Generation**: Generate prose from detailed scene outlines
- **Critique-Revision Loop**: Automatic critique with manual approval for each revision iteration
- **Series System**: Group related books with shared characters, world-building, and style guides
- **Reference Library**: Import style guides, published works, or notes as AI context
- **Edit Mode**: Revise existing prose through the critique loop
- **Manuscript Import**: Upload .docx/.txt/.md files, auto-detect chapters, create scenes in edit mode
- **Continuity System**: Automatically includes summaries from last 10 scenes for context
- **Dynamic Model Selection**: Choose from available OpenRouter models with live pricing
- **Default Model Settings**: Configure preferred generation and critique models
- **Word Count Goals**: Track progress toward writing targets with visual progress bar
- **Credit Alerts**: Notifications when OpenRouter balance drops below threshold
- **Docker Support**: Easy deployment with Docker and docker-compose

## Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript (no build step required)
- **AI**: Claude API (Opus for generation, Sonnet for critique)
- **Data**: File-based storage with markdown and JSON

## Project Structure

```
prose-pipeline/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── models/       # Pydantic data models
│   │   ├── services/     # Business logic
│   │   ├── api/routes/   # REST API endpoints
│   │   └── utils/        # Utilities
│   └── requirements.txt
├── frontend/             # Web UI
│   ├── css/
│   ├── js/
│   └── index.html
├── data/                 # Data storage
│   ├── characters/       # Character markdown files
│   ├── world/            # World context markdown files
│   ├── scenes/           # Scene JSON files
│   └── generations/      # Generation state files
└── docker/               # Docker configuration
```

## Quick Start

### Prerequisites

- Python 3.11+
- Claude API key from Anthropic
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Clone and navigate to the project**:
   ```bash
   cd prose-pipeline
   ```

2. **Set up Python environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp ../.env.example ../.env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

4. **Run the application**:
   ```bash
   cd ..
   DATA_DIR=./data python -m backend.app.main
   ```

5. **Access the web interface**:
   Open your browser to `http://localhost:8000`

### Docker Deployment

1. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

2. **Build and run with docker-compose**:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

3. **Access the web interface**:
   Open your browser to `http://localhost:8000`

## Usage

### Creating Characters

Characters are stored as markdown files with YAML frontmatter in `data/characters/`.

**Example** (`data/characters/protagonist.md`):

```markdown
---
name: Jane Doe
age: 30
role: protagonist
personality_traits:
  - Brave
  - Curious
skills:
  - Sword fighting
  - Ancient languages
---

# Jane Doe

## Background
Jane grew up in a small village...

## Voice and Mannerisms
- Speaks confidently
- Uses military jargon
```

### Creating World Context

World building information is stored in `data/world/` as markdown files.

**Example** (`data/world/fantasy-realm.md`):

```markdown
---
name: The Kingdom of Aldoria
era: Medieval fantasy
magic_system: Elemental magic
technology_level: Medieval
---

# The Kingdom of Aldoria

## History
The kingdom was founded 500 years ago...

## Current Political Climate
The kingdom is ruled by Queen Eleanor...
```

### Creating Scenes

Scenes are defined as JSON files in `data/scenes/`.

**Example** (`data/scenes/scene-001.json`):

```json
{
  "id": "scene-001",
  "title": "The Tavern Meeting",
  "outline": "Jane meets her old friend at a tavern and learns about a new quest...",
  "character_ids": ["jane-doe"],
  "world_context_ids": ["fantasy-realm"],
  "tone": "Mysterious and intriguing",
  "pov": "Third person limited",
  "target_length": "1000-1500 words"
}
```

### Generation Workflow

1. **Create or select a scene** in the web interface
2. **Click "Generate"** to start the pipeline
3. **Review the generated prose** when complete
4. **Read the automatic critique** of the prose
5. **Choose an action**:
   - **Approve & Revise**: Triggers a revision based on the critique
   - **Accept Final**: Marks the prose as complete
   - **Reject**: Cancels the generation
6. **Repeat** the critique-revision loop up to the maximum iterations (default: 5)

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Key Endpoints

#### Health Check
```
GET /api/health
```

#### Characters
```
GET    /api/characters          # List all characters
GET    /api/characters/{id}     # Get character by ID
POST   /api/characters          # Create new character
PUT    /api/characters/{id}     # Update character
DELETE /api/characters/{id}     # Delete character
```

#### World Contexts
```
GET    /api/world               # List all world contexts
GET    /api/world/{id}          # Get world context by ID
POST   /api/world               # Create new world context
PUT    /api/world/{id}          # Update world context
DELETE /api/world/{id}          # Delete world context
```

#### Scenes
```
GET    /api/scenes              # List all scenes
GET    /api/scenes/{id}         # Get scene by ID
POST   /api/scenes              # Create new scene
PUT    /api/scenes/{id}         # Update scene
DELETE /api/scenes/{id}         # Delete scene
```

#### Generations
```
POST   /api/generations/start              # Start new generation
GET    /api/generations/{id}               # Get generation state
POST   /api/generations/{id}/approve       # Approve & revise
POST   /api/generations/{id}/accept        # Accept final
POST   /api/generations/{id}/reject        # Reject generation
```

## Configuration

All configuration is managed through environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Your Claude API key |
| `MAX_ITERATIONS` | 5 | Maximum revision iterations |
| `GENERATION_MODEL` | claude-opus-4-5-20251101 | Model for prose generation |
| `CRITIQUE_MODEL` | claude-sonnet-4-5-20250929 | Model for critique |
| `GENERATION_TEMPERATURE` | 0.7 | Temperature for generation |
| `CRITIQUE_TEMPERATURE` | 0.3 | Temperature for critique |
| `GENERATION_MAX_TOKENS` | 4000 | Max tokens for generation |
| `CRITIQUE_MAX_TOKENS` | 2000 | Max tokens for critique |
| `DATA_DIR` | ./data | Data storage directory |
| `PORT` | 8000 | Server port |

## Development

### Running Tests

```bash
cd backend
pytest
```

### Project Structure

The codebase follows a clean layered architecture:

- **Models Layer** (`app/models/`): Pydantic models for data validation
- **Services Layer** (`app/services/`): Business logic and Claude API integration
- **API Layer** (`app/api/routes/`): FastAPI route handlers
- **Utils** (`app/utils/`): Shared utilities and prompt templates

### Adding New Features

1. **Add data model** in `app/models/`
2. **Implement service** in `app/services/`
3. **Create API routes** in `app/api/routes/`
4. **Register routes** in `app/main.py`
5. **Add frontend components** in `frontend/js/components/`

## Troubleshooting

### "File not found" errors
- Ensure `DATA_DIR` environment variable points to the correct directory
- Check that data directories exist and have proper permissions

### API key errors
- Verify `ANTHROPIC_API_KEY` is set in `.env`
- Ensure the API key is valid and has sufficient credits

### Generation hangs
- Check logs for rate limiting errors
- Verify internet connectivity to Claude API
- Consider reducing `MAX_ITERATIONS` or token limits

## License

This project is provided as-is for personal use.

## Support

For issues and feature requests, please open an issue on the project repository.
