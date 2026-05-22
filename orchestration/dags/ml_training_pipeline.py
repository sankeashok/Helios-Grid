"""
Helios-Grid ML Training Pipeline DAG
Orchestrates the complete ML lifecycle: data ingestion → feature engineering →
model training → evaluation → deployment with scheduling, queuing, and cost monitoring.
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
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=4),
}

dag = DAG(
    "helios_grid_training_pipeline",
    default_args=default_args,
    description="End-to-end ML training pipeline with hyperparameter sweeps",
    schedule_interval="0 2 * * 1",  # Weekly Monday 2AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "training", "energy-prediction"],
)


def validate_data(**context):
    """Validate incoming data quality before training."""
    import pandas as pd

    from src.data.energy_ingestion import EnergyDataIngestion

    ingestion = EnergyDataIngestion()
    df = ingestion.load_latest_data()

    checks = {
        "row_count": len(df) > 1000,
        "null_ratio": df.isnull().mean().max() < 0.3,
        "schema_valid": all(
            col in df.columns for col in ["datetime", "energy_consumption"]
        ),
    }

    if not all(checks.values()):
        raise ValueError(f"Data validation failed: {checks}")

    context["ti"].xcom_push(key="data_path", value="data/validated/latest.csv")
    context["ti"].xcom_push(key="sample_count", value=len(df))


def run_feature_engineering(**context):
    """Execute feature engineering pipeline."""
    import pandas as pd

    from src.features.energy_feature_engineering import (
        EnergyFeatureConfig,
        EnergyFeaturePipeline,
    )

    config = EnergyFeatureConfig(
        create_cyclical_features=True,
        create_lag_features=True,
        feature_selection_method="mutual_info",
        max_features=50,
        scaling_method="robust",
    )

    pipeline = EnergyFeaturePipeline(config)
    train_df = pd.read_csv(context["ti"].xcom_pull(key="data_path"))
    X_train, X_test, y_train = pipeline.process_features(train_df)

    X_train.to_csv("data/processed/X_train_energy.csv", index=False)
    y_train.to_csv("data/processed/y_train_energy.csv", index=False)
    pipeline.save_pipeline("models/energy_feature_pipeline.pkl")

    context["ti"].xcom_push(key="feature_count", value=X_train.shape[1])


def run_hyperparameter_sweep(**context):
    """Run Optuna hyperparameter optimization across model types."""
    import json

    import pandas as pd

    from src.training.energy_model_training import EnergyModelConfig, EnergyModelTrainer

    model_configs = [
        EnergyModelConfig(model_type="xgboost", n_trials=50, use_time_series_cv=True),
        EnergyModelConfig(model_type="lightgbm", n_trials=50, use_time_series_cv=True),
        EnergyModelConfig(
            model_type="random_forest", n_trials=30, use_time_series_cv=True
        ),
    ]

    X_train = pd.read_csv("data/processed/X_train_energy.csv")
    y_train = pd.read_csv("data/processed/y_train_energy.csv").iloc[:, 0]

    split_idx = int(0.8 * len(X_train))
    X_tr, X_val = X_train[:split_idx], X_train[split_idx:]
    y_tr, y_val = y_train[:split_idx], y_train[split_idx:]

    best_result = None
    best_rmse = float("inf")

    for config in model_configs:
        trainer = EnergyModelTrainer(config)
        result = trainer.train_energy_model(X_tr, y_tr, X_val, y_val)

        if result["cv_rmse"] < best_rmse:
            best_rmse = result["cv_rmse"]
            best_result = {
                "model_type": config.model_type,
                "cv_rmse": result["cv_rmse"],
                "params": result["best_params"],
            }

    context["ti"].xcom_push(key="best_model", value=json.dumps(best_result))
    context["ti"].xcom_push(key="best_rmse", value=best_rmse)


def evaluate_model_gate(**context):
    """Decide whether model is good enough for deployment."""
    best_rmse = context["ti"].xcom_pull(key="best_rmse")
    threshold = 0.15

    if best_rmse <= threshold:
        return "register_model"
    else:
        return "notify_model_rejected"


def register_model(**context):
    """Register approved model in MLflow Model Registry."""
    import json

    import mlflow

    best_model = json.loads(context["ti"].xcom_pull(key="best_model"))

    mlflow.set_tracking_uri("mlruns")
    client = mlflow.tracking.MlflowClient()

    client.transition_model_version_stage(
        name="helios_grid_energy_model",
        version=client.get_latest_versions("helios_grid_energy_model")[0].version,
        stage="Staging",
    )

    context["ti"].xcom_push(key="model_registered", value=True)


def track_training_cost(**context):
    """Track compute cost for the training run."""
    start_time = context["dag_run"].start_date
    duration_hours = (datetime.utcnow() - start_time).total_seconds() / 3600

    cost_per_hour = float(context["params"].get("cost_per_hour", 2.50))
    estimated_cost = duration_hours * cost_per_hour

    context["ti"].xcom_push(
        key="training_duration_hours", value=round(duration_hours, 2)
    )
    context["ti"].xcom_push(key="estimated_cost_usd", value=round(estimated_cost, 2))


# Task definitions
validate = PythonOperator(
    task_id="validate_data", python_callable=validate_data, dag=dag
)

feature_eng = PythonOperator(
    task_id="feature_engineering", python_callable=run_feature_engineering, dag=dag
)

hp_sweep = PythonOperator(
    task_id="hyperparameter_sweep",
    python_callable=run_hyperparameter_sweep,
    dag=dag,
    pool="gpu_pool",
    priority_weight=10,
)

model_gate = BranchPythonOperator(
    task_id="model_quality_gate", python_callable=evaluate_model_gate, dag=dag
)

register = PythonOperator(
    task_id="register_model", python_callable=register_model, dag=dag
)

notify_rejected = PythonOperator(
    task_id="notify_model_rejected",
    python_callable=lambda **ctx: print(
        f"Model rejected: RMSE {ctx['ti'].xcom_pull(key='best_rmse')} > threshold"
    ),
    dag=dag,
)

cost_tracking = PythonOperator(
    task_id="track_training_cost",
    python_callable=track_training_cost,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

trigger_deploy = TriggerDagRunOperator(
    task_id="trigger_deployment",
    trigger_dag_id="helios_grid_deployment_pipeline",
    dag=dag,
)

# Pipeline flow
validate >> feature_eng >> hp_sweep >> model_gate
model_gate >> [register, notify_rejected]
register >> trigger_deploy
[register, notify_rejected] >> cost_tracking
