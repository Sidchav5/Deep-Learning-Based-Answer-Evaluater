#!/bin/bash
# Setup Script for Refactored Backend (Linux/Mac)
# Run this after setting up your .env file

echo "================================================"
echo "   AI Answer Evaluation System - Setup"
echo "================================================"
echo ""

# Check if virtual environment is active
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
else
    echo "⚠️  Virtual environment not active. Activating..."
    if [ -f "../.venv/bin/activate" ]; then
        source "../.venv/bin/activate"
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found at ../.venv/"
        echo "   Please create it first: python -m venv ../.venv"
        exit 1
    fi
fi

echo ""

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️  .env file not found. Creating from template..."
    cp ".env.example" ".env"
    echo "✅ Created .env file. Please edit it and add your LLAMA_API_BASE_URL"
    echo ""
    echo "   Example: https://overjealous-kimberley-nonoperative.ngrok-free.app"
    echo ""
    read -p "Press Enter after you've added your Llama API URL to .env"
fi

echo ""
echo "📦 Installing/Updating dependencies..."
pip install -r requirements.txt --upgrade

echo ""
echo "🔍 Checking installation..."

# Check critical packages
packages=("flask" "faiss-cpu" "sentence-transformers" "tensorflow")
all_installed=true

for pkg in "${packages[@]}"; do
    if pip show "$pkg" > /dev/null 2>&1; then
        echo "   ✅ $pkg"
    else
        echo "   ❌ $pkg - NOT INSTALLED"
        all_installed=false
    fi
done

echo ""

if [ "$all_installed" = true ]; then
    echo "✅ All dependencies installed successfully!"
else
    echo "⚠️  Some dependencies are missing. Please check the errors above."
    exit 1
fi

echo ""
echo "================================================"
echo "   Setup Complete!"
echo "================================================"
echo ""
echo "To start the server, run:"
echo "   python main.py"
echo ""
echo "Or use the old version:"
echo "   python app.py"
echo ""
echo "📚 Check README_NEW.md for API documentation"
echo ""
