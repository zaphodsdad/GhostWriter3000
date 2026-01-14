#!/bin/bash

# Prose Pipeline - Development Server Startup Script

echo "========================================="
echo "  Prose Generation Pipeline"
echo "  Starting Development Server"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "Error: Please run this script from the prose-pipeline directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env and add your ANTHROPIC_API_KEY"
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
echo "========================================="
echo "  Starting FastAPI server on port 8000"
echo "========================================="
echo ""
echo "Open your browser to: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
cd backend && python -m app.main
