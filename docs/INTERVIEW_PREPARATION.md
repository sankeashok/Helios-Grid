# Helios-Grid MLOps Interview Preparation
## MLOps Platform Engineer — Complete Q&A Guide

---

## 1. SYSTEM DESIGN QUESTIONS

---

### Q1: Design an end-to-end ML platform for energy consumption prediction. Walk us through the architecture.

**Answer:**

I built Helios-Grid, an enterprise MLOps platform for energy consumption prediction. The architecture follows a layered approach:

**Data Layer:**
- Kaggle dataset ingestion via `kagglehub` with automated validation using Great Expectations
- Azure Blob Storage for raw/processed data versioning
- Data lineage tracking via SHA-256 hashing of training datasets

**Feature Engineering Layer:**
- Custom sklearn-compatible `EnergyFeatureEngineer` transformer with cyclical encoding (sin/cos for hour, day, month), lag features (1h to 2 weeks), rolling statistics, and interaction features
- Feature selection using mutual information regression
- Feature pipeline serialized with joblib for reproducibility

**Training Layer:**
- Optuna hyperparameter optimization across XGBoost, LightGBM, and Random Forest
- TimeSeriesSplit cross-validation (not random split — critical for time series)
- GPU orchestrator supporting Azure ML, SageMaker, and on-premise Docker GPU
- Job queuing with priority and budget limits

**Serving Layer:**
- FastAPI production server with Prometheus metrics instrumentation
- Docker containerized, deployed on Railway (cloud) and K8s (enterprise)
- Health checks, readiness probes, and graceful shutdown

**Monitoring Layer:**
- Statistical drift detection (KS test + PSI) running every 6 hours via Airflow
- Prometheus + Grafana dashboards for latency, RMSE, drift score, GPU utilization
- Auto-retraining trigger when both drift AND performance degradation detected

**Orchestration Layer:**
- 3 Airflow DAGs: Training Pipeline, Deployment Pipeline, Monitoring Pipeline
- Training DAG triggers Deployment DAG on success
- Monitoring DAG triggers Training DAG on degradation

**CI/CD Layer:**
- GitHub Actions 10-stage pipeline: Quality → Tests → Container → Staging → Auto-merge → Production → Release
- GitFlow pattern: Feature Branch → Staging → Main → Production

---

### Q2: How would you handle model versioning and rollback in production?

**Answer:**

I implemented a `ModelGovernance` class that manages the full lifecycle:

1. **Registration:** Every trained model gets a `ModelCard` with metrics, hyperparameters, data lineage hash, and owner
2. **Auto-approval:** If metrics meet thresholds (RMSE ≤ 0.15, R² ≥ 0.85), model auto-promotes to Staging
3. **Promotion path:** Development → Staging → Canary → Production → Archived
4. **Validation gates:** Production promotion requires approval status (auto or manual)
5. **Rollback:** The deployment DAG has a `rollback_model` task that reverts to the previous Production version if shadow testing fails

For A/B testing, I have a `compare_models` method that compares two versions side-by-side on all metrics and recommends the better one.

The key insight: **never promote directly to Production**. Always go through Canary (10% traffic) first, validate with `post_deployment_validation`, then full rollout.

---

### Q3: How do you ensure reproducibility in your ML pipeline?

**Answer:**

Multiple layers:

1. **Data versioning:** SHA-256 hash of training data stored as model tag in MLflow. If data changes, hash changes, and we know the model was trained on different data.
2. **Experiment tracking:** MLflow logs every parameter, metric, and artifact. Every training run is fully reproducible.
3. **Feature pipeline serialization:** The fitted `EnergyFeatureEngineer` is saved with joblib — same transformations applied at inference.
4. **Environment pinning:** `requirements.txt` with exact versions, Docker images tagged with version numbers.
5. **Random state:** All models use `random_state=42`, all splits are deterministic.
6. **Airflow DAGs:** Fixed schedule, fixed configs — same DAG run produces same results given same data.

---

### Q4: How would you scale this platform for 100x more models?

**Answer:**

1. **Compute:** Move from single GPU pool to Kubernetes-based auto-scaling GPU clusters (Azure ML Compute or SageMaker endpoints with auto-scaling policies)
2. **Orchestration:** Move from LocalExecutor to CeleryExecutor or KubernetesExecutor in Airflow for parallel DAG execution
3. **Feature Store:** Add a centralized feature store (Feast or Azure Feature Store) so features are computed once and shared across models
4. **Model Registry:** Namespace models by team/domain, add RBAC for governance
5. **Monitoring:** Per-model dashboards auto-generated from templates, alert routing by model owner
6. **CI/CD:** Monorepo with path-based triggers — only rebuild/redeploy models whose code changed

