"""
Helios-Grid Model Monitoring DAG
Continuous monitoring: drift detection, performance tracking, alerting, and auto-retraining triggers.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "mlops-team",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

dag = DAG(
    "helios_grid_monitoring",
    default_args=default_args,
    description="Continuous model monitoring with drift detection and auto-retraining",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["mlops", "monitoring", "drift-detection"],
)


def collect_serving_metrics(**context):
    """Collect prediction serving metrics from production."""
    import pandas as pd

    # Load recent serving logs
    serving_logs = pd.read_csv("data/serving_logs.csv")
    recent = serving_logs.tail(1000)

    metrics = {
        "total_predictions": len(recent),
        "avg_latency_ms": recent.get("latency_ms", pd.Series([0])).mean(),
        "error_rate": recent.get("error", pd.Series([0])).mean(),
        "avg_prediction": recent.get("prediction", pd.Series([0])).mean(),
    }

    context["ti"].xcom_push(key="serving_metrics", value=metrics)


def run_drift_detection(**context):
    """Run statistical drift detection on incoming data."""
    import json

    import pandas as pd

    from src.monitoring.drift_detection import DriftDetector

    reference_data = pd.read_csv("data/features.csv")
    current_data = pd.read_csv("data/serving_logs.csv").tail(500)

    # Align columns
    common_cols = list(set(reference_data.columns) & set(current_data.columns))
    if not common_cols:
        context["ti"].xcom_push(key="drift_detected", value=False)
        return

    detector = DriftDetector(reference_data[common_cols], threshold=0.1)
    results = detector.detect_drift(current_data[common_cols])

    context["ti"].xcom_push(key="drift_detected", value=results["overall_drift"])
    context["ti"].xcom_push(key="drift_score", value=results["drift_score"])
    context["ti"].xcom_push(key="drift_details", value=json.dumps(results))


def check_performance_degradation(**context):
    """Check if model performance has degraded below threshold."""
    import numpy as np
    import pandas as pd
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    serving_logs = pd.read_csv("data/serving_logs.csv")

    if "actual_consumption" not in serving_logs.columns:
        context["ti"].xcom_push(key="performance_degraded", value=False)
        return

    recent = serving_logs.dropna(subset=["actual_consumption", "prediction"]).tail(200)
    if len(recent) < 50:
        context["ti"].xcom_push(key="performance_degraded", value=False)
        return

    rmse = np.sqrt(
        mean_squared_error(recent["actual_consumption"], recent["prediction"])
    )
    mae = mean_absolute_error(recent["actual_consumption"], recent["prediction"])

    # Thresholds from model training baseline
    rmse_threshold = 0.20
    mae_threshold = 0.15

    degraded = rmse > rmse_threshold or mae > mae_threshold

    context["ti"].xcom_push(key="performance_degraded", value=degraded)
    context["ti"].xcom_push(key="current_rmse", value=round(rmse, 4))
    context["ti"].xcom_push(key="current_mae", value=round(mae, 4))


def decide_action(**context):
    """Decide whether to retrain, alert, or do nothing."""
    drift_detected = context["ti"].xcom_pull(key="drift_detected")
    performance_degraded = context["ti"].xcom_pull(key="performance_degraded")

    if performance_degraded and drift_detected:
        return "trigger_retraining"
    elif drift_detected or performance_degraded:
        return "send_alert"
    else:
        return "log_healthy_status"


def send_alert(**context):
    """Send alert to MLOps team."""
    drift_score = context["ti"].xcom_pull(key="drift_score")
    current_rmse = context["ti"].xcom_pull(key="current_rmse")

    alert_payload = {
        "severity": "warning",
        "model": "helios_grid_energy_model",
        "drift_score": drift_score,
        "current_rmse": current_rmse,
        "timestamp": datetime.utcnow().isoformat(),
        "action_required": "Review model performance",
    }

    # Push to monitoring system (Prometheus/Grafana via pushgateway)
    try:
        import requests

        requests.post(
            "http://localhost:9091/metrics/job/helios_grid_monitoring",
            data=f"model_drift_score {drift_score}\nmodel_rmse {current_rmse or 0}\n",
        )
    except Exception:
        pass

    context["ti"].xcom_push(key="alert_sent", value=True)


def log_healthy_status(**context):
    """Log that model is healthy."""
    import mlflow

    with mlflow.start_run(run_name="monitoring_healthy"):
        mlflow.log_metric("model_healthy", 1)
        mlflow.log_metric(
            "drift_score", context["ti"].xcom_pull(key="drift_score") or 0
        )


# Task definitions
collect_metrics = PythonOperator(
    task_id="collect_serving_metrics", python_callable=collect_serving_metrics, dag=dag
)

drift_check = PythonOperator(
    task_id="drift_detection", python_callable=run_drift_detection, dag=dag
)

perf_check = PythonOperator(
    task_id="performance_check",
    python_callable=check_performance_degradation,
    dag=dag,
)

action_gate = BranchPythonOperator(
    task_id="decide_action", python_callable=decide_action, dag=dag
)

alert = PythonOperator(task_id="send_alert", python_callable=send_alert, dag=dag)

healthy = PythonOperator(
    task_id="log_healthy_status", python_callable=log_healthy_status, dag=dag
)

retrain = TriggerDagRunOperator(
    task_id="trigger_retraining",
    trigger_dag_id="helios_grid_training_pipeline",
    dag=dag,
)

# Pipeline flow
collect_metrics >> [drift_check, perf_check] >> action_gate
action_gate >> [retrain, alert, healthy]
