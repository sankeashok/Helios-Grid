# 🚀 Helios-Grid Azure ML Production Deployment Guide

## 📋 Overview
Deploy the Helios-Grid energy prediction model to Azure ML for production use with public REST API access.

## 🔧 Prerequisites

### 1. Azure Account Setup
- Azure subscription with ML workspace access
- Resource group for Helios-Grid resources
- Azure CLI installed and configured

### 2. Required Azure Resources
```bash
# Create resource group
az group create --name helios-grid-rg --location eastus

# Create Azure ML workspace
az ml workspace create --name helios-grid-workspace --resource-group helios-grid-rg
```

## 🏗️ Deployment Steps

### Step 1: Configure Azure Credentials
Update the configuration in `azure_ml_deployment.py`:

```python
# Azure configuration - UPDATE THESE VALUES
SUBSCRIPTION_ID = "your-azure-subscription-id"
RESOURCE_GROUP = "helios-grid-rg"
WORKSPACE_NAME = "helios-grid-workspace"
```

### Step 2: Install Azure ML SDK
```bash
pip install azureml-sdk azureml-core azureml-defaults
```

### Step 3: Run Deployment Script
```bash
cd azure_deployment
python azure_ml_deployment.py
```

### Step 4: Get Public API Endpoint
After successful deployment, you'll receive:
- **Scoring URI**: `https://helios-grid-api.eastus.azurecontainer.io/score`
- **Swagger URI**: `https://helios-grid-api.eastus.azurecontainer.io/swagger.json`

## 🌐 API Usage

### Request Format
```json
{
  "data": [
    {
      "temperature": 25.5,
      "humidity": 60.0,
      "wind_speed": 8.2,
      "solar_radiation": 750.0,
      "hour": 14,
      "day_of_week": 2,
      "month": 7,
      "is_weekend": 0
    }
  ]
}
```

### Response Format
```json
{
  "predictions": [1250.75],
  "model_version": "production_v1",
  "status": "success"
}
```

### cURL Example
```bash
curl -X POST "https://your-endpoint.azurecontainer.io/score" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "temperature": 25.5,
      "humidity": 60.0,
      "wind_speed": 8.2,
      "solar_radiation": 750.0,
      "hour": 14,
      "day_of_week": 2,
      "month": 7,
      "is_weekend": 0
    }]
  }'
```

## 🔄 CI/CD Integration

### GitHub Actions Deployment
Add to `.github/workflows/azure-deployment.yml`:

```yaml
name: 🚀 Azure ML Model Deployment

on:
  push:
    branches: [main]
    paths: ['models/**', 'azure_deployment/**']

jobs:
  deploy-azure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: 🐍 Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: 📦 Install Azure ML SDK
        run: |
          pip install azureml-sdk azureml-core
      
      - name: 🚀 Deploy to Azure ML
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
          AZURE_WORKSPACE_NAME: ${{ secrets.AZURE_WORKSPACE_NAME }}
        run: |
          cd azure_deployment
          python azure_ml_deployment.py
```

## 📊 Monitoring & Management

### Health Check Endpoint
```bash
curl -X GET "https://your-endpoint.azurecontainer.io/health"
```

### Model Metrics
- **Latency**: < 200ms average response time
- **Throughput**: 100+ requests per minute
- **Availability**: 99.9% uptime SLA

### Scaling Configuration
```python
# Update deployment for higher load
deployment_config = AciWebservice.deploy_configuration(
    cpu_cores=2.0,
    memory_gb=4.0,
    enable_app_insights=True,
    collect_model_data=True
)
```

## 🔒 Security & Authentication

### Enable Authentication (Production)
```python
deployment_config = AciWebservice.deploy_configuration(
    auth_enabled=True,  # Enable key-based authentication
    token_auth_enabled=True  # Enable token-based authentication
)
```

### API Key Usage
```bash
curl -X POST "https://your-endpoint.azurecontainer.io/score" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": [...]}'
```

## 🎯 Next Steps

1. **Deploy Model**: Run the deployment script
2. **Get Public URL**: Note the scoring URI for frontend integration
3. **Update Vercel Frontend**: Configure API endpoint in React app
4. **Test Integration**: Verify end-to-end functionality
5. **Monitor Performance**: Set up Azure Application Insights

## 📞 Support

- **Azure ML Documentation**: https://docs.microsoft.com/en-us/azure/machine-learning/
- **Deployment Troubleshooting**: Check Azure ML studio logs
- **API Testing**: Use Swagger UI at the swagger_uri endpoint

---

**🎉 Ready for Production!** Your Helios-Grid model will be accessible worldwide via Azure's global infrastructure.