---

## 2. DEVOPS & CI/CD QUESTIONS

---

### Q5: Explain your CI/CD pipeline for ML models.

**Answer:**

My GitHub Actions enterprise pipeline has 10 stages:

1. **Code Quality** — Black formatting, Flake8 linting, Bandit security scan
2. **Backend Tests** — Matrix strategy: core tests, dependency tests, integration tests (parallel)
3. **Frontend Tests** — React build + test with coverage
4. **Containerization** — Docker build validation
5. **Deployment Readiness** — Gate check that all prior stages passed
6. **Staging Deployment** — Deploy to staging environment (feature branches only)
7. **Auto-merge to Main** — If staging passes, auto-merge feature branch → main
8. **Production Deployment** — Hugging Face Spaces + Vercel + Docker Hub (main branch only)
9. **Release Creation** — Generate release notes with version tag
10. **Success Notification** — Final status report

Key design decisions:
- **Sequential flow** — no parallel stages that could conflict
- **Feature branch isolation** — production only deploys from main
- **Non-blocking quality checks** — formatting issues warn but don't block (prevents developer friction)

---

### Q6: How do you handle secrets and credentials in your pipeline?

**Answer:**

- **GitHub Secrets** for CI/CD: `GITHUB_TOKEN`, `HF_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- **Azure Key Vault** for runtime secrets: API keys, database credentials, accessed via `DefaultAzureCredential`
- **Environment variables** with `.env.example` template (never commit actual `.env`)
- **Docker secrets** for container deployments
- **Conditional deployment** — if secrets aren't configured, pipeline simulates deployment instead of failing

```yaml
if [ -z "$VERCEL_TOKEN" ]; then
  echo "Simulating deployment..."
else
  vercel deploy --prod --token=$VERCEL_TOKEN
