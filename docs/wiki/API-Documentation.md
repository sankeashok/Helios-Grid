# 📚 API Documentation

## 🎯 Overview
Helios-Grid provides a comprehensive REST API for energy consumption predictions.

## 🔗 Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🚀 Key Endpoints

### Health Check
```
GET /health
```

### Energy Prediction
```
POST /predict
{
  "features": {
    "hour": 18,
    "temperature": 30,
    "day_of_week": 5
  }
}
```

### Batch Predictions
```
POST /batch_predict
```

## 📊 Response Format
```json
{
  "prediction": 156.7,
  "confidence": 0.92,
  "processing_time_ms": 2.1
}
```

---
**Last Updated**: January 2025
