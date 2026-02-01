# Quick Start Guide

Get up and running with the Prose Generation Pipeline in minutes.

## Prerequisites

- Python 3.11+
- An API key from one of:
  - **Anthropic** (Claude API) - recommended for best quality
  - **OpenRouter** - for model variety and cost control

## Quick Start (3 Steps)

### Step 1: Start the Server

```bash
./run_server.sh
```

This will:
- Create a virtual environment (if needed)
- Install Python dependencies
- Start the FastAPI server on port 8000

### Step 2: Open the Web Interface

```
http://localhost:8000
```

### Step 3: Configure API Keys

1. On the start page, expand the **Settings** panel
2. Enter your **Anthropic API Key** and/or **OpenRouter API Key**
3. Select your preferred generation and critique models
4. Click **Save**

You're ready to write!

## Creating Your First Project

1. Click **New Project** on the start page
2. Enter a project name (e.g., "My Novel")
3. Optionally assign it to a Series for multi-book continuity

## Adding Content

### Option A: Import an Existing Manuscript

1. Go to **Structure** tab → **Import**
2. Upload a `.docx`, `.txt`, or `.md` file
3. The system auto-detects chapters and creates scenes
4. Each chapter becomes ready for the critique/revision loop

### Option B: Import a Structured Outline

1. Go to **Structure** tab → **Import Outline**
2. Paste a markdown outline with acts, chapters, and scenes
3. Preview the parsed structure
4. Click **Import** to create all scenes at once

### Option C: Build Structure Manually

1. Go to **Structure** tab
2. Click **+ Act** to create an act
3. Click **+ Chapter** within an act
4. Click **+ Scene** within a chapter
5. Fill in scene outlines, POV, tone, target length

## Generating Prose

1. Click any scene in the sidebar
2. The **Unified Workspace** opens
3. Click **Generate** to start AI prose generation
4. Review the generated prose and automatic critique
5. Choose:
   - **Approve & Revise** - trigger another revision pass
   - **Accept as Canon** - finalize the scene
   - **Reject** - discard and try again

## Key Features

| Feature | How to Access |
|---------|---------------|
| Characters | Characters tab → + New Character |
| World Building | Worlds tab → + New World Context |
| References | References tab → upload style guides, examples |
| Series | Start page → + New Series (for multi-book projects) |
| Book Summary | Structure tab → Book Summary section (for series continuity) |
| Batch Generation | Select multiple scenes → Generate Selected |
| Evaluate Only | Click Evaluate to get critique without revision |
| Floating AI Bubble | Select text in prose view for quick AI edits |

## Series Continuity

For multi-book series:

1. Create a **Series** on the start page
2. Add books to the series (use book number 0 for prequels)
3. Write a **Book Summary** in the Structure tab when a book is complete
4. Later books can reference earlier book summaries for continuity

### Chico AI Assistant

Each series has **Chico**, a floating AI assistant that knows everything about your series:

1. Click the **Chico** toggle button (bottom-right corner)
2. Ask questions: "Who is Elena's love interest?" or "What happened in Book 1?"
3. Get continuity checks: "Does this contradict anything established?"
4. Brainstorm: "Give me 3 ways the betrayal could be revealed"

Chico's name and personality can be customized in the settings modal.

### Memory Layer

When you mark scenes as canon, the system automatically:

- **Extracts facts**: Character changes, world elements, plot events
- **Applies decay**: Older facts get lower weight in later books
- **Learns your style**: Detects patterns from your edits
- **Tracks causality**: Links plot events by cause and consequence

Use the Memory endpoints to generate summaries or check what the AI "knows" about your series.

### Series Dashboard

When you click a series on the start page, a dashboard appears showing:

- **Stats**: Total words, scenes, canon progress across all books
- **Memory Status**: Whether summaries are current or need refresh
- **Books Grid**: Each book with word count and canon percentage
- **Quick Actions**: Chat with Chico, add books, refresh memory

### Continuity Checking

Before marking a scene as canon, you can check it for contradictions:

1. Open a scene with prose in a series project
2. Click **Check Continuity** in the workspace header
3. The system compares your prose against established facts
4. Review any issues found (high/medium/low severity)
5. Fix contradictions before finalizing

## File Locations

```
prose-pipeline/
├── data/                    # Default data storage
│   └── projects/            # Your projects
│       └── {project-id}/
│           ├── characters/  # Character markdown files
│           ├── world/       # World context files
│           ├── scenes/      # Scene JSON files
│           ├── references/  # Reference documents
│           └── summary.md   # Book summary (for series continuity)
├── backend/                 # FastAPI application
└── frontend/                # Web interface
```

## Accessing from Other Devices

The server binds to `0.0.0.0` by default, so it's accessible on your local network.

```bash
# Find your server IP
hostname -I

# Access from another device
http://YOUR_SERVER_IP:8000
```

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Troubleshooting

### Port Already in Use

Edit `.env` and change `PORT=8000` to another port, then restart.

### API Key Errors

- Verify keys are correct in Settings
- Check you have credits/balance remaining
- Anthropic keys start with `sk-ant-`

### Virtual Environment Issues

```bash
rm -rf backend/venv
./run_server.sh
```

## Next Steps

- Read `README.md` for full feature documentation
- Check `TODO.md` for development roadmap
- See `CONTINUITY.md` for how scene summaries work