fi
```

---

### Q7: How do you handle infrastructure as code?

**Answer:**

- **Docker:** Multi-stage Dockerfiles (`Dockerfile`, `Dockerfile.production`, `Dockerfile.local`) with health checks
- **Docker Compose:** Separate configs for local dev, monitoring stack, and full Airflow orchestration
- **Kubernetes:** `k8s/deployment.yaml` with 3 replicas, resource limits, liveness/readiness probes, Ingress with TLS
- **Azure Pipelines:** `.azure/azure-pipelines.yml` for Azure-native CI/CD
- **Railway:** `railway.toml` for cloud deployment config

The K8s deployment includes:
- Resource requests/limits (256Mi-512Mi memory, 250m-500m CPU)
- Health check on `/health` endpoint
- LoadBalancer service + Nginx Ingress with cert-manager TLS

---

### Q8: How would you implement blue-green or canary deployments for ML models?

**Answer:**

My deployment DAG implements this:

1. **Shadow Testing** — New model runs alongside production on real traffic, predictions compared but not served
2. **Strategy Decision:**
   - RMSE < 0.10 → Full rollout (model is clearly better)
   - RMSE 0.10-0.15 → Canary (10% traffic via K8s weighted routing)
   - RMSE > 0.15 → Rollback (model rejected)
3. **Canary Validation** — Monitor canary for 1 hour, check error rates and latency
4. **Full Promotion** — If canary healthy, update K8s deployment to 100% new model
5. **Rollback** — If issues detected, `kubectl rollout undo` to previous version

In K8s, this is implemented with two Deployments (stable + canary) and an Istio/Nginx weighted routing rule.

---

### Q9: How do you monitor your CI/CD pipeline health?

**Answer:**

- **GitHub Actions dashboard** — visual pipeline status per branch
- **Pipeline success notification** (Stage 10) — reports all stage statuses
- **Auto-merge validation** — if merge fails, pipeline reports the conflict
- **Docker build validation** — catches dependency issues before production
- **Artifact upload** — React build artifacts preserved for debugging failed deployments

For the ML-specific pipeline (Airflow):
- Airflow UI shows DAG run history, task durations, and failure reasons
- Prometheus scrapes Airflow metrics (DAG run duration, task success rate)
- Grafana panel shows pipeline health over time

---

## 3. TECHNICAL / ML ENGINEERING QUESTIONS

---

### Q10: Why did you choose XGBoost/LightGBM over deep learning for energy prediction?

**Answer:**

For tabular time series with engineered features:
- **XGBoost/LightGBM outperform deep learning** on structured data with < 100K samples
- **Interpretability** — feature importance is directly available, critical for energy domain
- **Training speed** — 50 Optuna trials complete in minutes vs hours for neural networks
- **Deployment simplicity** — sklearn-compatible models serialize to pickle, no GPU needed for inference

I would use LSTM/Transformer only if:
- Raw sequence data without feature engineering
- Very long-range dependencies (months ahead)
- Multivariate time series with complex interactions

---

### Q11: Explain your hyperparameter optimization strategy.

**Answer:**

I use Optuna with these design choices:

1. **Search space per model type:**
   - XGBoost: n_estimators (100-2000), max_depth (3-12), learning_rate (0.01-0.3), subsample, colsample_bytree, reg_alpha, reg_lambda
   - LightGBM: Same + num_leaves (10-500), min_child_samples
   - Random Forest: n_estimators (100-1000), max_depth (5-25), min_samples_split/leaf

2. **Cross-validation:** TimeSeriesSplit with 5 folds (not random KFold — that would leak future data)

3. **Objective:** Minimize negative MSE (Optuna minimizes by default)

4. **Multi-model sweep:** Train all 3 model types, pick the best RMSE across all

5. **Early stopping:** For XGBoost/LightGBM, use eval_set with early_stopping_rounds=50 to prevent overfitting

6. **Cost-aware:** Limited to 50 trials per model type to stay within GPU budget

---

### Q12: How do you detect data drift in production?

**Answer:**

My `DriftDetector` class uses multiple statistical tests:

1. **Kolmogorov-Smirnov test** — Compares distributions of reference vs current data. Non-parametric, works for any distribution shape.

2. **Population Stability Index (PSI)** — Bins reference data into 10 buckets, compares bucket proportions. PSI > 0.2 = significant drift.

3. **Mean shift detection** — Measures how many standard deviations the current mean has shifted from reference.

4. **Chi-square test** — For categorical features, compares frequency distributions.

5. **Combined score:** `max(KS statistic, PSI, normalized mean shift)` — if any test flags drift, we investigate.

The monitoring DAG runs every 6 hours and:
- If drift detected BUT performance OK → send warning alert
- If drift AND performance degraded → auto-trigger retraining
- If no drift → log healthy status

This avoids unnecessary retraining (drift doesn't always mean degradation).

---

### Q13: How do you handle feature engineering for time series data?

**Answer:**

My `EnergyFeatureEngineer` creates 5 categories of features:

1. **Temporal features:** hour, day_of_week, month, quarter, day_of_year + cyclical encoding (sin/cos) to capture periodicity without discontinuity at boundaries

2. **Lag features:** 1h, 2h, 3h, 6h, 12h, 24h, 48h, 168h (1 week), 336h (2 weeks) — captures autocorrelation at different scales

3. **Rolling statistics:** mean, std, min, max, median, Q25, Q75 over 6h, 12h, 24h, 48h, 168h windows — captures trends and volatility

4. **Domain features:** is_weekend, is_business_hour, is_peak_morning (7-9), is_peak_evening (17-20), season, is_summer_peak, is_winter_peak

5. **Interaction features:** hour × weekend, hour × season, business_hour × weekday — captures conditional patterns

Key implementation details:
- Sklearn-compatible (fit/transform pattern) for pipeline integration
- Removes features with correlation > 0.95 to reduce multicollinearity
- Uses RobustScaler (handles outliers better than StandardScaler for energy data)
- Feature selection via mutual information regression (captures non-linear relationships)

---

### Q14: How do you handle the cold start problem when deploying a new model with no production data?

**Answer:**

1. **Shadow mode first** — Deploy new model alongside existing one, compare predictions on live traffic without serving them
2. **Backtest on historical data** — Use last 3 months of production logs as validation set
3. **Conservative thresholds** — Set stricter approval gates for first deployment (RMSE < 0.12 instead of 0.15)
4. **Gradual rollout** — Start with 5% canary, increase to 10%, 25%, 50%, 100% over days
5. **Fallback model** — Always keep a simple baseline (e.g., last-24h-average) as emergency fallback

---

### Q15: Explain your model serving architecture.

**Answer:**

**FastAPI production server** with:
- `/predict` endpoint — accepts JSON with features, returns prediction + confidence
- `/batch-predict` endpoint — accepts CSV, returns batch predictions
- `/health` endpoint — K8s liveness probe
- `/metrics` endpoint — Prometheus metrics (latency histogram, request counter, error counter)

**Performance optimizations:**
- Model loaded once at startup (not per-request)
- Numpy operations for batch inference
- Async endpoints for I/O-bound operations
- Docker health check every 30s

**Instrumentation:**
- `@track_prediction` decorator automatically records latency, success/error counts
- Prometheus histogram with buckets: 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s
- Model version label on all metrics for A/B comparison

---

## 4. CODING QUESTIONS

---

### Q16: Write a function to calculate Population Stability Index (PSI).

**Answer:**

```python
def calculate_psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """Calculate PSI to measure distribution shift."""
    # Create bins from reference data
    _, bin_edges = np.histogram(reference, bins=bins)
    
    # Calculate proportions in each bin
    ref_hist, _ = np.histogram(reference, bins=bin_edges)
    curr_hist, _ = np.histogram(current, bins=bin_edges)
    
    ref_dist = ref_hist / len(reference)
    curr_dist = curr_hist / len(current)
    
    # Avoid log(0) — replace zeros with small epsilon
    ref_dist = np.where(ref_dist == 0, 0.0001, ref_dist)
    curr_dist = np.where(curr_dist == 0, 0.0001, curr_dist)
    
    # PSI formula: sum((current - reference) * ln(current / reference))
    psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))
    return psi

