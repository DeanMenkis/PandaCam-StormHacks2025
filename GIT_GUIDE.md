# Git Guide - Circuit Breakers StormHacks 2025

## 📁 What's Included in Git

### ✅ **Files that SHOULD be committed:**
- **Source code**: `*.py` files (watchdog_app.py, watchdog_app_modern.py, etc.)
- **Configuration**: `ai_config.json`, `requirements.txt`
- **Documentation**: `README.md`, `*.md` files
- **Scripts**: `*.sh` files (launch_modern.sh, setup_camera.sh, etc.)
- **Desktop files**: `*.desktop` files
- **Project structure**: Main directories and important config files

### ❌ **Files that are IGNORED:**
- **Virtual environment**: `venv/` directory (too large, machine-specific)
- **Python cache**: `__pycache__/` directories
- **Images**: `*.jpg`, `*.png` (camera captures, debug images)
- **Log files**: `*.log`, `watchdog_log.txt`
- **Temporary files**: `*.tmp`, `*.swp`, backup files
- **System files**: `.DS_Store`, `Thumbs.db`, etc.
- **IDE files**: `.vscode/`, `.idea/`, etc.

## 🚀 **Quick Git Commands**

### Initial Setup (if not done):
```bash
git init
git add .
git commit -m "Initial commit: 3D Printer Watchdog StormHacks 2025"
```

### Regular Workflow:
```bash
# Check status
git status

# Add specific files
git add rpi_firmware/watchdog_app_modern.py
git add rpi_firmware/ai_config.json

# Or add all tracked changes
git add .

# Commit changes
git commit -m "Improve camera feed sizing and UI layout"

# Push to GitHub
git push origin main
```

### Before Committing:
```bash
# Always check what you're about to commit
git status
git diff --cached

# Make sure no sensitive data (API keys, logs, images)
git log --oneline -5
```

## 🔒 **Security Notes**

- ✅ **API keys are in environment variables** (not hardcoded)
- ✅ **No personal images or logs** will be committed
- ✅ **Virtual environment excluded** (keeps repo size small)
- ✅ **Debug files ignored** (no test images or logs)

## 📊 **Repository Size**

With this `.gitignore`, your repository will be:
- **Small and clean** (~50-100 MB max)
- **Fast to clone** (no large binary files)
- **Professional** (only source code and docs)
- **Secure** (no sensitive data)

## 🎯 **Ready for GitHub!**

Your project is now properly configured for GitHub with:
- ✅ Comprehensive `.gitignore`
- ✅ Clean file structure
- ✅ Professional documentation
- ✅ No sensitive data exposure
