# GhostWriter 3000

> AI-powered prose generation engine for fiction writers. Critique-revision loop, series memory, continuity tracking, and 300+ LLM models via OpenRouter.

<!-- TODO: Add screenshot/GIF of the UI here -->

## About This Project

I'm John Burks. I always wanted to write. Life had other plans.

I spent 20 years in oil and gas — MWD coordination, field operations, real-time operations centers, facilities management. I was good at it. I ran crews, managed complex systems under pressure, and kept things moving when everything was trying to fall apart. But corporate oilfield culture ground the passion out of me. It's a dog-eat-dog world and after two decades I was done.

The writing never stopped, though. I've been a fiction writer my whole adult life — took some swings at self-publishing years ago, never quite landed it because the mechanics of getting stories onto the page always outpaced the hours in the day. I've got multiple novels in progress, a head full of characters and plot, and not enough time.

I'd been using NovelCrafter, which is genuinely great software. But I hate subscriptions when I can avoid them. Then I discovered vibe coding — building real applications with AI assistance — and this was the first thing I thought of. A writing engine I own, that runs on my own hardware, that remembers my entire series and lets me pick any model I want. I started coding a few weeks ago. This is the result.

**Great stories shouldn't be trapped by writing mechanics.** GhostWriter 3000 helps storytellers who have vivid characters, compelling plots, and rich worlds — but need help getting them onto the page. It generates natural prose, critiques it, revises it, and learns your writing style over time.

Built with Python/FastAPI and a retro-futuristic vanilla JS frontend. No database — everything is markdown and JSON files. Bring your own API key.

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/zaphodsdad/ghostwriter3000.git
cd ghostwriter3000
make docker
```

### Local

```bash
git clone https://github.com/zaphodsdad/ghostwriter3000.git
cd ghostwriter3000
make run
```

Both methods open the UI at **http://localhost:8000**. Add your [OpenRouter API key](https://openrouter.ai/keys) in Settings — that's it. Demo data is included so you can explore immediately.

## What It Does

### The Core Loop

```
Scene Outline → Generate Prose → AI Critique → Revise → Repeat → Accept as Canon
```

You define characters, world context, and scene outlines. The AI generates prose, then a second AI pass critiques it. You review, give feedback, and the system revises — up to 5 iterations until you're happy. When you accept a scene as canon, it becomes part of the series memory.

### Series Memory

This is the differentiator. Most AI writing tools are stateless — each generation starts from scratch. GhostWriter 3000 accumulates knowledge across your entire series:

- **Automatic extraction** — when scenes become canon, the system extracts characters, world elements, plot events, and causal chains
- **Tiered summaries** — book-level and scene-level summaries assembled into context for each generation
- **Memory decay** — older facts deprioritized by book distance so recent events feel more present
- **Continuity checking** — LLM-based detection of contradictions with established canon
- **Style learning** — the system learns your voice from your edits (vocabulary, sentence structure, dialogue patterns)

### AI Writing Assistant

Each series gets a conversational AI assistant (default name: "Chico") that knows everything about your series — characters, world, plot, current prose. Ask it questions, check continuity, brainstorm plot points. Supports optional integration with [Persona MCP](https://github.com/zaphodsdad) for persistent AI identity and emotional memory.

## Features

| Category | What |
|----------|------|
| **Generation** | Critique-revision loop, polish mode, evaluate-only, batch queue, floating inline revision bubble |
| **Structure** | Acts, chapters, scenes with beats. Manual creation or auto-generated outlines |
| **Import** | Manuscript import (.docx/.txt/.md), structured outline import with full metadata extraction |
| **Characters** | Markdown + YAML frontmatter, portrait support, bulk import, chapter-by-chapter extraction from existing prose |
| **World** | World context files, automatic extraction, location/magic/politics/creature categorization |
| **Memory** | Series memory layer, causal chains, decay, staleness detection, tiered summaries |
| **Continuity** | Cross-scene summaries, LLM contradiction detection, series-level knowledge |
| **Style** | Style learning from edits, per-series style guides, reference library for tone/voice examples |
| **Models** | 300+ models via OpenRouter with live pricing. DeepSeek for cost, Claude for quality. BYOK |
| **Backup** | Auto-backup before destructive ops, scene version history, project snapshots, full data export |
| **UI** | Dark/light themes, generation queue with review panel, word count goals, credit alerts |
| **MCP** | 74 MCP tools across 10 modules (see below) |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Web UI (vanilla JS)                │
│         Retro-futuristic dark theme / light theme     │
└─────────────────────┬────────────────────────────────┘
                      │ HTTP
┌─────────────────────▼────────────────────────────────┐
│                FastAPI Backend (Python)               │
│                                                      │
│  Routes ──→ Services ──→ LLM Service ──→ OpenRouter  │
│    │            │                                    │
│    │     ┌──────┴──────────┐                         │
│    │     │  Memory Service │  Style Learning          │
│    │     │  Entity Service │  Continuity Checking     │
│    │     │  Persona Client │  Generation Queue        │
│    │     └─────────────────┘                         │
│    │                                                 │
│  MCP Wrapper (74 tools) ──→ FastMCP ──→ /mcp/        │
└─────────────────────┬────────────────────────────────┘
                      │ File I/O
┌─────────────────────▼────────────────────────────────┐
│              File-Based Storage                       │
│  projects/ ── characters/ ── world/ ── scenes/       │
│  series/   ── memory/     ── style/  ── generations/ │
│              (Markdown + JSON, no database)           │
└──────────────────────────────────────────────────────┘
```

