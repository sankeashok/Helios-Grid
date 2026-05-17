import gradio as gr
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json


# Simple prediction function (fallback when API is not available)
def simple_prediction(hour, temperature, day_of_week):
    """Local prediction when API is unavailable"""
    base_consumption = 100.0

    # Hour factor
    if 8 <= hour <= 10 or 18 <= hour <= 20:  # Peak hours
        hour_factor = 1.5
    elif 22 <= hour <= 6:  # Night hours
        hour_factor = 0.7
    else:
        hour_factor = 1.0

    # Temperature factor
    if temperature > 25:  # Hot weather (AC usage)
        temp_factor = 1.3
    elif temperature < 10:  # Cold weather (heating)
        temp_factor = 1.2
    else:
        temp_factor = 1.0

    # Day factor
    if day_of_week in [6, 7]:  # Weekend
        day_factor = 0.9
    else:
        day_factor = 1.1

    prediction = base_consumption * hour_factor * temp_factor * day_factor
    prediction += np.random.normal(0, 5)
    prediction = max(prediction, 10.0)

    confidence = min(0.95, max(0.6, 1.0 - abs(prediction - 100) / 200))

    return prediction, confidence, "local_model_v1.0"


def predict_energy(
    hour, temperature, day_of_week, api_endpoint="http://localhost:8000"
):
    """Main prediction function"""

    # Try API first
    try:
        response = requests.post(
            f"{api_endpoint}/predict",
            json={
                "features": {
                    "hour": float(hour),
                    "temperature": float(temperature),
                    "day_of_week": float(day_of_week),
                }
            },
            timeout=5,
        )

        if response.status_code == 200:
            result = response.json()
            prediction = result.get("prediction", 0)
            confidence = result.get("confidence", 0) * 100
            model_version = result.get("model_version", "api")
            status = "🟢 API Connected"
        else:
            raise Exception("API Error")

    except Exception as e:
        # Fallback to local prediction
        prediction, conf, model_version = simple_prediction(
            hour, temperature, day_of_week
        )
        confidence = conf * 100
        status = "🟡 Local Mode (API Unavailable)"

    # Format results
    result_text = f"""
    ## 🔮 Energy Prediction Results
    
    **Energy Consumption:** {prediction:.2f} kWh
    **Confidence:** {confidence:.1f}%
    **Model Version:** {model_version}
    **Status:** {status}
    
    ### 📊 Input Parameters:
    - **Hour:** {hour}:00 ({get_time_period(hour)})
    - **Temperature:** {temperature}°C ({get_temp_category(temperature)})
    - **Day:** {get_day_name(day_of_week)} ({get_day_type(day_of_week)})
    """

    return result_text


def get_time_period(hour):
    """Get time period description"""
    if 6 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 18:
        return "Afternoon"
    elif 18 <= hour < 22:
        return "Evening"
    else:
        return "Night"


def get_temp_category(temp):
    """Get temperature category"""
    if temp < 10:
        return "Cold"
    elif temp > 25:
        return "Hot"
    else:
        return "Moderate"


def get_day_name(day_num):
    """Get day name from number"""
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return days[day_num - 1]


def get_day_type(day_num):
    """Get day type"""
    return "Weekend" if day_num in [6, 7] else "Weekday"


def generate_forecast(temperature, day_of_week):
    """Generate 24-hour forecast"""
    hours = list(range(24))
    predictions = []

    for hour in hours:
        pred, _, _ = simple_prediction(hour, temperature, day_of_week)
        predictions.append(pred)

    # Create plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=predictions,
            mode="lines+markers",
            name="Energy Consumption",
            line=dict(color="#667eea", width=3),
            marker=dict(size=6),
        )
    )

    fig.update_layout(
        title="24-Hour Energy Consumption Forecast",
        xaxis_title="Hour of Day",
        yaxis_title="Energy Consumption (kWh)",
        template="plotly_white",
        height=400,
        showlegend=False,
    )

    return fig


# Create Gradio interface
with gr.Blocks(
    theme=gr.themes.Soft(),
    title="☀️ Helios-Grid Energy Predictor",
    css="""
    .gradio-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main-header {
        text-align: center;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    """,
) as app:

    # Header
    gr.HTML(
        """
    <div class="main-header">
        <h1 style="color: white; font-size: 3rem; margin-bottom: 1rem;">☀️ Helios-Grid</h1>
        <h2 style="color: white; font-size: 1.5rem; margin-bottom: 0.5rem;">AI-Powered Energy Consumption Predictor</h2>
        <p style="color: white; opacity: 0.9;">Enterprise MLOps Pipeline for Energy Forecasting</p>
    </div>
    """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 🎛️ Prediction Parameters")

            hour = gr.Slider(
                minimum=0,
                maximum=23,
                value=14,
                step=1,
                label="⏰ Hour of Day (0-23)",
                info="Select the hour for prediction",
            )

            temperature = gr.Slider(
                minimum=-20,
                maximum=50,
                value=22,
                step=1,
                label="🌡️ Temperature (°C)",
                info="Current temperature in Celsius",
            )

            day_of_week = gr.Dropdown(
                choices=[
                    (1, "Monday"),
                    (2, "Tuesday"),
                    (3, "Wednesday"),
                    (4, "Thursday"),
                    (5, "Friday"),
                    (6, "Saturday"),
                    (7, "Sunday"),
                ],
                value=3,
                label="📅 Day of Week",
                info="Select the day of the week",
            )

            api_endpoint = gr.Textbox(
                value="http://localhost:8000",
                label="🔗 API Endpoint",
                info="Helios-Grid API URL (optional)",
            )

            predict_btn = gr.Button(
                "⚡ Predict Energy Consumption", variant="primary", size="lg"
            )

        with gr.Column(scale=2):
            gr.Markdown("## 🔮 Prediction Results")

            result_output = gr.Markdown(
                value="Click 'Predict Energy Consumption' to get started!",
                elem_classes=["prediction-output"],
            )

    with gr.Row():
        gr.Markdown("## 📈 24-Hour Energy Forecast")

    with gr.Row():
        forecast_plot = gr.Plot(label="Energy Consumption Forecast")

        generate_forecast_btn = gr.Button(
            "📊 Generate 24-Hour Forecast", variant="secondary"
        )

    # Event handlers
    predict_btn.click(
        fn=predict_energy,
        inputs=[hour, temperature, day_of_week, api_endpoint],
        outputs=result_output,
    )

    generate_forecast_btn.click(
        fn=generate_forecast, inputs=[temperature, day_of_week], outputs=forecast_plot
    )

    # Footer
    gr.HTML(
        """
    <div style="text-align: center; padding: 2rem; margin-top: 2rem; background: rgba(255, 255, 255, 0.1); border-radius: 15px;">
        <h3 style="color: white;">☀️ Helios-Grid Energy Predictor</h3>
        <p style="color: white; opacity: 0.9;">Powered by AI • Built for Energy Efficiency • Deploy Anywhere</p>
        <p style="color: white; opacity: 0.8;"><strong>Deployment Options:</strong> Gradio Cloud • Streamlit • Docker • Local Python</p>
    </div>
    """
    )

# Launch the app
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
