# Test the Prose Pipeline NOW!

## Quick Manual Setup (2 Minutes)

Since the automatic setup requires installing `python3-venv`, here's how to test manually:

### Option 1: Simple Test (No Dependencies)

Just open the HTML file directly in your browser to see the UI:

```bash
# From the prose-pipeline directory
firefox frontend/index.html
# or
google-chrome frontend/index.html
# or just open it in any browser
```

You'll see the complete UI with all the example data (Elena Blackwood character, The Shattered Empire world, and the scene outline).

**Note:** The API health check will show "Offline" since the backend isn't running yet, but you can explore all the UI sections.

### Option 2: Full Server Test (With Dependencies)

If you want to test the full stack with the API running:

#### 1. Install system dependencies:

```bash
sudo apt install python3-pip python3-venv
```

#### 2. Run the server:

```bash
./run_server.sh
```

#### 3. Open your browser:

```
http://localhost:8000
```

The health check will show "Online" and you can test the API endpoints.

### Option 3: Manual Server Start (Alternative)

If you prefer to do it manually:

```bash
# Install dependencies globally (or use --user flag)
pip3 install fastapi uvicorn anthropic pydantic pydantic-settings python-frontmatter pyyaml aiofiles python-dotenv --user

# Start the server
cd backend
python3 -m app.main
```

Then visit http://localhost:8000

## What You'll See

### Web Interface

The UI has 5 sections:

1. **Overview** - Project introduction, statistics, and system health
2. **Characters** - Elena Blackwood's complete character profile
3. **World** - The Shattered Empire setting with factions and geography
4. **Scenes** - "Discovery in the Wastes" scene outline
5. **Generate** - Instructions for the generation pipeline

### Example Data

All example files are ready to view:

**Character:**
```bash
cat data/characters/elena-blackwood.md
```

**World:**
```bash
cat data/world/shattered-empire.md
```

**Scene:**
```bash
cat data/scenes/scene-001.json
```

## Testing the API

Once the server is running, test the health endpoint:

```bash
# Check health
curl http://localhost:8000/api/health

# Should return:
# {
#   "status": "healthy",
#   "timestamp": "2026-01-12T...",
#   "version": "1.0.0"
# }
```

## Interactive API Docs

Visit these URLs while the server is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## What's Implemented vs. What's Coming

### ✅ Phase 1 - COMPLETE (Foundation)

- [x] Project structure with all directories
- [x] Configuration management (`.env` based)
- [x] Pydantic models for all data types
- [x] Markdown parser with YAML frontmatter support
- [x] File utilities with atomic writes
- [x] Prompt templates for Claude API
- [x] Basic FastAPI app with health check
- [x] Example data (character, world, scene)
- [x] Web UI showing all example data
- [x] README and documentation

### ⏳ Phase 2 - TODO (Data Management API)

- [ ] Character CRUD endpoints
- [ ] World context CRUD endpoints
- [ ] Scene CRUD endpoints
- [ ] File upload/download
- [ ] Validation and error handling

### ⏳ Phase 3 - TODO (Claude Integration)

- [ ] Claude service implementation
- [ ] Generation method
- [ ] Critique method
- [ ] Revision method
- [ ] Token usage tracking
- [ ] Error handling and retries

### ⏳ Phase 4 - TODO (Generation Pipeline)

- [ ] State manager with persistence
- [ ] Generation orchestration service
- [ ] Pipeline endpoints (start, approve, accept, reject)
- [ ] Background task processing
- [ ] WebSocket or polling for real-time updates

### ⏳ Phases 5-6 - TODO (Interactive Frontend)

- [ ] API client wrapper
- [ ] Scene editor component
- [ ] Character/world viewer components
- [ ] Generation controls
- [ ] Prose viewer with formatting
- [ ] Critique viewer
- [ ] Approval panel with actions
- [ ] Real-time status updates

### ⏳ Phase 7 - TODO (Docker & Polish)

- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] Production configuration
- [ ] Logging and monitoring
- [ ] End-to-end tests

## Current File Count

```
22 Python files
3 Example data files
1 HTML page
1 CSS file
1 JavaScript file
3 Documentation files
2 Configuration files
---
33 total files created
```

## Estimated Progress

**Phase 1:** 100% Complete ✅
**Overall Project:** ~15% Complete

The foundation is solid and ready for the next phases!

## Next Steps

Once you've tested the current implementation, let me know if you'd like me to:

1. **Continue with Phase 2** - Implement the data management API endpoints
2. **Jump to Phase 3** - Implement Claude API integration
3. **Build out the frontend** - Make the UI fully interactive
4. **Add Docker** - Create containerization for easy deployment
5. **Something else** - Any specific feature or change you'd like

Enjoy exploring the example data!