### MCP Integration

GhostWriter 3000 exposes its full API as **74 MCP (Model Context Protocol) tools** across 10 modules. This means any MCP-compatible client — Claude Desktop, custom agents, bots — can drive the entire writing workflow programmatically.

| Module | Tools | Coverage |
|--------|-------|----------|
| Projects | 11 | Project + series CRUD, export |
| Structure | 16 | Acts, chapters, beats CRUD |
| Scenes | 11 | Scene CRUD, prose, evaluate, edit mode, selection revise |
| Characters | 5 | Character CRUD |
| World | 5 | World context CRUD |
| Generation | 7 | Start, poll, approve, accept, reject, list, queue |
| Memory | 6 | Series memory, continuity, summaries, scene extraction |
| Extraction | 3 | Manuscript import, analysis, health check |
| Style | 4 | Project + series style guides |
| Outline | 6 | Outline generation, cost estimation, scopes, apply |

MCP endpoint: `http://localhost:8000/mcp/` (trailing slash required).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic, uvicorn |
| Frontend | Vanilla HTML/CSS/JavaScript (no build step) |
| AI | OpenRouter API (300+ models), optional Persona MCP |
| Data | File-based (Markdown + YAML frontmatter, JSON) |
| MCP | FastMCP (streamable-http transport) |
| Deploy | Docker, docker-compose, or bare Python |

## Project Structure

```
ghostwriter3000/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # 20 route modules
│   │   ├── models/          # Pydantic data models
│   │   ├── services/        # Business logic, LLM, memory, style
│   │   └── utils/           # Prompts, backup, file I/O
│   ├── prose_mcp/           # MCP wrapper (74 tools, 10 modules)
│   └── requirements.txt
├── frontend/
│   ├── css/styles.css       # Single stylesheet, CSS variables
│   ├── js/app.js            # Single JS file, no framework
│   └── index.html           # Single HTML file
├── data/                    # Demo data (characters, scenes, world)
├── docker/                  # Dockerfile
├── docker-compose.yml       # One-command deployment
├── Makefile                 # make run | make docker | make stop
└── .env.example             # Configuration template
```

## Configuration

All settings can be configured through the UI (Settings panel) or via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `GENERATION_MODEL` | deepseek/deepseek-chat-v3.1 | Model for prose generation |
| `CRITIQUE_MODEL` | deepseek/deepseek-chat-v3.1 | Model for critique |
| `MAX_ITERATIONS` | 5 | Max revision iterations per generation |
| `DATA_DIR` | ./data | Data storage directory |
| `PORT` | 8000 | Server port |
| `API_AUTH_KEY` | (empty) | Optional API key for authentication |

Full list in [.env.example](.env.example). API docs at `http://localhost:8000/docs` (Swagger UI).

## Design Decisions

**Why file-based storage?** Simplicity. Characters and world docs are markdown files you can edit in any text editor. Scenes are JSON. No database setup, no migrations, easy to back up (just copy the folder). For a single-user writing tool, this is the right tradeoff.

**Why vanilla JS?** No build step means anyone can clone and run. The frontend is one HTML file, one CSS file, one JS file. It works. For a tool that's about writing, not about the UI framework, this keeps the focus where it belongs.

**Why OpenRouter?** One API key gives you 300+ models from every major provider. Writers can use cheap models (DeepSeek at $0.14/M tokens) for iteration and expensive ones (Claude Opus) for final passes. No vendor lock-in.

**Why MCP?** The writing engine is useful beyond the web UI. MCP tools let Claude Desktop, Discord bots, or custom agents drive the full workflow. The 74-tool surface was designed for this.

## License

MIT License — see [LICENSE](LICENSE) for details.
