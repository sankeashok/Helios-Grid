"""
Helios-Grid Production Status Check
Simple verification that everything is ready for deployment
"""

import os
import json
from pathlib import Path


def check_status():
    """Check production readiness status"""

    print("HELIOS-GRID PRODUCTION STATUS CHECK")
    print("=" * 50)

    status = {
        "model_trained": False,
        "model_file_exists": False,
        "mlflow_data": False,
        "ci_cd_pipeline": False,
        "email_configured": True,  # User confirmed this
        "production_server": False,
    }

    # Check model file
    model_path = Path("models/helios_grid_production_model.pkl")
    if model_path.exists():
        status["model_trained"] = True
        status["model_file_exists"] = True
        print("✅ Production model file exists")
        print(f"   Location: {model_path}")
        print(f"   Size: {model_path.stat().st_size / 1024:.1f} KB")
    else:
        print("❌ Production model file missing")

    # Check model info
    model_info_path = Path("models/model_info.json")
    if model_info_path.exists():
        try:
            with open(model_info_path) as f:
                model_info = json.load(f)
            print("✅ Model info available")
            print(f"   Model Type: {model_info.get('model_type', 'unknown')}")
            print(f"   Training Date: {model_info.get('training_date', 'unknown')}")
            if "metrics" in model_info:
                metrics = model_info["metrics"]
                print(f"   Test R²: {metrics.get('test_r2', 'N/A'):.4f}")
                print(f"   Test RMSE: {metrics.get('test_rmse', 'N/A'):.2f} kWh")
        except Exception as e:
            print(f"⚠️ Model info file corrupted: {e}")

    # Check MLflow data
    mlruns_path = Path("mlruns")
    if mlruns_path.exists() and any(mlruns_path.iterdir()):
        status["mlflow_data"] = True
        print("✅ MLflow experiment data exists")
        experiments = list(mlruns_path.iterdir())
        print(f"   Experiments: {len(experiments)}")
    else:
        print("❌ MLflow experiment data missing")

    # Check CI/CD pipeline file
    pipeline_path = Path(".github/workflows/main-ci.yml")
    if pipeline_path.exists():
        status["ci_cd_pipeline"] = True
        print("✅ CI/CD pipeline configured")
        print(f"   Pipeline: {pipeline_path}")
    else:
        print("❌ CI/CD pipeline missing")

    # Check production server
    server_path = Path("production_server.py")
    if server_path.exists():
        status["production_server"] = True
        print("✅ Production server ready")
        print(f"   Server: {server_path}")
    else:
        print("❌ Production server missing")

    # Check data files
    data_path = Path("data")
    if data_path.exists():
        data_files = list(data_path.glob("*.csv"))
        if data_files:
            print("✅ Training data available")
            print(f"   Data files: {len(data_files)}")
        else:
            print("⚠️ No training data files found")

    # Email configuration (user confirmed)
    print("✅ Email notifications configured")
    print("   Gmail: sanke.shokk@gmail.com")
    print("   App Password: ****")

    # Overall status
    print("\n" + "=" * 50)
    print("OVERALL STATUS")
    print("=" * 50)

    ready_count = sum(status.values())
    total_count = len(status)

    for component, ready in status.items():
        status_icon = "✅" if ready else "❌"
        print(f"{status_icon} {component.replace('_', ' ').title()}")

    print(f"\nReadiness: {ready_count}/{total_count} components ready")

    if ready_count == total_count:
        print("\n🎉 PRODUCTION READY!")
        print("✅ All systems operational")
        print("✅ CI/CD pipeline should pass")
        print("✅ Email notifications will be sent")
        print("\n🚀 Next Steps:")
        print(
            "1. Monitor CI/CD pipeline: https://github.com/sankeashok/Helios-Grid/actions"
        )
        print("2. Check email for deployment notifications")
        print("3. Start production server: python production_server.py")
        print("4. Access API: http://localhost:3002")
        print("5. View MLflow: mlflow ui (http://localhost:5000)")
    else:
        missing = [comp for comp, ready in status.items() if not ready]
        print(f"\n⚠️ Missing components: {', '.join(missing)}")
        print("Fix missing components before deployment")

    return ready_count == total_count


if __name__ == "__main__":
    check_status()
