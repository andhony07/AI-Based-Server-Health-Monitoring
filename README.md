# AI-Based Predictive System Health Monitoring and Failure Risk Analysis

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Code Style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-brightgreen.svg)
![Tests: Pytest](https://img.shields.io/badge/tests-237%20passed-brightgreen.svg)

A Python-based system monitoring application that collects computer and server telemetry, analyzes resource behavior, detects unusual activity, and presents system health information through an interactive Streamlit dashboard.

The application is designed for software-based monitoring of a local computer or server. It combines operating-system metrics, feature engineering, machine learning-based anomaly detection, health scoring, and risk categorization.

> **Scope note:** Anomaly detection and resource-based risk indicators describe observed system behavior. They do not establish a validated probability that a hardware or operating-system failure will occur. Reliable failure prediction requires representative, labeled failure-event data.

## Features

- **System telemetry collection:** Monitor CPU, memory, disk, network activity, and running processes.
- **Data validation and cleaning:** Handle missing, invalid, and non-finite metric values.
- **Feature engineering:** Transform telemetry into numerical features, including rolling statistics and changes between samples.
- **Historical storage:** Persist system metrics, feature vectors, and validation records in SQLite.
- **Anomaly detection:** Use an Isolation Forest model to identify telemetry patterns that differ from the observed baseline.
- **System health score:** Calculate a score from 0 to 100 using anomaly and resource-utilization penalties.
- **Risk categorization:** Classify current system conditions into Normal, Low, Moderate, High, or Critical categories.
- **Interactive dashboard:** Explore current metrics, health indicators, historical trends, anomaly records, and database information.
- **Live and background monitoring:** Capture an individual snapshot or run periodic collection.
- **Safe anomaly simulation:** Generate synthetic scenarios for CPU spikes, memory pressure, disk saturation, network saturation, combined resource pressure, and normal baseline behavior.
- **Explainable diagnostics:** Display evidence-based diagnostic suggestions associated with observed metrics and scenarios.
- **Operational status:** Inspect component states, worker activity, and telemetry freshness.
- **CSV exports:** Export supported monitoring and diagnostic data for further analysis.
- **Model management:** Save and load model artifacts with feature-schema validation and a heuristic fallback when implemented.
- **Automated testing:** Test core components, persistence, machine learning, dashboard services, simulation, diagnostics, operational status, and CSV exports.

## 1. Project Overview

**AI-Based Predictive System Health Monitoring and Failure Risk Analysis** is an academic software platform designed to observe computer and server operational telemetry, identify behavioral anomalies, and present resource-based health and risk indicators.

The application collects host operating-system metrics such as CPU, RAM, disk, network, and process information. It processes the measurements, derives features, evaluates unusual behavior using machine learning where available, and presents the results through a Streamlit dashboard.

The project includes deterministic simulation scenarios to demonstrate how the application handles different resource-pressure patterns without intentionally creating real CPU, memory, or disk stress on the host.

## 2. Technology Stack

| Area                 | Technology        |
| -------------------- | ----------------- |
| Programming language | Python 3.12+      |
| System metrics       | `psutil`          |
| Machine learning     | `scikit-learn`    |
| Data processing      | `numpy`, `pandas` |
| Dashboard            | `Streamlit`       |
| Visualizations       | `Plotly`          |
| Database             | SQLite            |
| Model serialization  | `joblib`          |
| Configuration        | `python-dotenv`   |
| Testing              | `pytest`          |

## 3. Application Architecture

The application is organized into modular components.

```text
AI-Based-Server-Health-Monitoring/
├── app/
│   ├── core/             # Configuration and logging
│   ├── models/           # Typed telemetry data models
│   ├── collectors/       # CPU, memory, disk, network, and process metrics
│   ├── preprocessing/    # Validation, cleaning, rolling statistics, features
│   ├── database/         # SQLite schema, migrations, and repositories
│   ├── ml/               # Anomaly detection, simulation, diagnostics
│   ├── dashboard/        # Streamlit pages, charts, components, and services
│   └── utils/            # Shared utilities
├── data/                 # Local telemetry database and data directories
├── models/               # Saved machine learning model artifacts
├── logs/                 # Runtime logs
├── docs/                 # Documentation and review rehearsal guide
├── tests/                # Automated test suite
├── .env.example          # Example environment configuration
├── requirements.txt      # Python dependencies
├── run.py                # Application command-line entry point
└── README.md
```

### Data flow

```text
Host Operating System
        |
        v
Metric Collectors
        |
        v
Validation and Preprocessing
        |
        v
Feature Engineering
        |
        +--------------------> SQLite Historical Storage
        |
        v
Anomaly Detection and Health Analysis
        |
        v
Risk Categorization and Diagnostics
        |
        v
Streamlit Dashboard and CSV Exports
```

## 4. Metrics and Analysis

### Collected metrics

- **CPU:** Overall utilization and core information.
- **Memory:** Total, used, available memory, and utilization.
- **Disk:** Total, used, and free storage, along with utilization.
- **Network:** Bytes sent and received, plus throughput.
- **Processes:** Process count and resource usage of top processes.

### Feature engineering

The preprocessing pipeline creates a numerical feature vector. Features include current resource utilization, changes between samples, rolling-window statistics, process usage, time indicators, and flags for missing metric domains.

The exact feature schema is defined by the implementation and must remain consistent with the model artifacts.

### Machine learning and risk analysis

The application uses an Isolation Forest model to identify telemetry that differs from patterns represented in the training data. Its anomaly score is presented separately from the health score and risk category.

The health score is a deterministic indicator based on configured anomaly and resource-utilization penalties. Risk categories summarize current observed conditions using configured thresholds.

These outputs indicate observed system behavior. They are **not calibrated probabilities of future failure**.

## 5. Simulation and Diagnostics

The dashboard includes deterministic synthetic scenarios intended for demonstrations and regression testing. Available scenarios may include:

- CPU spike
- Memory leak or memory pressure
- Disk saturation
- Network saturation
- Combined resource pressure
- Normal baseline

The simulation produces synthetic telemetry for the application's analysis pipeline. It does not intentionally exhaust real host resources or inject operating-system faults.

Diagnostic recommendations are based on available metric evidence and scenario context. They are troubleshooting guidance, not proof of a root cause.

## 6. Dashboard

The Streamlit dashboard provides the following views:

- **System Overview:** Current system status and CPU, memory, disk, network, and process metrics.
- **Health & Risk Analysis:** Health score, anomaly score, risk category, and score breakdown.
- **Real-Time Monitoring:** On-demand snapshots and background monitoring controls.
- **Historical Telemetry:** Charts of stored metrics over selectable time ranges.
- **Anomaly Audit Log:** Historical anomaly scores and risk categories.
- **Simulation and Diagnostics:** Run synthetic scenarios and inspect diagnostic evidence and recommendations.
- **Operational Status:** Inspect component status, worker state, and telemetry freshness where available.
- **CSV Export:** Download supported records for offline analysis.
- **Database Inspection:** Record counts, sample timestamps, database size, and recent records.

Displayed status and freshness depend on collector and worker activity. An idle worker or stale telemetry may indicate that monitoring has not recently collected a sample.

## 7. Requirements

- Python 3.12 or newer
- Windows (the current project setup is Windows-focused)
- Git (optional, for cloning the repository)

## 8. Installation

### Step 1: Clone the repository

```powershell
git clone https://github.com/andhony07/AI-Based-Server-Health-Monitoring.git
cd AI-Based-Server-Health-Monitoring
```

### Step 2: Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Create a local environment file

```powershell
Copy-Item .env.example .env
```

Edit `.env` if you need to change the default application settings. Do not add secrets or machine-specific sensitive information to version control.

## 9. Usage

### Launch the Streamlit dashboard

From the project root, run:

```powershell
python -m streamlit run app/dashboard/dashboard_main.py
```

Open the local URL shown in the terminal. Streamlit commonly uses:

```text
http://localhost:8501
```

### Alternative dashboard entry point

If supported by the current `run.py` configuration, the dashboard can also be launched with:

```powershell
python run.py --dashboard
```

### Start continuous monitoring from the command line

```powershell
python run.py
```

Press `Ctrl+C` to stop the monitoring process.

### Capture one telemetry snapshot

```powershell
python run.py --single-shot
```

### Train the anomaly detection model

```powershell
python run.py --train
```

The training workflow uses historical feature vectors stored in SQLite. A sufficient number of valid samples is required before training can proceed.

### Run the tests

```powershell
pytest
```

The latest reported test run completed with **237 passed tests**. Run the command above to verify the current repository state. The test count may change as tests are added or modified.

## 10. Data Storage

Telemetry is stored locally in SQLite, by default under:

```text
data/system_metrics.db
```

The database stores system metric snapshots, engineered feature vectors, and preprocessing validation records. The application uses transactions to keep related records consistent and supports retention cleanup.

The database is local to the machine running the application; it is not a distributed storage system.

To inspect the number of collected samples, if the database schema contains the `system_metrics` table, run:

```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/system_metrics.db'); print('Samples:', conn.execute('SELECT COUNT(*) FROM system_metrics').fetchone()[0]); conn.close()"
```

## 11. Machine Learning Scope and Limitations

- Isolation Forest identifies telemetry that differs from patterns represented in the training data.
- The health score is a deterministic indicator based on anomaly and resource-utilization penalties.
- Risk categories summarize current observed conditions using configured thresholds.
- If a trained model is unavailable or historical data is insufficient, the application may use a heuristic fallback where implemented.
- Synthetic simulation scenarios are useful for demonstrations and software testing but do not represent authentic hardware-failure events.
- The project does not establish a validated probability or time-to-failure estimate from labeled real-world failures.

A supervised failure-prediction model would require suitable labeled data, a defined prediction horizon, and evaluation that avoids temporal data leakage. Its performance would need to be evaluated on representative data that was not used for training.

## 12. Testing and Validation

Run the complete test suite from the project root:

```powershell
pytest
```

The latest reported run completed with **237 passing tests**. The suite includes tests for configuration, metric collectors, preprocessing, database operations, machine learning, dashboard services, simulation, diagnostics, operational status, CSV export, and integration behavior.

Tests help verify software behavior. They do not, by themselves, demonstrate predictive accuracy on real-world hardware failures or guarantee production readiness.

## 13. Configuration

Application settings can be customized through the `.env` file. The provided `.env.example` includes settings for application metadata, logging, metric collection intervals, process limits, preprocessing, and database behavior.

Do not commit secrets or machine-specific sensitive information to the repository.

## 14. Future Improvements

- Evaluate the system with longer-running telemetry collected across different workloads.
- Add support for importing labeled failure-event datasets.
- Develop and validate supervised failure prediction when suitable ground-truth data is available.
- Add remote-host monitoring and centralized storage if multi-machine monitoring is required.
- Improve alert delivery and configurable notification thresholds.
- Add further operational monitoring and end-to-end tests for supported deployment environments.
