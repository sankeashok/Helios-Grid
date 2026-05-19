@echo off
REM Helios-Grid Git Setup and Push Script for Windows
REM This script initializes the git repository and pushes to GitHub

echo 🌟 Setting up Helios-Grid Git Repository
echo ========================================

REM Navigate to project directory
cd /d "C:\Users\sanke\Documents\MLops\Azure-MLOps-Pipeline"

REM Check if git is initialized
if not exist ".git" (
    echo 📁 Initializing Git repository...
    git init
) else (
    echo 📁 Git repository already initialized
)

REM Configure git user
echo 👤 Configuring Git user...
git config user.name "Ashok Sanke"
git config user.email "sankeashok@gmail.com"

REM Add remote origin
echo 🔗 Adding remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/sankeashok/Helios-Grid.git

REM Create main branch
echo 🌿 Setting up main branch...
git branch -M main

REM Add all files
echo 📦 Adding files to staging...
git add .

REM Create initial commit
echo 💾 Creating initial commit...
git commit -m "🚀 Initial commit: Helios-Grid Enterprise Energy MLOps Pipeline

✨ Features:
- Complete MLOps pipeline for energy consumption prediction
- Azure-native architecture with enterprise security
- Premium glassmorphism UI with WCAG accessibility
- Comprehensive CI/CD with blue-green deployments
- Real-time monitoring and drift detection
- Chaos engineering and edge case handling
- Staff-level engineering implementation

🔧 Tech Stack:
- Azure ML, Blob Storage, Key Vault, DevOps
- FastAPI, MLflow, XGBoost, LightGBM
- Prometheus, Grafana, Docker
- pytest, SAST/DAST security scanning

🎯 Ready for enterprise production deployment!"

REM Push to GitHub
echo 🚀 Pushing to GitHub...
git push -u origin main

echo.
echo ✅ Helios-Grid successfully pushed to GitHub!
echo 🌐 Repository: https://github.com/sankeashok/Helios-Grid
echo.
echo 🎉 Next steps:
echo    1. Visit the repository on GitHub
echo    2. Set up branch protection rules
echo    3. Configure GitHub Actions (optional)
echo    4. Add collaborators if needed
echo.
echo ☀️ Helios-Grid is ready to power the future of energy analytics!

pause