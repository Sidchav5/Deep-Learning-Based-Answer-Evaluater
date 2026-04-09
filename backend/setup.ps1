# Setup Script for Refactored Backend
# Run this after setting up your .env file

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   AI Answer Evaluation System - Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is active
if ($env:VIRTUAL_ENV) {
    Write-Host "✅ Virtual environment is active: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "⚠️  Virtual environment not active. Activating..." -ForegroundColor Yellow
    if (Test-Path "..\.venv\Scripts\Activate.ps1") {
        & "..\.venv\Scripts\Activate.ps1"
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "❌ Virtual environment not found at ..\.venv\" -ForegroundColor Red
        Write-Host "   Please create it first: python -m venv ../.venv" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""

# Check if .env exists
if (Test-Path ".env") {
    Write-Host "✅ .env file found" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file. Please edit it and add your LLAMA_API_BASE_URL" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Example: https://overjealous-kimberley-nonoperative.ngrok-free.app" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter after you've added your Llama API URL to .env"
}

Write-Host ""
Write-Host "📦 Installing/Updating dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt --upgrade

Write-Host ""
Write-Host "🔍 Checking installation..." -ForegroundColor Cyan

# Check critical packages
$packages = @("flask", "faiss-cpu", "sentence-transformers", "tensorflow")
$allInstalled = $true

foreach ($pkg in $packages) {
    pip show $pkg 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $pkg - NOT INSTALLED" -ForegroundColor Red
        $allInstalled = $false
    }
}

Write-Host ""

if ($allInstalled) {
    Write-Host "✅ All dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some dependencies are missing. Please check the errors above." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the server, run:" -ForegroundColor Cyan
Write-Host "   python main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or use the old version:" -ForegroundColor Cyan
Write-Host "   python app.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "📚 Check README_NEW.md for API documentation" -ForegroundColor Cyan
Write-Host ""
