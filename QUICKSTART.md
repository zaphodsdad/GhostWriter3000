# Quick Start Guide

## Testing the Prose Generation Pipeline (Phase 1)

The foundation is complete! Here's how to test what we have so far.

### What's Working Now

✅ **Project Structure** - All directories and files in place
✅ **Example Data** - Character, world, and scene examples
✅ **FastAPI Backend** - Basic server with health check endpoint
✅ **Web Interface** - Basic UI showing example data
✅ **Configuration** - Environment-based settings management

### What's Not Yet Implemented

⏳ **Data Management API** - CRUD endpoints for characters/world/scenes (Phase 2)
⏳ **Claude Integration** - Generation/critique/revision (Phase 3)
⏳ **Generation Pipeline** - Full orchestration and state management (Phase 4)
⏳ **Interactive Frontend** - Full UI with real-time updates (Phases 5-6)

## Quick Test (3 Steps)

### Step 1: Start the Server

Run the startup script:

```bash
./run_server.sh
```

This will:
- Create a virtual environment (if needed)
- Install Python dependencies
- Start the FastAPI server on port 8000

### Step 2: View the Web Interface

Open your browser to:

```
http://localhost:8000
```

You'll see:
- **Overview** - Project introduction and system status
- **Characters** - Elena Blackwood character profile
- **World** - The Shattered Empire setting
- **Scenes** - "Discovery in the Wastes" scene outline
- **Generate** - Instructions for the generation pipeline

### Step 3: Check API Health

Visit the API health endpoint:

```
http://localhost:8000/api/health
```

Or use curl:

```bash
curl http://localhost:8000/api/health
```

You should see:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-12T...",
  "version": "1.0.0"
}
```

## View Example Data Files

### Character Sheet

```bash
cat data/characters/elena-blackwood.md
```

This shows the markdown format with YAML frontmatter for character data.

### World Context

```bash
cat data/world/shattered-empire.md
```

This shows the world building information format.

### Scene Outline

```bash
cat data/scenes/scene-001.json
```

This shows the JSON format for scene definitions.

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

Currently, only the `/api/health` endpoint is available.

## Troubleshooting

### Port 8000 Already in Use

If port 8000 is already in use, edit `.env` and change:

```
PORT=8000
```

To a different port (e.g., `PORT=8080`), then restart the server.

### Python Virtual Environment Issues

If the virtual environment has issues:

```bash
# Remove the old venv
rm -rf backend/venv

# Run the script again to recreate it
./run_server.sh
```

### Missing Dependencies

If you get import errors:

```bash
# Activate virtual environment
source backend/venv/bin/activate

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Can't Access from Other Devices

The server binds to `0.0.0.0` by default, which means it's accessible from other devices on your network.

Find your server's IP:

```bash
hostname -I
```

Then access from another device:

```
http://YOUR_SERVER_IP:8000
```

## Next Steps

To continue building the pipeline:

1. **Phase 2**: Implement CRUD endpoints for characters, world contexts, and scenes
2. **Phase 3**: Add Claude API integration for generation and critique
3. **Phase 4**: Build the complete generation pipeline with state management
4. **Phase 5-6**: Complete the interactive web interface
5. **Phase 7**: Add Docker containerization

## Getting Your API Key

To use the generation features (Phase 3+), you'll need a Claude API key:

1. Visit https://console.anthropic.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Add it to your `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## File Structure Overview

```
prose-pipeline/
├── run_server.sh           # Quick start script
├── QUICKSTART.md          # This file
├── README.md              # Full documentation
├── .env                   # Your configuration
├── .env.example           # Configuration template
│
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   ├── config.py      # Settings
│   │   ├── models/        # Data models
│   │   ├── services/      # Business logic
│   │   ├── api/routes/    # API endpoints
│   │   └── utils/         # Utilities
│   └── requirements.txt   # Python dependencies
│
├── frontend/
│   ├── index.html         # Web interface
│   ├── css/main.css       # Styles
│   └── js/main.js         # JavaScript
│
└── data/
    ├── characters/        # Character markdown files
    ├── world/             # World context files
    ├── scenes/            # Scene JSON files
    └── generations/       # Generated prose (Phase 4+)
```

## Support

For questions or issues:
- Check the main README.md for detailed documentation
- Review the API docs at http://localhost:8000/docs
- Look at the example data files in the `data/` directory
