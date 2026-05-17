"""
Data Drift Monitoring System with Azure Integration
Monitors model performance and data drift in production
"""

import os
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
import evidently
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, RegressionPreset
from evidently.metrics import DatasetDriftMetric, ColumnDriftMetric
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import mlflow
import json
import warnings

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DriftDetector:
    """Advanced drift detection using statistical tests and ML-based methods"""

    def __init__(self, reference_data: pd.DataFrame, threshold: float = 0.1):
        self.reference_data = reference_data
        self.threshold = threshold
        self.feature_stats = self._calculate_reference_stats()

    def _calculate_reference_stats(self) -> Dict[str, Dict]:
        """Calculate reference statistics for each feature"""
        stats_dict = {}

        for column in self.reference_data.columns:
            if self.reference_data[column].dtype in ["int64", "float64"]:
                stats_dict[column] = {
                    "mean": self.reference_data[column].mean(),
                    "std": self.reference_data[column].std(),
                    "min": self.reference_data[column].min(),
                    "max": self.reference_data[column].max(),
                    "q25": self.reference_data[column].quantile(0.25),
                    "q75": self.reference_data[column].quantile(0.75),
                    "type": "numerical",
                }
            else:
                value_counts = self.reference_data[column].value_counts(normalize=True)
                stats_dict[column] = {
                    "distribution": value_counts.to_dict(),
                    "unique_values": set(self.reference_data[column].unique()),
                    "type": "categorical",
                }

        return stats_dict

    def detect_drift(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect drift using multiple statistical tests"""
        drift_results = {
            "overall_drift": False,
            "drift_score": 0.0,
            "feature_drift": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        drift_scores = []

        for column in self.reference_data.columns:
            if column not in current_data.columns:
                continue

            feature_result = self._test_feature_drift(
                column, self.reference_data[column], current_data[column]
            )

            drift_results["feature_drift"][column] = feature_result
            drift_scores.append(feature_result["drift_score"])

        # Overall drift score (average of feature drift scores)
        drift_results["drift_score"] = np.mean(drift_scores) if drift_scores else 0.0
        drift_results["overall_drift"] = drift_results["drift_score"] > self.threshold

        return drift_results

    def _test_feature_drift(
        self, column: str, reference: pd.Series, current: pd.Series
    ) -> Dict:
        """Test drift for a single feature using appropriate statistical test"""

        if self.feature_stats[column]["type"] == "numerical":
            return self._test_numerical_drift(column, reference, current)
        else:
            return self._test_categorical_drift(column, reference, current)

    def _test_numerical_drift(
        self, column: str, reference: pd.Series, current: pd.Series
    ) -> Dict:
        """Test drift for numerical features using KS test and statistical measures"""

        # Kolmogorov-Smirnov test
        ks_statistic, ks_p_value = stats.ks_2samp(reference, current)

        # Population Stability Index (PSI)
        psi_score = self._calculate_psi(reference, current)

        # Statistical measures comparison
        ref_stats = self.feature_stats[column]
        curr_mean = current.mean()
        curr_std = current.std()

        mean_shift = (
            abs(curr_mean - ref_stats["mean"]) / ref_stats["std"]
            if ref_stats["std"] > 0
            else 0
        )
        std_ratio = curr_std / ref_stats["std"] if ref_stats["std"] > 0 else 1

        # Combined drift score
        drift_score = max(ks_statistic, psi_score, min(mean_shift / 3, 1.0))

        return {
            "drift_detected": drift_score > self.threshold,
            "drift_score": drift_score,
            "ks_statistic": ks_statistic,
            "ks_p_value": ks_p_value,
            "psi_score": psi_score,
            "mean_shift": mean_shift,
            "std_ratio": std_ratio,
            "test_type": "numerical",
        }

    def _test_categorical_drift(
        self, column: str, reference: pd.Series, current: pd.Series
    ) -> Dict:
        """Test drift for categorical features using chi-square test"""

        ref_dist = reference.value_counts(normalize=True)
        curr_dist = current.value_counts(normalize=True)

        # Align distributions
        all_categories = set(ref_dist.index) | set(curr_dist.index)
        ref_aligned = pd.Series(
            [ref_dist.get(cat, 0) for cat in all_categories], index=all_categories
        )
        curr_aligned = pd.Series(
            [curr_dist.get(cat, 0) for cat in all_categories], index=all_categories
        )

        # Chi-square test
        try:
            chi2_stat, chi2_p_value = stats.chisquare(curr_aligned, ref_aligned)
        except:
            chi2_stat, chi2_p_value = 0, 1

        # PSI for categorical
        psi_score = self._calculate_categorical_psi(ref_aligned, curr_aligned)

        drift_score = max(psi_score, min(chi2_stat / 10, 1.0))

        return {
            "drift_detected": drift_score > self.threshold,
            "drift_score": drift_score,
            "chi2_statistic": chi2_stat,
            "chi2_p_value": chi2_p_value,
            "psi_score": psi_score,
            "test_type": "categorical",
        }

    def _calculate_psi(
        self, reference: pd.Series, current: pd.Series, bins: int = 10
    ) -> float:
        """Calculate Population Stability Index for numerical features"""

        # Create bins based on reference data
        _, bin_edges = np.histogram(reference, bins=bins)

        # Calculate distributions
        ref_hist, _ = np.histogram(reference, bins=bin_edges)
        curr_hist, _ = np.histogram(current, bins=bin_edges)

        # Normalize
        ref_dist = ref_hist / len(reference)
        curr_dist = curr_hist / len(current)

        # Avoid division by zero
        ref_dist = np.where(ref_dist == 0, 0.0001, ref_dist)
        curr_dist = np.where(curr_dist == 0, 0.0001, curr_dist)

        # Calculate PSI
        psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))

        return psi

    def _calculate_categorical_psi(
        self, reference: pd.Series, current: pd.Series
    ) -> float:
        """Calculate PSI for categorical features"""

        ref_dist = reference.values
        curr_dist = current.values

        # Avoid division by zero
        ref_dist = np.where(ref_dist == 0, 0.0001, ref_dist)
        curr_dist = np.where(curr_dist == 0, 0.0001, curr_dist)

        psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))

        return psi


class ModelPerformanceMonitor:
    """Monitor model performance degradation"""

    def __init__(self, model, reference_performance: Dict[str, float]):
        self.model = model
        self.reference_performance = reference_performance

    def evaluate_performance(
        self, X: pd.DataFrame, y_true: pd.Series
    ) -> Dict[str, Any]:
        """Evaluate current model performance"""

        try:
            y_pred = self.model.predict(X)

            current_metrics = {
                "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
                "mae": mean_absolute_error(y_true, y_pred),
                "mape": np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
            }

            # Calculate performance degradation
            degradation = {}
            for metric, current_value in current_metrics.items():
                if metric in self.reference_performance:
                    ref_value = self.reference_performance[metric]
                    if metric in ["rmse", "mae", "mape"]:  # Lower is better
                        degradation[f"{metric}_degradation"] = (
                            current_value - ref_value
                        ) / ref_value
                    else:  # Higher is better (e.g., r2_score)
                        degradation[f"{metric}_degradation"] = (
                            ref_value - current_value
                        ) / ref_value

            return {
                "current_metrics": current_metrics,
                "reference_metrics": self.reference_performance,
                "degradation": degradation,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Performance evaluation error: {e}")
            return {}


class AzureMonitoringPipeline:
    """Complete monitoring pipeline with Azure integration"""

    def __init__(self, storage_account: str, container_name: str):
        self.storage_account = storage_account
        self.container_name = container_name
        self.blob_client = self._setup_blob_client()

    def _setup_blob_client(self) -> BlobServiceClient:
        """Setup Azure Blob Storage client"""
        credential = DefaultAzureCredential()
        account_url = f"https://{self.storage_account}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=credential)

    def run_monitoring_pipeline(
        self,
        current_data: pd.DataFrame,
        reference_data: pd.DataFrame,
        model=None,
        y_true: pd.Series = None,
    ) -> Dict[str, Any]:
        """Run complete monitoring pipeline"""

        results = {
            "monitoring_timestamp": datetime.utcnow().isoformat(),
            "data_drift": {},
            "performance_monitoring": {},
            "alerts": [],
        }

        # Data drift detection
        logger.info("Running drift detection...")
        drift_detector = DriftDetector(reference_data, threshold=0.1)
        drift_results = drift_detector.detect_drift(current_data)
        results["data_drift"] = drift_results

        # Performance monitoring (if model and ground truth available)
        if model is not None and y_true is not None:
            logger.info("Running performance monitoring...")
            # Load reference performance (you'd store this during model training)
            reference_performance = {
                "rmse": 0.15,  # Example values
                "mae": 0.10,
                "mape": 8.5,
            }

            perf_monitor = ModelPerformanceMonitor(model, reference_performance)
            perf_results = perf_monitor.evaluate_performance(current_data, y_true)
            results["performance_monitoring"] = perf_results

        # Generate alerts
        results["alerts"] = self._generate_alerts(results)

        # Generate Evidently report
        evidently_report = self._generate_evidently_report(reference_data, current_data)

        # Store results in Azure
        self._store_monitoring_results(results, evidently_report)

        # Log to MLflow
        self._log_to_mlflow(results)

        return results

    def _generate_alerts(self, results: Dict) -> List[Dict]:
        """Generate alerts based on monitoring results"""
        alerts = []

        # Data drift alerts
        if results["data_drift"].get("overall_drift", False):
            alerts.append(
                {
                    "type": "data_drift",
                    "severity": (
                        "high"
                        if results["data_drift"]["drift_score"] > 0.3
                        else "medium"
                    ),
                    "message": f"Data drift detected with score {results['data_drift']['drift_score']:.3f}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        # Performance degradation alerts
        if "performance_monitoring" in results and results["performance_monitoring"]:
            degradation = results["performance_monitoring"].get("degradation", {})
            for metric, deg_value in degradation.items():
                if deg_value > 0.1:  # 10% degradation threshold
                    alerts.append(
                        {
                            "type": "performance_degradation",
                            "severity": "high" if deg_value > 0.2 else "medium",
                            "message": f"{metric} degraded by {deg_value:.1%}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        return alerts

    def _generate_evidently_report(
        self, reference_data: pd.DataFrame, current_data: pd.DataFrame
    ) -> str:
        """Generate Evidently HTML report"""

        try:
            report = Report(
                metrics=[
                    DataDriftPreset(),
                ]
            )

            report.run(reference_data=reference_data, current_data=current_data)
            return report.get_html()

        except Exception as e:
            logger.error(f"Failed to generate Evidently report: {e}")
            return ""

    def _store_monitoring_results(self, results: Dict, evidently_report: str):
        """Store monitoring results in Azure Blob Storage"""

        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

            # Store JSON results
            json_blob_name = f"monitoring/results_{timestamp}.json"
            json_data = json.dumps(results, indent=2)

            blob_client = self.blob_client.get_blob_client(
                container=self.container_name, blob=json_blob_name
            )
            blob_client.upload_blob(json_data, overwrite=True)

            # Store Evidently report
            if evidently_report:
                html_blob_name = f"monitoring/report_{timestamp}.html"
                blob_client = self.blob_client.get_blob_client(
                    container=self.container_name, blob=html_blob_name
                )
                blob_client.upload_blob(evidently_report, overwrite=True)

            logger.info(f"Monitoring results stored: {json_blob_name}")

        except Exception as e:
            logger.error(f"Failed to store monitoring results: {e}")

    def _log_to_mlflow(self, results: Dict):
        """Log monitoring results to MLflow"""

        try:
            with mlflow.start_run(run_name="monitoring_run"):
                # Log drift metrics
                drift_data = results.get("data_drift", {})
                mlflow.log_metric(
                    "overall_drift_score", drift_data.get("drift_score", 0)
                )
                mlflow.log_metric(
                    "drift_detected", int(drift_data.get("overall_drift", False))
                )

                # Log performance metrics
                perf_data = results.get("performance_monitoring", {})
                if perf_data:
                    current_metrics = perf_data.get("current_metrics", {})
                    for metric, value in current_metrics.items():
                        mlflow.log_metric(f"current_{metric}", value)

                # Log alert count
                mlflow.log_metric("alert_count", len(results.get("alerts", [])))

        except Exception as e:
            logger.error(f"Failed to log to MLflow: {e}")


# Example usage
if __name__ == "__main__":
    # Load reference and current data
    # reference_data = pd.read_csv('reference_data.csv')
    # current_data = pd.read_csv('current_data.csv')

    # Initialize monitoring pipeline
    pipeline = AzureMonitoringPipeline(
        storage_account=os.getenv("AZURE_STORAGE_ACCOUNT"), container_name="monitoring"
    )

    # Run monitoring
    # results = pipeline.run_monitoring_pipeline(current_data, reference_data)
    # print(f"Monitoring completed. Alerts: {len(results['alerts'])}")