# Interpretation:
# PSI < 0.1  → No significant drift
# PSI 0.1-0.2 → Moderate drift, monitor closely
# PSI > 0.2  → Significant drift, investigate/retrain
```

---

### Q17: How would you implement a rate limiter for your ML API?

**Answer:**

```python
import time
from collections import defaultdict

class SlidingWindowRateLimiter:
    """Sliding window rate limiter for ML API."""
    
    def __init__(self, max_requests: int = 1000, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        current_time = time.time()
        cutoff = current_time - self.window_seconds
        
        # Remove expired timestamps
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > cutoff
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(current_time)
        return True
```

In my project, this is implemented in `enterprise_security.py` with async support and IP-based tracking.

---

### Q18: Write a decorator that tracks ML prediction latency and pushes to Prometheus.

**Answer:**

```python
import time
from functools import wraps
from prometheus_client import Histogram, Counter

LATENCY = Histogram(
    "prediction_latency_seconds",
    "Prediction latency",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)
REQUESTS = Counter("prediction_requests_total", "Total requests", ["status"])

def track_prediction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            REQUESTS.labels(status="success").inc()
            return result
        except Exception as e:
            REQUESTS.labels(status="error").inc()
            raise
        finally:
            LATENCY.observe(time.time() - start)
    return wrapper
```

---

### Q19: How would you implement a model quality gate in an Airflow DAG?

**Answer:**

```python
from airflow.operators.python import BranchPythonOperator

def evaluate_model_gate(**context):
    """Branch based on model quality metrics."""
    best_rmse = context["ti"].xcom_pull(key="best_rmse")
    best_r2 = context["ti"].xcom_pull(key="best_r2")
    
    # Multi-metric gate
    if best_rmse <= 0.15 and best_r2 >= 0.85:
        return "register_model"  # Proceed to deployment
    elif best_rmse <= 0.20:
        return "send_review_alert"  # Needs human review
    else:
        return "notify_model_rejected"  # Auto-reject

model_gate = BranchPythonOperator(
    task_id="model_quality_gate",
    python_callable=evaluate_model_gate,
    dag=dag,
)
```

This is exactly what I implemented in `orchestration/dags/ml_training_pipeline.py`.

---

### Q20: How do you ensure your feature engineering is consistent between training and inference?

**Answer:**

```python
class EnergyFeatureEngineer(BaseEstimator, TransformerMixin):
    """Sklearn-compatible transformer ensures consistency."""
    
    def fit(self, X, y=None):
        # Learn statistics from training data
        self.feature_names_ = list(X.columns)
        self.scaler.fit(X)
        self.feature_selector.fit(X, y)
        return self
    
    def transform(self, X):
        # Apply same transformations at inference
        X_features = self._create_all_features(X.copy())
        
        # Ensure same columns as training
        missing_cols = set(self.feature_names_) - set(X_features.columns)
        for col in missing_cols:
            X_features[col] = 0
        
        # Same column order
        X_features = X_features[self.feature_names_]
        
        # Same scaling
        X_features = self.scaler.transform(X_features)
        return X_features
```

The key: **serialize the fitted transformer** with the model. At inference, load both model AND feature pipeline. Never recompute statistics from production data.

---

## 5. SCENARIO-BASED QUESTIONS

---

### Q21: Your model's RMSE suddenly increased by 30% in production. How do you investigate?

**Answer:**

1. **Check monitoring dashboard** — Is it a sudden spike or gradual degradation?
2. **Run drift detection** — Compare last 24h of input features against training distribution
3. **Check data pipeline** — Did upstream data source change schema or format?
4. **Check feature distributions** — Which specific features drifted? (my `DriftDetector` reports per-feature scores)
5. **Check for data quality issues** — Null values, outliers, encoding errors
6. **Compare predictions** — Are predictions systematically high/low (bias shift) or just noisy (variance increase)?
7. **Rollback if critical** — If error rate > 5%, immediately rollback to previous model version
8. **Root cause** — Usually one of: seasonal shift, upstream data change, or concept drift

My monitoring DAG automates steps 1-3 and triggers retraining if both drift and degradation are confirmed.

---

### Q22: A training job is taking 10x longer than expected. What do you do?

**Answer:**

1. **Check GPU utilization** — If low (<20%), likely a data loading bottleneck, not compute
2. **Check data size** — Did the dataset grow unexpectedly?
3. **Check hyperparameter space** — Did n_trials accidentally increase?
4. **Check for memory issues** — OOM causing swap, which is 100x slower
5. **Check cost** — My `TrainingJobQueue` has `max_runtime_hours` limit. If exceeded, job auto-terminates
6. **Mitigation:**
   - Reduce n_trials for initial sweep
   - Use early stopping more aggressively
   - Sample data for hyperparameter search, train final model on full data
   - Use preemptible/spot instances for cost control

---

### Q23: How would you onboard a new ML model to your platform?

**Answer:**

1. **Create model config** — Define `EnergyModelConfig` (or equivalent) with model type, hyperparameter space, CV strategy
2. **Add to Airflow DAG** — Add model type to the `model_configs` list in `run_hyperparameter_sweep`
3. **Register in governance** — Model gets a `ModelCard` with owner, description, approval thresholds
4. **Add monitoring** — Define model-specific drift thresholds and performance baselines
5. **CI/CD** — Model code goes through same pipeline (quality → test → container → deploy)
6. **Documentation** — Update model card with training data, features, known limitations

The platform is designed so adding a new model is just adding a config — not rewriting infrastructure.

---

### Q24: How do you handle training on both cloud and on-premise GPU?

**Answer:**

My `GPUTrainingOrchestrator` abstracts the compute target:

```python
class ComputeTarget(Enum):
    LOCAL_GPU = "local_gpu"
    AZURE_ML_GPU = "azure_ml_gpu"
    AWS_SAGEMAKER = "aws_sagemaker"
    ON_PREMISE_GPU = "on_premise_gpu"
```

Each target has a specific launcher:
- **Azure ML:** Creates `AmlCompute` cluster (Standard_NC6s_v3 with V100), submits `ScriptRunConfig`
- **SageMaker:** Creates `Estimator` with `ml.g4dn.xlarge`, supports spot instances
- **On-premise:** Launches Docker container with `--gpus` flag via SSH
- **Local:** Direct Python execution

The Airflow DAG uses `pool="gpu_pool"` with max 2 concurrent jobs to prevent resource contention. Priority queue ensures critical retraining jobs run before experimental ones.

---

### Q25: How do you ensure security in your ML pipeline?

**Answer:**

My `enterprise_security.py` implements:

1. **Input validation** — SQL injection detection (regex patterns), XSS detection, null byte removal
2. **Rate limiting** — Sliding window per IP (1000 req/hour default)
3. **JWT authentication** — Token generation with security context, MFA support, token blacklisting
4. **RBAC** — `@require_permission` decorator for endpoint-level access control
5. **Secrets management** — Azure Key Vault integration, never hardcoded credentials
6. **Audit logging** — Every security event logged with threat level and action taken
7. **SAST/DAST integration** — Bandit scan in CI/CD pipeline, security scanner class for runtime

Zero-trust principle: every request is validated regardless of source network.

---

## 6. BEHAVIORAL / PROCESS QUESTIONS

---

### Q26: How do you promote MLOps best practices in a team?

**Answer:**

Based on my Helios-Grid implementation:

1. **Make it easy** — Provide templates (model configs, DAG templates, Dockerfile templates) so teams don't start from scratch
2. **Automate governance** — Auto-approval gates mean teams don't need manual reviews for good models
3. **Visibility** — Grafana dashboards show everyone's model health. Peer pressure works.
4. **Documentation** — I maintain wiki docs for every component (Installation Guide, API Documentation, System Architecture)
5. **CI/CD enforcement** — Pipeline blocks bad code from reaching production. No exceptions.
6. **Cost transparency** — Training cost reports make teams conscious of resource usage

---

### Q27: Describe a time you had to debug a complex pipeline issue.

**Answer:**

In Helios-Grid, my CI/CD pipeline had multiple workflows triggering simultaneously, causing:
- Resource waste (3 pipelines running for 1 commit)
- Race conditions on auto-merge
- Confusing status checks

**Root cause:** Multiple workflow files in `.github/workflows/` all triggered on the same events.

**Solution:** Consolidated into a single `enterprise-pipeline.yml` with 10 sequential stages. Moved old workflows to `_temp/_temp_workflows/` with `.disabled` extension. Added `max_active_runs=1` in Airflow to prevent similar issues there.

**Lesson:** One pipeline to rule them all. Complexity should be in stages within a pipeline, not in multiple competing pipelines.

---

### Q28: How do you balance speed of iteration with production stability?

**Answer:**

- **Feature branches** — Developers iterate fast on feature branches without affecting production
- **Staging environment** — Every feature branch deploys to staging for validation
- **Auto-merge with gates** — Only merge to main if ALL stages pass (quality, tests, container, staging)
- **Canary deployments** — New models serve 10% traffic first
- **Rollback capability** — One-click (or auto) rollback if metrics degrade
- **Non-blocking quality checks** — Formatting warnings don't block deployment (prevents developer friction)

The key insight: **fast iteration on feature branches, strict gates before production**.

---

## 7. QUICK-FIRE TECHNICAL QUESTIONS

---

### Q29: What's the difference between data drift and concept drift?

**Data drift:** Input feature distributions change (e.g., temperature patterns shift due to climate change). Detected by comparing P(X) between reference and current.

**Concept drift:** The relationship between features and target changes (e.g., energy consumption patterns change due to new building regulations). Detected by monitoring P(Y|X) — model performance degrades even if inputs look similar.

My monitoring handles both: drift detection catches data drift, performance monitoring catches concept drift.

---

### Q30: Why TimeSeriesSplit instead of KFold for energy data?

KFold randomly shuffles data, which means training on future data to predict the past — **data leakage**. TimeSeriesSplit always trains on past, validates on future, mimicking real deployment conditions.

---

### Q31: What's PSI and when would you use it?

Population Stability Index measures how much a distribution has shifted. Formula: Σ (current% - reference%) × ln(current% / reference%). 

Use it for: monitoring feature distributions in production, validating that new training data is representative, detecting upstream data pipeline issues.

---

### Q32: How does your Airflow pool work for GPU jobs?

`gpu_pool` has slots=2, meaning max 2 GPU training jobs run concurrently. Jobs with higher `priority_weight` get scheduled first. This prevents OOM on shared GPU clusters and ensures critical retraining jobs aren't blocked by experimental ones.

---

### Q33: What's the purpose of the data lineage hash in your governance system?

SHA-256 hash of training data stored with each model version. If I need to reproduce a model, I can verify I'm using the exact same training data. Also detects if someone accidentally retrained on corrupted/different data.

---

### Q34: Why Prometheus + Grafana instead of CloudWatch or Azure Monitor?

- **Vendor-agnostic** — works on any cloud or on-premise
- **Pull-based model** — Prometheus scrapes targets, no agent installation needed
- **PromQL** — powerful query language for complex ML metrics
- **Custom metrics** — easy to add model-specific metrics via client library
- **Cost** — open source, no per-metric charges at scale

I'd use CloudWatch/Azure Monitor for infrastructure metrics, Prometheus for ML-specific metrics.

---

### Q35: How do you handle model serving at scale?

- **Horizontal scaling** — K8s deployment with 3 replicas, HPA based on CPU/latency
- **Batch prediction** — Separate endpoint for bulk inference (more efficient than N individual calls)
- **Model caching** — Load model once at startup, not per-request
- **Async processing** — FastAPI async endpoints for I/O-bound operations
- **Connection pooling** — Reuse database/storage connections

For very high throughput (>10K req/sec), I'd add:
- Model compilation (ONNX Runtime)
- Request batching at the serving layer
- Dedicated inference GPU instances

---
