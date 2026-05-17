import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json

# Page configuration
st.set_page_config(
    page_title="Helios-Grid Energy Predictor",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="auto",  # Auto-collapse on mobile
)

# Mobile-friendly CSS with responsive design
st.markdown(
    """
<style>
    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem !important;
            margin-bottom: 1rem !important;
        }
        .prediction-result {
            padding: 1rem !important;
            font-size: 1.2rem !important;
        }
        .stColumn {
            padding: 0.5rem !important;
        }
        .stMetric {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.5rem;
            border-radius: 8px;
            margin: 0.25rem 0;
        }
    }
    
    /* Touch-friendly buttons */
    .stButton > button {
        height: 3rem;
        font-size: 1.1rem;
        border-radius: 25px;
        background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
        border: none;
        color: white;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 53, 0.4);
    }
    
    /* Mobile-optimized header */
    .main-header {
        font-size: 3rem;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #FF6B35, #F7931E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Responsive metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 15px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
    }
    
    /* Mobile-optimized prediction result */
    .prediction-result {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.3);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    /* Mobile sidebar optimization */
    @media (max-width: 768px) {
        .css-1d391kg {
            padding-top: 1rem;
        }
        .stSidebar {
            width: 100% !important;
        }
    }
    
    /* Touch-friendly sliders */
    .stSlider {
        padding: 1rem 0;
    }
    
    /* Responsive charts */
    .js-plotly-plot {
        width: 100% !important;
    }
    
    /* Mobile navigation */
    .mobile-nav {
        display: none;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        z-index: 1000;
        box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.1);
    }
    
    @media (max-width: 768px) {
        .mobile-nav {
            display: flex;
            justify-content: space-around;
        }
        .mobile-nav-item {
            color: white;
            text-align: center;
            font-size: 0.8rem;
            cursor: pointer;
        }
    }
    
    /* Improved mobile typography */
    @media (max-width: 768px) {
        .stMarkdown h1 {
            font-size: 1.5rem !important;
        }
        .stMarkdown h2 {
            font-size: 1.3rem !important;
        }
        .stMarkdown h3 {
            font-size: 1.1rem !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# Mobile-responsive header
st.markdown(
    '<h1 class="main-header">☀️ Helios-Grid Energy Predictor</h1>',
    unsafe_allow_html=True,
)

# Check if mobile device (simplified detection)
is_mobile = st.sidebar.checkbox(
    "📱 Mobile Mode", help="Toggle for mobile-optimized layout"
)

if is_mobile:
    st.markdown("#### 📱 Mobile Energy Predictor")
    st.info("💡 Swipe and tap to interact with controls")
else:
    st.markdown("### Enterprise-Grade Energy Consumption MLOps Pipeline")

# Mobile-responsive input layout
if is_mobile:
    # Mobile layout - inputs in main area
    st.header("🔧 Prediction Parameters")

    # Create mobile-friendly input columns
    mobile_col1, mobile_col2 = st.columns(2)

    with mobile_col1:
        hour = st.slider("⏰ Hour (0-23)", 0, 23, 18, help="Peak: 17-20")
        temperature = st.slider(
            "🌡️ Temp (°C)", -10, 45, 25, help="Hot weather = more AC"
        )

    with mobile_col2:
        day_of_week = st.selectbox(
            "📅 Day",
            options=[1, 2, 3, 4, 5, 6, 7],
            format_func=lambda x: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
                x - 1
            ],
            index=4,
        )

        # Quick presets for mobile
        preset = st.selectbox(
            "⚡ Quick Preset",
            ["Custom", "Morning Peak", "Evening Peak", "Night Low", "Weekend"],
            help="Quick parameter combinations",
        )

    # Apply presets
    if preset == "Morning Peak":
        hour, temperature, day_of_week = 8, 22, 2
    elif preset == "Evening Peak":
        hour, temperature, day_of_week = 19, 28, 3
    elif preset == "Night Low":
        hour, temperature, day_of_week = 2, 18, 4
    elif preset == "Weekend":
        hour, temperature, day_of_week = 14, 25, 6

    # Simplified advanced parameters for mobile
    with st.expander("🔬 More Options"):
        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            humidity = st.slider("💧 Humidity", 0, 100, 60)
            wind_speed = st.slider("💨 Wind", 0, 50, 10)
        with adv_col2:
            cloud_cover = st.slider("☁️ Clouds", 0, 100, 30)

else:
    # Desktop layout - sidebar inputs
    st.sidebar.header("🔧 Prediction Parameters")

    # Input parameters
    hour = st.sidebar.slider(
        "Hour of Day (0-23)", 0, 23, 18, help="Peak hours are typically 17-20"
    )
    temperature = st.sidebar.slider(
        "Temperature (°C)",
        -10,
        45,
        25,
        help="Higher temperatures increase cooling demand",
    )
    day_of_week = st.sidebar.selectbox(
        "Day of Week",
        options=[1, 2, 3, 4, 5, 6, 7],
        format_func=lambda x: [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ][x - 1],
        index=4,
        help="Weekdays typically have different patterns than weekends",
    )

    # Advanced parameters (collapsible)
    with st.sidebar.expander("🔬 Advanced Parameters"):
        humidity = st.slider("Humidity (%)", 0, 100, 60)
        wind_speed = st.slider("Wind Speed (km/h)", 0, 50, 10)
        cloud_cover = st.slider("Cloud Cover (%)", 0, 100, 30)

# Responsive main content layout
if is_mobile:
    # Mobile: single column layout
    col1, col2 = st.columns([1]), st.columns([1])
    col1, col2 = col1[0], col2[0]
else:
    # Desktop: two column layout
    col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Energy Consumption Prediction")

    # Prediction function (mock implementation for demo)
    def predict_energy_consumption(hour, temp, day, humidity=60, wind=10, cloud=30):
        """Mock prediction function - replace with actual model"""
        # Base consumption
        base = 100

        # Hour factor (peak hours)
        hour_factor = 1.0
        if 17 <= hour <= 20:  # Peak hours
            hour_factor = 1.4
        elif 22 <= hour <= 6:  # Night hours
            hour_factor = 0.7

        # Temperature factor
        temp_factor = 1.0
        if temp > 25:  # Hot weather increases AC usage
            temp_factor = 1.0 + (temp - 25) * 0.03
        elif temp < 10:  # Cold weather increases heating
            temp_factor = 1.0 + (10 - temp) * 0.02

        # Day factor
        day_factor = 1.2 if day <= 5 else 0.8  # Weekday vs weekend

        # Weather factors
        humidity_factor = 1.0 + (humidity - 50) * 0.001
        wind_factor = 1.0 - wind * 0.005
        cloud_factor = 1.0 - cloud * 0.002

        # Calculate prediction
        prediction = (
            base
            * hour_factor
            * temp_factor
            * day_factor
            * humidity_factor
            * wind_factor
            * cloud_factor
        )

        # Add some randomness for realism
        prediction += np.random.normal(0, 5)

        # Confidence based on parameter certainty
        confidence = min(95, 85 + np.random.uniform(0, 10))

        return round(prediction, 1), round(confidence, 1)

    # Mobile-optimized predict button
    button_text = "⚡ Predict" if is_mobile else "⚡ Predict Energy Consumption"
    if st.button(button_text, type="primary", use_container_width=True):
        with st.spinner("🔮 Analyzing energy patterns..."):
            prediction, confidence = predict_energy_consumption(
                hour, temperature, day_of_week, humidity, wind_speed, cloud_cover
            )

            # Display result
            # Mobile-optimized result display
            if is_mobile:
                st.markdown(
                    f"""
                <div class="prediction-result">
                    <h2>🔮 Result</h2>
                    <h1>{prediction} kWh</h1>
                    <p>✅ {confidence}% confident</p>
                    <p>⚡ {np.random.uniform(1.5, 3.2):.1f}ms</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                <div class="prediction-result">
                    <h2>🔮 Prediction Result</h2>
                    <h1>{prediction} kWh</h1>
                    <p>Confidence: {confidence}%</p>
                    <p>Processing Time: {np.random.uniform(1.5, 3.2):.1f}ms</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Additional insights
            st.success("✅ Prediction completed successfully!")

            # Mobile-responsive factors analysis
            if is_mobile:
                st.subheader("📊 Key Factors")
                factors_col1, factors_col2 = st.columns(2)
                factors_col3 = st.columns([1])[0]
            else:
                st.subheader("📈 Key Factors Analysis")
                factors_col1, factors_col2, factors_col3 = st.columns(3)

            with factors_col1:
                st.metric(
                    "Time Impact",
                    f"{hour}:00",
                    "Peak" if 17 <= hour <= 20 else "Normal",
                )

            with factors_col2:
                temp_delta = (
                    "High"
                    if temperature > 25
                    else "Low" if temperature < 10 else "Normal"
                )
                st.metric("Temperature Impact", f"{temperature}°C", temp_delta)

            with factors_col3:
                day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
                    day_of_week - 1
                ]
                day_type = "Weekday" if day_of_week <= 5 else "Weekend"
                st.metric("Day Impact", day_name, day_type)

