# prose-pipeline (Prometheus) — AI Prose Generation Tool

**Repo:** https://github.com/zaphodsdad/prose-pipeline (public, MIT)
**App name:** Prometheus
**Stack:** Python 3.12 + FastAPI backend, vanilla HTML/CSS/JS frontend
**Data:** File-based (markdown + JSON), no database
**AI:** OpenRouter (300+ models), primarily Claude Opus for generation, Sonnet for critique

## What This Is

AI-powered prose generation tool for fiction writers. You give it characters, world docs, and scene outlines — it generates prose, critiques it, and iterates through a revision loop until you accept. Supports multi-book series with continuity tracking.

## Running the App

```bash
cd /root/prose-pipeline/backend
python3 -m app.main
# Web UI: http://192.168.2.187:8000
# API docs: http://192.168.2.187:8000/docs
# MCP endpoint: http://192.168.2.187:8000/mcp
```

## MCP Wrapper

The MCP wrapper lives at `backend/prose_mcp/` and exposes **66 tools** covering the full writing workflow. It's a thin proxy layer — all tools call the FastAPI backend via HTTP.

**Architecture:**
```
Claude (Desktop/Code/MCP client)
    ↓ MCP protocol
prose_mcp (FastMCP server)
    ↓ HTTP calls
FastAPI backend (http://127.0.0.1:8000)
    ↓
File-based data storage
```

**Tool modules (66 tools total):**
| Module | Tools | Coverage |
|--------|-------|----------|
| `tools/projects.py` | 11 | Project + series CRUD, export |
| `tools/structure.py` | 16 | Acts, chapters, beats CRUD |
| `tools/scenes.py` | 11 | Scene CRUD, prose, evaluate, edit mode, selection revise |
| `tools/characters.py` | 5 | Character CRUD |
| `tools/world.py` | 5 | World context CRUD |
| `tools/generation.py` | 7 | Start, poll, approve, accept, reject, list, queue |
| `tools/memory.py` | 5 | Series memory, continuity, summaries |
| `tools/extraction.py` | 2 | Manuscript analysis, health check |
| `tools/style.py` | 4 | Project + series style guides |

**Transports:**
- `streamable-http` — embedded at `/mcp` on the FastAPI app (port 8000)
- `stdio` — `python -m prose_mcp.main` (for Claude Desktop local)
- `sse` — `TRANSPORT=sse SERVER_PORT=8001 python -m prose_mcp.main`

**Claude Desktop config (Mac):**
```json
{
  "mcpServers": {
    "prose-pipeline": {
      "url": "http://192.168.2.187:8000/mcp"
    }
  }
}
```

## Key Directories

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point, MCP mount
│   ├── routes/              # All API route handlers
│   ├── services/            # Business logic, LLM calls
│   ├── models/              # Pydantic models
│   └── utils/               # Prompts, logging, helpers
├── prose_mcp/
│   ├── server.py            # FastMCP setup, tool registration
│   ├── client.py            # HTTP client (proxies to FastAPI)
│   ├── main.py              # Standalone entry point
│   └── tools/               # 9 tool modules (66 tools)
frontend/                    # Vanilla HTML/CSS/JS web UI
data/                        # Sample/test data files
```

## Environment Variables

| Variable | Default | What |
|----------|---------|------|
| `PORT` | 8000 | Server port |
| `DATA_DIR` | ./data | Data storage path |
| `GENERATION_MODEL` | deepseek/deepseek-chat-v3.1 | Prose generation model |
| `CRITIQUE_MODEL` | deepseek/deepseek-chat-v3.1 | Critique model |
| `MAX_ITERATIONS` | 5 | Max revision iterations |

## Chapter Extraction

The Structure tab has an **Extract** button that analyzes imported prose chapter-by-chapter using AI, extracting:
- **Characters** — saved as markdown files in `data/series/{series_id}/characters/`
- **World elements** — locations, creatures, magic, politics, etc. in `data/series/{series_id}/world/`
- **Memory** — plot events, character state changes, world facts per scene in `data/series/{series_id}/memory/`

Requires the project to be in a series (entities save at series level). Processes one chapter at a time to stay within LLM context limits. Progress popup shows current chapter, running totals, and overall progress. Re-running is safe — entity service merges new data with existing.

**Endpoints:**
- `POST /api/projects/{id}/extract-chapters/extract` — start background extraction
- `GET /api/projects/{id}/extract-chapters/extract/status` — poll progress
- `POST /api/projects/{id}/extract-chapters/extract/cancel` — stop at next chapter

**Code:** `backend/app/api/routes/chapter_extraction.py`

## Not Exposed via MCP (Yet)

These backend features exist but aren't MCP tools:
- Chat/Chico AI assistant
- Chapter extraction (extract characters/world/memory from imported prose)
- Manuscript import (.docx/.txt/.md upload)
- Outline import (structured markdown → acts/chapters/scenes)
- Story templates
- Auto-generate outline from premise
- Backups (scene versions, snapshots, checkpoints)
- Settings/admin
- LanguageTool grammar checking
- Reference library

## TODO

- [ ] **Fix extraction progress modal.** The Extract button triggers the backend correctly and extraction runs, but the progress popup doesn't appear in the browser. Likely a static file caching issue — the JS code is correct (verified IDs match between index.html and app.js). Debug: hard refresh, check browser console for errors, verify the modal element exists in DOM. The 409 "already running" case now correctly opens the modal + starts polling instead of showing an error toast.
- [ ] **Standalone deployment.** Move prose-pipeline backend out of VS Code Server terminal into a proper systemd service or LXC container. It should start on boot and stay running independently. The MCP wrapper should also run standalone (SSE on LXC 304 with the other MCPs, proxying back to the backend).
- [ ] **Add remaining MCP tools.** Chat/Chico, backups, manuscript import, outline import, and references are useful via MCP but lower priority.
- [ ] **Revision UI.** Three-panel diff view for the revision workflow (see REVISION-UI-SKETCH.md).
- [ ] **Personage MCP integration.** This project's memory system (memory_service.py, character persistence, style learning) is a candidate for extraction into the shared Personage MCP layer.
