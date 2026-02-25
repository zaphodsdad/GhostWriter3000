#!/bin/bash

# GhostWriter 3000 — Development Server Startup Script

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   G H O S T W R I T E R   3 0 0 0        ║"
echo "  ║   AI-Powered Prose Generation Engine      ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "Error: Please run this script from the GhostWriter 3000 project directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env and add your OPENROUTER_API_KEY"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "Python version: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv backend/venv
    echo "Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source backend/venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r backend/requirements.txt

echo ""
echo "  ┌───────────────────────────────────────────┐"
echo "  │  Starting server on port 8000             │"
echo "  │  http://localhost:8000                    │"
echo "  │  Press Ctrl+C to stop                     │"
echo "  └───────────────────────────────────────────┘"
echo ""

# Start the server
cd backend && python -m app.main