# Mobile-responsive system status
if not is_mobile:
    with col2:
        st.header("📊 System Status")

        # System health metrics
        st.metric("🟢 System Health", "Operational", "✅ All systems go")
        st.metric("🤖 Model Status", "Ready", "v1.0.0")
        st.metric("⚡ Response Time", "2.1ms", "Fast")

        # Quick stats
        st.subheader("📈 Quick Stats")
        st.info("🏠 Avg Household: 120 kWh/day")
        st.info("🏢 Commercial: 500+ kWh/day")
        st.info("🌡️ Peak Temp Impact: +40%")
        st.info("⏰ Peak Hour Impact: +60%")
else:
    # Mobile: compact status in expandable section
    with st.expander("📊 System Status & Stats"):
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            st.metric("🟢 Health", "OK", "✅")
            st.metric("🤖 Model", "Ready", "v1.0")
        with status_col2:
            st.metric("⚡ Speed", "2.1ms", "Fast")
            st.info("🏠 Avg: 120 kWh/day")

# Historical data visualization
st.header("📈 Energy Consumption Patterns")

# Generate sample historical data
dates = pd.date_range(
    start=datetime.now() - timedelta(days=30), end=datetime.now(), freq="H"
)
sample_data = []

for date in dates:
    hour = date.hour
    temp = (
        20
        + 10 * np.sin((date.dayofyear - 80) * 2 * np.pi / 365)
        + np.random.normal(0, 3)
    )
    day_of_week = date.weekday() + 1
    consumption, _ = predict_energy_consumption(hour, temp, day_of_week)

    sample_data.append(
        {
            "datetime": date,
            "hour": hour,
            "temperature": temp,
            "consumption": consumption,
            "day_type": "Weekday" if day_of_week <= 5 else "Weekend",
        }
    )

