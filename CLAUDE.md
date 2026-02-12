# prose-pipeline (Prometheus) — AI Prose Generation Tool

**Repo:** https://github.com/zaphodsdad/prose-pipeline (public, MIT)
**App name:** Prometheus
**Stack:** Python 3.12 + FastAPI backend, vanilla HTML/CSS/JS frontend
**Data:** File-based (markdown + JSON), no database
**AI:** OpenRouter (300+ models), primarily Claude Opus for generation, Sonnet for critique

## What This Is

AI-powered prose generation tool for fiction writers. You give it characters, world docs, and scene outlines — it generates prose, critiques it, and iterates through a revision loop until you accept. Supports multi-book series with continuity tracking.

## Deployment

**Production:** Systemd service on LXC 304 (192.168.2.210), the MCP gateway server.
```
Web UI:       http://192.168.2.210:8000/
REST API:     http://192.168.2.210:8000/api/
MCP endpoint: http://192.168.2.210:8000/mcp/  (trailing slash required)
```

**Dev (LXC 101):** Run manually for development:
```bash
cd /root/prose-pipeline/backend
venv/bin/python -m app.main
# Web UI: http://192.168.2.187:8000
```

**Service management (on LXC 304):**
```bash
ssh root@192.168.2.184 "pct exec 304 -- systemctl restart prose-pipeline"
ssh root@192.168.2.184 "pct exec 304 -- journalctl -u prose-pipeline -f"
```

## MCP Wrapper

The MCP wrapper lives at `backend/prose_mcp/` and exposes **74 tools** covering the full writing workflow. It's a thin proxy layer — all tools call the FastAPI backend via HTTP.

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

**Tool modules (74 tools total):**
| Module | Tools | Coverage |
|--------|-------|----------|
| `tools/projects.py` | 11 | Project + series CRUD, export |
| `tools/structure.py` | 16 | Acts, chapters, beats CRUD |
| `tools/scenes.py` | 11 | Scene CRUD, prose, evaluate, edit mode, selection revise |
| `tools/characters.py` | 5 | Character CRUD |
| `tools/world.py` | 5 | World context CRUD |
| `tools/generation.py` | 7 | Start, poll, approve, accept, reject, list, queue |
| `tools/memory.py` | 6 | Series memory, continuity, summaries, scene extraction |
| `tools/extraction.py` | 3 | Manuscript import, manuscript analysis, health check |
| `tools/style.py` | 4 | Project + series style guides |
| `tools/outline.py` | 6 | Outline generation, cost estimation, scopes, apply, next scene |

**Transports:**
- `streamable-http` — embedded at `/mcp` on the FastAPI app (port 8000)
- `stdio` — `python -m prose_mcp.main` (for Claude Desktop local)
- `sse` — `TRANSPORT=sse SERVER_PORT=8001 python -m prose_mcp.main`

**Claude Desktop config (Mac):**
```json
{
  "mcpServers": {
    "prose-pipeline": {
      "url": "http://192.168.2.210:8000/mcp/"
    }
  }
}
```
Note the **trailing slash** — `/mcp/` not `/mcp`. Without it you get 404.

**MCP proxy gotcha:** FastAPI list endpoints (routes defined as `@router.get("/")`) require trailing slashes when mounted at a prefix. All MCP tool proxy paths in `prose_mcp/tools/*.py` must include trailing slashes for list/create endpoints (e.g. `/api/projects/` not `/api/projects`). Single-resource endpoints like `/api/projects/{id}` work without.

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
│   └── tools/               # 10 tool modules (74 tools)
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
| `PERSONA_MCP_URL` | http://192.168.2.210:8091/mcp | Persona MCP server URL |

## Persona MCP Integration

The Chico AI assistant supports **Persona MCP** for persistent identity and memory. When a `persona_id` is set in Chico's per-series settings, the assistant's identity, memories, and emotional state come from Persona MCP instead of static personality templates.

**How it works:**
1. User sends message via Chico floating widget
2. PP fetches persona context from Persona MCP (experiences, emotional arc, callbacks)
3. PP loads series knowledge locally (characters, world, scenes, memory — same as always)
4. PP builds system prompt combining persona identity + series knowledge
5. PP calls OpenRouter for chat response
6. PP saves to local history (for UI display)
7. PP submits interaction summary as experience to Persona MCP (memory evolves)

**Fallback:** If Persona MCP is unreachable or `persona_id` is null, Chico works in stateless mode (original behavior). No breakage.

**Settings UI:** The Chico settings modal has a "Persona" dropdown that lists available Persona MCP personas (e.g., Mirror, Editor) with a connection status indicator. When a persona is selected, the name/personality fields are hidden since identity comes from Persona MCP.

**Key files:**
- `backend/app/services/persona_client.py` — Reusable HTTP client for Persona MCP (also used later by generation hooks)
- `backend/app/services/chico_service.py` — Chat logic with persona mode branching
- `backend/app/models/chico.py` — `ChicoSettings.persona_id` field
- `backend/app/api/routes/chico.py` — `GET /{series_id}/personas` endpoint

**Available personas:** Mirror (prose writer) and Editor (quality reviewer) are currently defined in Persona MCP on LXC 304.

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
- Chapter extraction (extract characters/world/memory from imported prose)
- Outline import (structured markdown → acts/chapters/scenes)
- Story templates
- Backups (scene versions, snapshots, checkpoints)
- Settings/admin
- LanguageTool grammar checking
- Reference library

**Note:** Chat/Chico AI assistant is intentionally NOT exposed via MCP. Chico now uses Persona MCP for identity/memory (see "Persona MCP Integration" above). Exposing Chico as MCP tools is unnecessary since Persona MCP already provides the relevant tools.

## TODO

- [x] ~~**Standalone deployment.**~~ Deployed to LXC 304 as systemd service (Feb 10, 2026). Starts on boot, accessible at `192.168.2.210:8000`.
- [ ] **Add remaining MCP tools.** Backups, outline import, and references are useful via MCP but lower priority.
- [ ] **Revision UI.** Three-panel diff view for the revision workflow (see REVISION-UI-SKETCH.md).
- [x] ~~**Persona MCP integration (chat).**~~ Chico's chat backend now uses Persona MCP for persistent identity and memory (Feb 12, 2026). Mirror and Editor personas available. Full cycle: fetch context → chat → submit experience.
- [ ] **Persona MCP generation hooks.** Pre-generation: inject persona emotional context into generation prompts. Post-canon: submit scene events as experiences. The persona_client.py is already built for this.
