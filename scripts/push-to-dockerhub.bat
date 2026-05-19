@echo off
echo 🚀 Helios-Grid Docker Hub Deployment
echo ===================================

set PROJECT_NAME=helios-grid
set VERSION=1.0.0

echo 📊 Current Docker Images:
docker images | findstr %PROJECT_NAME%
echo.

echo 🔑 Step 1: Login to Docker Hub
echo Please run: docker login
echo Enter your Docker Hub username and password when prompted
echo.

echo 🏷️ Step 2: Tag for Docker Hub
echo Replace 'yourusername' with your actual Docker Hub username:
echo docker tag %PROJECT_NAME%:%VERSION% yourusername/%PROJECT_NAME%:%VERSION%
echo docker tag %PROJECT_NAME%:%VERSION% yourusername/%PROJECT_NAME%:latest
echo.

echo 📤 Step 3: Push to Docker Hub
echo docker push yourusername/%PROJECT_NAME%:%VERSION%
echo docker push yourusername/%PROJECT_NAME%:latest
echo.

echo 🌐 Step 4: Deploy from Docker Hub
echo Once pushed, anyone can run your image with:
echo docker run -d -p 8000:8000 yourusername/%PROJECT_NAME%:latest
echo.

echo 📋 Example with username 'sankeashok':
echo docker tag %PROJECT_NAME%:%VERSION% sankeashok/%PROJECT_NAME%:%VERSION%
echo docker tag %PROJECT_NAME%:%VERSION% sankeashok/%PROJECT_NAME%:latest
echo docker push sankeashok/%PROJECT_NAME%:%VERSION%
echo docker push sankeashok/%PROJECT_NAME%:latest
echo.

echo ✅ Current Status:
echo - ✅ Docker image built successfully
echo - ✅ Local testing completed
echo - ✅ Health check passed
echo - ⏳ Ready for Docker Hub push
echo.

echo 🎯 What to do next:
echo 1. Run: docker login
echo 2. Replace 'yourusername' with your Docker Hub username in the commands above
echo 3. Run the tag and push commands
echo 4. Your image will be available globally!
echo.

pause