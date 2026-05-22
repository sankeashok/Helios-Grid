"""
Prometheus Metrics Exporter for Helios-Grid ML Model Serving
Exposes model performance, latency, drift, and cost metrics for Grafana dashboards.
"""

import time
from functools import wraps
from typing import Callable

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
    start_http_server,
)

# Request metrics
PREDICTION_REQUESTS = Counter(
    "prediction_requests_total",
    "Total prediction requests",
    ["model_version", "status"],
)

PREDICTION_ERRORS = Counter(
    "prediction_errors_total",
    "Total prediction errors",
    ["error_type"],
)

PREDICTION_LATENCY = Histogram(
    "prediction_latency_seconds",
    "Prediction request latency",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# Model performance metrics
MODEL_RMSE = Gauge("model_rmse", "Current model RMSE on recent predictions")
MODEL_MAE = Gauge("model_mae", "Current model MAE on recent predictions")
MODEL_DRIFT_SCORE = Gauge("model_drift_score", "Current data drift score")
FEATURE_DRIFT = Gauge(
    "feature_drift_score", "Per-feature drift score", ["feature"]
)

# Model version info
MODEL_VERSION_INFO = Info("model_version_info", "Current model version details")

# Training cost metrics
TRAINING_JOB_COST = Gauge(
    "training_job_cost_usd", "Cost of last training job in USD"
)
TRAINING_BUDGET_REMAINING = Gauge(
    "training_budget_remaining_usd", "Remaining training budget"
)

# GPU metrics
GPU_UTILIZATION = Gauge(
    "gpu_utilization_percent", "GPU utilization percentage", ["gpu_id"]
)
GPU_MEMORY_USED = Gauge(
    "gpu_memory_used_bytes", "GPU memory used", ["gpu_id"]
)
GPU_MEMORY_TOTAL = Gauge(
    "gpu_memory_total_bytes", "GPU memory total", ["gpu_id"]
)

# Deployment events
MODEL_DEPLOYMENT_EVENT = Counter(
    "model_deployment_event", "Model deployment events", ["version", "stage"]
)


def track_prediction(model_version: str = "latest"):
    """Decorator to track prediction metrics."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                PREDICTION_REQUESTS.labels(
                    model_version=model_version, status="success"
                ).inc()
                return result
            except Exception as e:
                PREDICTION_REQUESTS.labels(
                    model_version=model_version, status="error"
                ).inc()
                PREDICTION_ERRORS.labels(error_type=type(e).__name__).inc()
                raise
            finally:
                PREDICTION_LATENCY.observe(time.time() - start_time)

        return wrapper

    return decorator


def update_model_metrics(rmse: float, mae: float, drift_score: float):
    """Update model performance gauges."""
    MODEL_RMSE.set(rmse)
    MODEL_MAE.set(mae)
    MODEL_DRIFT_SCORE.set(drift_score)


def update_feature_drift(drift_scores: dict):
    """Update per-feature drift scores."""
    for feature, score in drift_scores.items():
        FEATURE_DRIFT.labels(feature=feature).set(score)


def update_model_version(name: str, version: str, stage: str):
    """Update model version info."""
    MODEL_VERSION_INFO.info(
        {"model_name": name, "version": version, "stage": stage}
    )


def record_deployment(version: str, stage: str):
    """Record a model deployment event."""
    MODEL_DEPLOYMENT_EVENT.labels(version=version, stage=stage).inc()


def update_training_cost(job_cost: float, budget_remaining: float):
    """Update training cost metrics."""
    TRAINING_JOB_COST.set(job_cost)
    TRAINING_BUDGET_REMAINING.set(budget_remaining)


def start_metrics_server(port: int = 9091):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
