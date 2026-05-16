@echo off
echo 🚀 Helios-Grid Cloud Deployment Helper
echo ======================================

set PROJECT_NAME=helios-grid
set VERSION=1.0.0

echo 📦 Building production Docker image...
docker build -f Dockerfile.production -t %PROJECT_NAME%:%VERSION% .
docker tag %PROJECT_NAME%:%VERSION% %PROJECT_NAME%:latest

echo ✅ Docker image built successfully!
echo.

echo 🌐 Cloud Deployment Options:
echo.

echo 1️⃣  AZURE CONTAINER REGISTRY (ACR)
echo    # Login to Azure
echo    az login
echo    az acr login --name ^<your-registry-name^>
echo.
echo    # Tag and push
echo    docker tag %PROJECT_NAME%:%VERSION% ^<your-registry^>.azurecr.io/%PROJECT_NAME%:%VERSION%
echo    docker push ^<your-registry^>.azurecr.io/%PROJECT_NAME%:%VERSION%
echo.

echo 2️⃣  DOCKER HUB (Public Registry)
echo    # Login to Docker Hub
echo    docker login
echo.
echo    # Tag and push
echo    docker tag %PROJECT_NAME%:%VERSION% ^<your-username^>/%PROJECT_NAME%:%VERSION%
echo    docker push ^<your-username^>/%PROJECT_NAME%:%VERSION%
echo.

echo 3️⃣  AWS ECR
echo    # Login to AWS ECR
echo    aws ecr get-login-password --region ^<region^> ^| docker login --username AWS --password-stdin ^<account-id^>.dkr.ecr.^<region^>.amazonaws.com
echo.

echo 📊 Current Docker Images:
docker images | findstr %PROJECT_NAME%

echo.
echo 🎯 Next Steps:
echo 1. Choose your cloud provider
echo 2. Set up container registry  
echo 3. Run the appropriate commands above
echo 4. Deploy using Kubernetes manifests in k8s/ folder
echo.
pause