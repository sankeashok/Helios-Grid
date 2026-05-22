"""
Model Governance & Registry Management
Handles model versioning, approval workflows, A/B testing configuration,
and lifecycle governance for the Helios-Grid MLOps platform.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelStage(Enum):
    DEVELOPMENT = "Development"
    STAGING = "Staging"
    CANARY = "Canary"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


@dataclass
class ModelCard:
    """Model documentation card for governance compliance."""

    model_name: str
    version: str
    owner: str
    description: str
    training_data_hash: str
    metrics: Dict[str, float]
    hyperparameters: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_by: Optional[str] = None
    approval_status: str = ApprovalStatus.PENDING.value
    deployment_config: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "version": self.version,
            "owner": self.owner,
            "description": self.description,
            "training_data_hash": self.training_data_hash,
            "metrics": self.metrics,
            "hyperparameters": self.hyperparameters,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "approval_status": self.approval_status,
            "deployment_config": self.deployment_config,
            "tags": self.tags,
        }


class ModelGovernance:
    """Manages model lifecycle, approvals, and governance policies."""

    def __init__(self, tracking_uri: str = "mlruns"):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        self.approval_thresholds = {
            "rmse_max": 0.15,
            "mae_max": 0.12,
            "r2_min": 0.85,
            "mape_max": 10.0,
        }

    def register_model(
        self,
        model_uri: str,
        model_name: str,
        metrics: Dict[str, float],
        params: Dict[str, Any],
        training_data_path: str,
        owner: str = "mlops-team",
    ) -> ModelCard:
        """Register a new model version with governance metadata."""

        # Register in MLflow
        result = mlflow.register_model(model_uri, model_name)
        version = result.version

        # Compute data lineage hash
        data_hash = self._compute_data_hash(training_data_path)

        # Create model card
        card = ModelCard(
            model_name=model_name,
            version=version,
            owner=owner,
            description=f"Energy consumption model v{version}",
            training_data_hash=data_hash,
            metrics=metrics,
            hyperparameters=params,
            tags={
                "framework": "scikit-learn",
                "domain": "energy_consumption",
                "pipeline_version": "2.0",
            },
        )

        # Auto-approve if meets thresholds
        if self._check_auto_approval(metrics):
            card.approval_status = ApprovalStatus.AUTO_APPROVED.value
            card.approved_by = "automated-governance"
            self._promote_to_staging(model_name, version)
        else:
            card.approval_status = ApprovalStatus.PENDING.value

        # Store model card as artifact
        self.client.set_model_version_tag(
            model_name, version, "model_card", json.dumps(card.to_dict())
        )
        self.client.set_model_version_tag(
            model_name, version, "approval_status", card.approval_status
        )
        self.client.set_model_version_tag(
            model_name, version, "data_lineage_hash", data_hash
        )

        logger.info(
            f"Model {model_name} v{version} registered. "
            f"Approval: {card.approval_status}"
        )
        return card

    def promote_model(
        self, model_name: str, version: str, target_stage: ModelStage
    ) -> bool:
        """Promote model to target stage with validation."""

        # Validate promotion path
        current_stage = self._get_current_stage(model_name, version)
        if not self._is_valid_promotion(current_stage, target_stage):
            raise ValueError(
                f"Invalid promotion: {current_stage} → {target_stage.value}"
            )

        # Check approval status
        tags = self.client.get_model_version(model_name, version).tags
        approval = tags.get("approval_status", ApprovalStatus.PENDING.value)

        if (
            target_stage == ModelStage.PRODUCTION
            and approval not in [ApprovalStatus.APPROVED.value, ApprovalStatus.AUTO_APPROVED.value]
        ):
            raise ValueError("Model must be approved before production deployment")

        # Perform promotion
        self.client.transition_model_version_stage(
            model_name, version, target_stage.value
        )

        logger.info(f"Model {model_name} v{version} promoted to {target_stage.value}")
        return True

    def get_production_model(self, model_name: str) -> Optional[Dict]:
        """Get current production model details."""
        versions = self.client.get_latest_versions(model_name, stages=["Production"])
        if not versions:
            return None

        v = versions[0]
        return {
            "version": v.version,
            "source": v.source,
            "stage": v.current_stage,
            "tags": v.tags,
            "creation_timestamp": v.creation_timestamp,
        }

    def compare_models(
        self, model_name: str, version_a: str, version_b: str
    ) -> Dict[str, Any]:
        """Compare two model versions for A/B testing decisions."""
        card_a = self._get_model_card(model_name, version_a)
        card_b = self._get_model_card(model_name, version_b)

        if not card_a or not card_b:
            raise ValueError("Model cards not found for comparison")

        comparison = {
            "version_a": version_a,
            "version_b": version_b,
            "metrics_comparison": {},
            "recommendation": None,
        }

        for metric in card_a.get("metrics", {}):
            val_a = card_a["metrics"].get(metric, 0)
            val_b = card_b["metrics"].get(metric, 0)
            improvement = ((val_a - val_b) / val_b * 100) if val_b != 0 else 0

            comparison["metrics_comparison"][metric] = {
                "version_a": val_a,
                "version_b": val_b,
                "improvement_pct": round(improvement, 2),
            }

        # Recommend based on RMSE (lower is better)
        rmse_a = card_a.get("metrics", {}).get("rmse", float("inf"))
        rmse_b = card_b.get("metrics", {}).get("rmse", float("inf"))
        comparison["recommendation"] = version_a if rmse_a < rmse_b else version_b

        return comparison

    def _check_auto_approval(self, metrics: Dict[str, float]) -> bool:
        """Check if model meets auto-approval thresholds."""
        checks = []
        if "rmse" in metrics:
            checks.append(metrics["rmse"] <= self.approval_thresholds["rmse_max"])
        if "mae" in metrics:
            checks.append(metrics["mae"] <= self.approval_thresholds["mae_max"])
        if "r2" in metrics:
            checks.append(metrics["r2"] >= self.approval_thresholds["r2_min"])
        if "mape" in metrics:
            checks.append(metrics["mape"] <= self.approval_thresholds["mape_max"])

        return all(checks) if checks else False

    def _promote_to_staging(self, model_name: str, version: str):
        """Auto-promote approved model to staging."""
        self.client.transition_model_version_stage(model_name, version, "Staging")

    def _get_current_stage(self, model_name: str, version: str) -> str:
        mv = self.client.get_model_version(model_name, version)
        return mv.current_stage

    def _is_valid_promotion(self, current: str, target: ModelStage) -> bool:
        valid_paths = {
            "None": [ModelStage.DEVELOPMENT, ModelStage.STAGING],
            "Development": [ModelStage.STAGING],
            "Staging": [ModelStage.CANARY, ModelStage.PRODUCTION],
            "Canary": [ModelStage.PRODUCTION, ModelStage.ARCHIVED],
            "Production": [ModelStage.ARCHIVED],
        }
        return target in valid_paths.get(current, [])

    def _get_model_card(self, model_name: str, version: str) -> Optional[Dict]:
        mv = self.client.get_model_version(model_name, version)
        card_json = mv.tags.get("model_card")
        return json.loads(card_json) if card_json else None

    def _compute_data_hash(self, data_path: str) -> str:
        try:
            with open(data_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except FileNotFoundError:
            return "unknown"
