#!/bin/bash
# Cloud Deployment Script for Helios-Grid

echo "🚀 Helios-Grid Cloud Deployment Helper"
echo "======================================"

# Configuration
PROJECT_NAME="helios-grid"
VERSION="1.0.0"
REGISTRY_URL=""  # Set your registry URL

# Build production Docker image
echo "📦 Building production Docker image..."
docker build -f Dockerfile.production -t ${PROJECT_NAME}:${VERSION} .
docker tag ${PROJECT_NAME}:${VERSION} ${PROJECT_NAME}:latest

echo "✅ Docker image built successfully!"

echo ""
echo "🌐 Cloud Deployment Options:"
echo ""

echo "1️⃣  AZURE CONTAINER REGISTRY (ACR)"
echo "   # Login to Azure"
echo "   az login"
echo "   az acr login --name <your-registry-name>"
echo ""
echo "   # Tag and push"
echo "   docker tag ${PROJECT_NAME}:${VERSION} <your-registry>.azurecr.io/${PROJECT_NAME}:${VERSION}"
echo "   docker push <your-registry>.azurecr.io/${PROJECT_NAME}:${VERSION}"
echo ""
echo "   # Deploy to Azure Container Instances"
echo "   az container create \\"
echo "     --resource-group <your-rg> \\"
echo "     --name ${PROJECT_NAME} \\"
echo "     --image <your-registry>.azurecr.io/${PROJECT_NAME}:${VERSION} \\"
echo "     --ports 8000 \\"
echo "     --dns-name-label ${PROJECT_NAME}-demo"
echo ""

echo "2️⃣  AWS ELASTIC CONTAINER REGISTRY (ECR)"
echo "   # Login to AWS ECR"
echo "   aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com"
echo ""
echo "   # Create repository (if not exists)"
echo "   aws ecr create-repository --repository-name ${PROJECT_NAME}"
echo ""
echo "   # Tag and push"
echo "   docker tag ${PROJECT_NAME}:${VERSION} <account-id>.dkr.ecr.<region>.amazonaws.com/${PROJECT_NAME}:${VERSION}"
echo "   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/${PROJECT_NAME}:${VERSION}"
echo ""
echo "   # Deploy to ECS or EKS"
echo "   # (Use ECS task definition or Kubernetes manifests)"
echo ""

echo "3️⃣  GOOGLE CONTAINER REGISTRY (GCR)"
echo "   # Configure Docker for GCR"
echo "   gcloud auth configure-docker"
echo ""
echo "   # Tag and push"
echo "   docker tag ${PROJECT_NAME}:${VERSION} gcr.io/<project-id>/${PROJECT_NAME}:${VERSION}"
echo "   docker push gcr.io/<project-id>/${PROJECT_NAME}:${VERSION}"
echo ""
echo "   # Deploy to Cloud Run"
echo "   gcloud run deploy ${PROJECT_NAME} \\"
echo "     --image gcr.io/<project-id>/${PROJECT_NAME}:${VERSION} \\"
echo "     --platform managed \\"
echo "     --region <region> \\"
echo "     --allow-unauthenticated"
echo ""

echo "4️⃣  DOCKER HUB (Public Registry)"
echo "   # Login to Docker Hub"
echo "   docker login"
echo ""
echo "   # Tag and push"
echo "   docker tag ${PROJECT_NAME}:${VERSION} <your-username>/${PROJECT_NAME}:${VERSION}"
echo "   docker push <your-username>/${PROJECT_NAME}:${VERSION}"
echo ""

echo "5️⃣  KUBERNETES DEPLOYMENT"
echo "   # Apply Kubernetes manifests"
echo "   kubectl apply -f k8s/"
echo ""

echo "📊 Image Information:"
docker images | grep ${PROJECT_NAME}

echo ""
echo "🎯 Next Steps:"
echo "1. Choose your cloud provider"
echo "2. Set up container registry"
echo "3. Run the appropriate commands above"
echo "4. Access your deployed application!"
echo ""
echo "💡 Tip: For production, consider using:"
echo "   - Load balancers"
echo "   - Auto-scaling"
echo "   - Monitoring (Prometheus/Grafana)"
echo "   - Secrets management"
echo "   - CI/CD pipelines"