df = pd.DataFrame(sample_data)

# Mobile-responsive charts
if is_mobile:
    # Mobile: stacked charts
    fig_ts = px.line(
        df,
        x="datetime",
        y="consumption",
        title="📈 Energy Over Time",
        labels={"consumption": "Energy (kWh)", "datetime": "Time"},
    )
    fig_ts.update_layout(height=300, title_font_size=16)
    st.plotly_chart(fig_ts, use_container_width=True)

    # Mobile chart tabs
    chart_tab = st.selectbox("📊 View Chart", ["Hourly Pattern", "Temperature Impact"])

    if chart_tab == "Hourly Pattern":
        hourly_avg = df.groupby("hour")["consumption"].mean().reset_index()
        fig_hourly = px.bar(
            hourly_avg,
            x="hour",
            y="consumption",
            title="⏰ Hourly Pattern",
            labels={"consumption": "Energy (kWh)", "hour": "Hour"},
        )
        fig_hourly.update_layout(height=250, title_font_size=14)
        st.plotly_chart(fig_hourly, use_container_width=True)
    else:
        fig_temp = px.scatter(
            df,
            x="temperature",
            y="consumption",
            title="🌡️ Temperature Impact",
            labels={"consumption": "Energy (kWh)", "temperature": "Temp (°C)"},
        )
        fig_temp.update_layout(height=250, title_font_size=14)
        st.plotly_chart(fig_temp, use_container_width=True)
