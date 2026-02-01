# Prose Pipeline - Development Notes

**Last Updated:** 2026-02-01

---

## Project Overview

AI-powered prose generation pipeline for long-form fiction. Features a critique-revision loop, series continuity, and a unified web workspace.

**Core Philosophy:** Output prose indistinguishable from skilled human authors. No AI tells. No banned vocabulary. Authentic voice.

---

## Architecture

```
Frontend (Vanilla JS SPA)
    │
    ▼
FastAPI Backend
    │
    ├── Generation Service (critique-revision loop)
    ├── LLM Service (Anthropic + OpenRouter)
    ├── State Manager (file-based persistence)
    └── Prompt Templates (anti-AI-tell rules embedded)
```

**Data Storage:** File-based (JSON + Markdown), no database required.

---

## Key Services

| Service | Purpose |
|---------|---------|
| `generation_service.py` | Orchestrates generate → critique → revise loop |
| `llm_service.py` | Anthropic/OpenRouter API calls with caching |
| `state_manager.py` | Project/scene persistence, backup system |
| `prompt_templates.py` | All AI prompts with anti-AI-tell rules |

---

## Active Development

See `TODO.md` for:
- Current priorities (Series continuity for Book 2)
- Bug tracking
- Feature roadmap
- Session notes

---

## Server Locations

| Environment | Path | Notes |
|-------------|------|-------|
| Development | `/root/prose-pipeline` | This machine |
| Production | TBD | Docker deployment available |

---

## Key Decisions

1. **No database** - File-based storage for simplicity and portability
2. **Anti-AI-tells** - Banned vocabulary list enforced in all prompts
3. **Human-in-the-loop** - AI proposes, human decides
4. **Prompt caching** - Anthropic cache_control for 70% token cost reduction
5. **BYOK model** - OpenRouter for model flexibility and cost control

---

## Related Documentation

- `README.md` - Full feature documentation
- `QUICKSTART.md` - Getting started guide
- `CONTINUITY.md` - Scene summary system
- `TODO.md` - Development tracking and roadmap
- `outline_plan.md` - Outlining module design
