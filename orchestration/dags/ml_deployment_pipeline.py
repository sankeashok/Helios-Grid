"""
Helios-Grid Model Deployment Pipeline DAG
Handles model promotion: Staging → Canary → Production with rollback capability.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "mlops-team",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

dag = DAG(
    "helios_grid_deployment_pipeline",
    default_args=default_args,
    description="Model deployment with canary rollout and A/B testing",
    schedule_interval=None,  # Triggered by training pipeline
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["mlops", "deployment", "canary"],
)


def load_staging_model(**context):
    """Load the latest staging model for deployment validation."""
    import mlflow

    client = mlflow.tracking.MlflowClient()
    staging_versions = client.get_latest_versions(
        "helios_grid_energy_model", stages=["Staging"]
    )

    if not staging_versions:
        raise ValueError("No staging model found")

    model_version = staging_versions[0]
    context["ti"].xcom_push(key="model_version", value=model_version.version)
    context["ti"].xcom_push(key="model_uri", value=model_version.source)


def run_shadow_testing(**context):
    """Run shadow testing against production traffic."""
    import numpy as np
    import pandas as pd

    from src.monitoring.drift_detection import ModelPerformanceMonitor

    model_uri = context["ti"].xcom_pull(key="model_uri")

    # Load shadow test data (recent production traffic)
    shadow_data = pd.read_csv("data/serving_logs.csv")
    X_shadow = shadow_data.drop(columns=["actual_consumption"], errors="ignore")
    y_actual = shadow_data.get("actual_consumption")

    import mlflow

    model = mlflow.pyfunc.load_model(model_uri)
    predictions = model.predict(X_shadow)

    if y_actual is not None:
        from sklearn.metrics import mean_squared_error

        rmse = np.sqrt(mean_squared_error(y_actual, predictions))
        context["ti"].xcom_push(key="shadow_rmse", value=rmse)
        return rmse < 0.2  # Shadow test threshold

    return True


def decide_deployment_strategy(**context):
    """Choose deployment strategy based on model risk assessment."""
    shadow_rmse = context["ti"].xcom_pull(key="shadow_rmse")

    if shadow_rmse is None or shadow_rmse < 0.10:
        return "deploy_full_rollout"
    elif shadow_rmse < 0.15:
        return "deploy_canary"
    else:
        return "rollback_model"


def deploy_canary(**context):
    """Deploy model to canary (10% traffic)."""
    model_version = context["ti"].xcom_pull(key="model_version")

    # Update K8s canary deployment
    import subprocess

    subprocess.run(
        [
            "kubectl",
            "set",
            "image",
            "deployment/helios-grid-canary",
            f"helios-grid=sankeashok/helios-grid:v{model_version}",
        ],
        check=True,
    )

    context["ti"].xcom_push(key="deployment_type", value="canary")


def deploy_full_rollout(**context):
    """Deploy model to 100% production traffic."""
    import mlflow

    model_version = context["ti"].xcom_pull(key="model_version")

    client = mlflow.tracking.MlflowClient()
    client.transition_model_version_stage(
        name="helios_grid_energy_model",
        version=model_version,
        stage="Production",
    )

    context["ti"].xcom_push(key="deployment_type", value="full_rollout")


def rollback_model(**context):
    """Rollback to previous production model."""
    import mlflow

    client = mlflow.tracking.MlflowClient()
    prod_versions = client.get_latest_versions(
        "helios_grid_energy_model", stages=["Production"]
    )

    if prod_versions:
        context["ti"].xcom_push(
            key="rollback_version", value=prod_versions[0].version
        )


def post_deployment_validation(**context):
    """Validate deployment health after rollout."""
    import requests

    endpoints = [
        "https://helios-grid.up.railway.app/health",
        "https://helios-grid.up.railway.app/api/v1/model/info",
    ]

    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, timeout=10)
            if resp.status_code != 200:
                raise ValueError(f"Health check failed: {endpoint}")
        except Exception as e:
            raise ValueError(f"Post-deployment validation failed: {e}")

    context["ti"].xcom_push(key="deployment_healthy", value=True)


# Task definitions
load_model = PythonOperator(
    task_id="load_staging_model", python_callable=load_staging_model, dag=dag
)

shadow_test = PythonOperator(
    task_id="shadow_testing", python_callable=run_shadow_testing, dag=dag
)

strategy_gate = BranchPythonOperator(
    task_id="deployment_strategy_gate",
    python_callable=decide_deployment_strategy,
    dag=dag,
)

canary = PythonOperator(
    task_id="deploy_canary", python_callable=deploy_canary, dag=dag
)

full_rollout = PythonOperator(
    task_id="deploy_full_rollout", python_callable=deploy_full_rollout, dag=dag
)

rollback = PythonOperator(
    task_id="rollback_model", python_callable=rollback_model, dag=dag
)

validate_deploy = PythonOperator(
    task_id="post_deployment_validation",
    python_callable=post_deployment_validation,
    trigger_rule=TriggerRule.ONE_SUCCESS,
    dag=dag,
)

# Pipeline flow
load_model >> shadow_test >> strategy_gate
strategy_gate >> [canary, full_rollout, rollback]
[canary, full_rollout] >> validate_deploy