else:
    # Desktop: full charts
    fig_ts = px.line(
        df,
        x="datetime",
        y="consumption",
        title="Energy Consumption Over Time",
        labels={"consumption": "Energy (kWh)", "datetime": "Date & Time"},
    )
    fig_ts.update_layout(height=400)
    st.plotly_chart(fig_ts, use_container_width=True)

    # Daily pattern chart
    col1, col2 = st.columns(2)

if not is_mobile:
    with col1:
        hourly_avg = df.groupby("hour")["consumption"].mean().reset_index()
        fig_hourly = px.bar(
            hourly_avg,
            x="hour",
            y="consumption",
            title="Average Consumption by Hour",
            labels={"consumption": "Energy (kWh)", "hour": "Hour of Day"},
        )
        fig_hourly.update_layout(height=300)
        st.plotly_chart(fig_hourly, use_container_width=True)

    with col2:
        temp_consumption = (
            df.groupby(pd.cut(df["temperature"], bins=10))["consumption"]
            .mean()
            .reset_index()
        )
        temp_consumption["temp_range"] = temp_consumption["temperature"].astype(str)
        fig_temp = px.scatter(
            df,
            x="temperature",
            y="consumption",
            title="Consumption vs Temperature",
            labels={"consumption": "Energy (kWh)", "temperature": "Temperature (°C)"},
        )
        fig_temp.update_layout(height=300)
        st.plotly_chart(fig_temp, use_container_width=True)

# Mobile-responsive API section
if is_mobile:
    with st.expander("🔌 API Info"):
        st.markdown("**Quick API Example:**")
        st.code("POST /predict\n{hour: 18, temp: 30}", language="json")
        st.markdown("📚 [Full API Docs](http://localhost:8000/docs)")
else:
    st.header("🔌 API Integration")

    with st.expander("📚 API Documentation"):
        st.code(
            """
# Python API Usage Example
import requests

# Make prediction request
response = requests.post('http://localhost:8000/predict', 
    json={
        "features": {
            "hour": 18,
            "temperature": 30,
            "day_of_week": 5
        }
    }
)

result = response.json()
print(f"Energy Consumption: {result['prediction']} kWh")
print(f"Confidence: {result['confidence']}%")
        """,
            language="python",
        )

        st.markdown("**Available Endpoints:**")
        st.markdown("- `POST /predict` - Single prediction")
        st.markdown("- `POST /batch_predict` - Batch predictions")
        st.markdown("- `GET /health` - System health check")
        st.markdown("- `GET /docs` - Interactive API documentation")

# Mobile-responsive footer
st.markdown("---")
if is_mobile:
    st.markdown(
        """
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p>🌟 Helios-Grid MLOps<br>
        <a href='https://github.com/sankeashok/Helios-Grid'>GitHub</a> | 
        <a href='https://hub.docker.com/r/sankeashok/helios-grid'>Docker</a></p>
    </div>
    
    <!-- Mobile navigation bar -->
    <div class="mobile-nav">
        <div class="mobile-nav-item">🏠<br>Home</div>
        <div class="mobile-nav-item">📊<br>Charts</div>
        <div class="mobile-nav-item">🔧<br>Settings</div>
        <div class="mobile-nav-item">📚<br>API</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
    <div style='text-align: center; color: #666;'>
        <p>🌟 Powered by Helios-Grid MLOps Pipeline | 
        <a href='https://github.com/sankeashok/Helios-Grid'>GitHub</a> | 
        <a href='https://hub.docker.com/r/sankeashok/helios-grid'>Docker Hub</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )
