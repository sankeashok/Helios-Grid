# 📊 Dataset Documentation

## 🔌 **Hourly Energy Consumption Dataset**

### **📋 Dataset Overview**

**Source**: [Hourly Energy Consumption Dataset](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption/data)  
**Author**: [@robikscube](https://www.kaggle.com/robikscube) on Kaggle  
**Original Data Provider**: PJM Interconnection LLC  
**License**: [Dataset License on Kaggle](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption/data)

### **🎯 Dataset Description**

This dataset contains **10+ years of hourly energy consumption data** from PJM Interconnection LLC, one of the largest power grid operators in North America. The data covers multiple regions and provides comprehensive insights into energy consumption patterns across different time periods, seasons, and geographical areas.

### **📈 Key Statistics**

| Metric | Value |
|--------|-------|
| **Time Range** | 2002-2018 (16+ years) |
| **Frequency** | Hourly |
| **Total Records** | ~145,000 rows |
| **Regions Covered** | 10+ PJM regions |
| **File Size** | ~15 MB |
| **Format** | CSV |

### **🗂️ Data Structure**

#### **Columns Description**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| **Datetime** | datetime | Timestamp (hourly) | 2004-12-31 01:00:00 |
| **AEP_MW** | float | AEP energy consumption (MW) | 13478.0 |
| **COMED_MW** | float | ComEd energy consumption (MW) | 15572.0 |
| **DAYTON_MW** | float | Dayton energy consumption (MW) | 2277.0 |
| **DEOK_MW** | float | DEOK energy consumption (MW) | 1513.0 |
| **DOM_MW** | float | Dominion energy consumption (MW) | 4781.0 |
| **DUQ_MW** | float | Duquesne energy consumption (MW) | 2354.0 |
| **EKPC_MW** | float | EKPC energy consumption (MW) | 1776.0 |
| **FE_MW** | float | FirstEnergy energy consumption (MW) | 6634.0 |
| **NI_MW** | float | Northern Indiana energy consumption (MW) | 1932.0 |
| **PJME_MW** | float | PJM East energy consumption (MW) | 26498.0 |
| **PJMW_MW** | float | PJM West energy consumption (MW) | 21865.0 |
| **PJM_Load_MW** | float | Total PJM load (MW) | 32845.0 |

#### **Regional Coverage**

The dataset includes energy consumption data from these major regions:

1. **AEP** - American Electric Power
2. **ComEd** - Commonwealth Edison (Chicago area)
3. **Dayton** - Dayton Power & Light
4. **DEOK** - Duke Energy Ohio/Kentucky
5. **DOM** - Dominion Virginia Power
6. **DUQ** - Duquesne Light Company
7. **EKPC** - East Kentucky Power Cooperative
8. **FE** - FirstEnergy
9. **NI** - Northern Indiana Public Service Company
10. **PJM East/West** - Regional aggregations

### **📊 Data Quality Assessment**

#### **Completeness**
- **Missing Values**: < 0.1% across all columns
- **Data Gaps**: Minimal gaps, mostly during maintenance periods
- **Consistency**: High temporal consistency with hourly intervals

#### **Data Patterns**
- **Seasonal Trends**: Clear summer/winter consumption peaks
- **Daily Patterns**: Business hours vs. residential consumption
- **Weekly Cycles**: Weekday vs. weekend consumption differences
- **Holiday Effects**: Reduced consumption during major holidays

### **🔄 Data Processing Pipeline**

#### **1. Data Ingestion**
```python
import kagglehub

# Download dataset using Kaggle API
path = kagglehub.dataset_download("robikscube/hourly-energy-consumption")
df = pd.read_csv(f"{path}/pjm_hourly_est.csv")
```

#### **2. Data Cleaning**
- **Datetime Parsing**: Convert to proper datetime format
- **Missing Value Handling**: Forward fill for short gaps, interpolation for longer gaps
- **Outlier Detection**: Statistical outlier identification and treatment
- **Data Validation**: Range checks and consistency validation

#### **3. Feature Engineering**
- **Temporal Features**: Hour, day, month, season, year
- **Cyclical Encoding**: Sin/cos transformation for periodic features
- **Lag Features**: Historical consumption values (1h, 24h, 168h)
- **Rolling Statistics**: Moving averages and standard deviations
- **Weather Proxies**: Temperature estimation from consumption patterns

### **📈 Usage in Helios-Grid**

#### **Primary Use Cases**
1. **Energy Demand Forecasting**: Predict future consumption patterns
2. **Peak Load Prediction**: Identify high-demand periods
3. **Grid Optimization**: Optimize energy distribution and storage
4. **Anomaly Detection**: Identify unusual consumption patterns

#### **Model Training**
- **Target Variable**: Total PJM load (PJM_Load_MW)
- **Features**: Temporal features + lag variables + regional data
- **Validation**: Time series cross-validation (2016-2018 as test set)
- **Metrics**: RMSE, MAE, MAPE for energy forecasting accuracy

### **🎯 Business Value**

#### **Energy Industry Applications**
- **Grid Management**: Optimize power generation and distribution
- **Capacity Planning**: Plan infrastructure investments
- **Demand Response**: Implement dynamic pricing strategies
- **Renewable Integration**: Balance renewable energy with demand

#### **Predictive Insights**
- **Peak Demand Forecasting**: Predict high-consumption periods
- **Seasonal Planning**: Prepare for seasonal demand variations
- **Regional Analysis**: Understand regional consumption patterns
- **Economic Impact**: Correlate energy consumption with economic activity

### **📚 Data Citation**

When using this dataset, please cite:

```
@dataset{robikscube2018hourly,
  title={Hourly Energy Consumption Dataset},
  author={Rob Mulla (@robikscube)},
  year={2018},
  publisher={Kaggle},
  url={https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption/data}
}
```

### **🔗 Related Resources**

- **Original Dataset**: [Kaggle Dataset Page](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption/data)
- **PJM Interconnection**: [Official Website](https://www.pjm.com/)
- **Data Analysis Notebooks**: [Kaggle Kernels](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption/kernels)
- **Energy Forecasting Research**: [IEEE Papers on Energy Forecasting](https://ieeexplore.ieee.org/)

### **⚠️ Important Notes**

1. **Data Licensing**: Ensure compliance with Kaggle's dataset license
2. **Commercial Use**: Check PJM's data usage policies for commercial applications
3. **Data Privacy**: No personal information included - aggregated grid data only
4. **Update Frequency**: Historical dataset - not real-time data
5. **Regional Scope**: Limited to PJM regions - may not represent global patterns

---

**Last Updated**: January 2025  
**Dataset Version**: Latest available on Kaggle  
**Helios-Grid Integration**: v1.0.0