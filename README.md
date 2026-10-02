AI-Based Predictive System Health Monitoring and Failure Risk Analysis
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()
[![Code Style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-brightgreen.svg)]()
[![Tests: Pytest](https://img.shields.io/badge/tests-195%20passed-brightgreen.svg)]()
A Python-based system monitoring application that collects computer and server telemetry, analyzes resource behavior, detects unusual activity, and presents system health information through an interactive dashboard.
The application is designed for software-based monitoring of a local computer or server. It uses operating-system metrics and machine learning-based anomaly detection to help users understand resource utilization and identify unusual system behavior.
> **Scope note:** Anomaly detection and resource-based risk indicators do not establish that a hardware failure will occur. Reliable failure prediction requires representative, labeled failure-event data.
---
Features
System telemetry collection: Monitor CPU, memory, disk, network activity, and running processes.
Data validation and cleaning: Handle missing, invalid, and non-finite metric values.
Feature engineering: Transform telemetry into a structured set of 39 numerical features, including rolling statistics and changes between samples.
Historical storage: Persist system metrics, feature vectors, and validation records in SQLite.
Anomaly detection: Use an Isolation Forest model to identify telemetry patterns that differ from the observed baseline.
System health score: Calculate a transparent score from 0 to 100 using anomaly and resource-utilization penalties.
Risk categorization: Classify current system conditions into Normal, Low, Moderate, High, or Critical categories.
Interactive dashboard: Explore current metrics, health indicators, historical trends, anomaly records, and database information.
Live and background monitoring: Capture an individual snapshot or run periodic collection.
Model management: Save and load model artifacts with feature-schema validation and a heuristic fallback when a trained model is unavailable.
Automated tests: Validate core components, data persistence, machine learning behavior, dashboard services, and integration workflows.
---
Technology Stack
Area	Technology
Language	Python 3.12+
System metrics	`psutil`
Machine learning	`scikit-learn`
Data processing	`numpy`, `pandas`
Dashboard	`Streamlit`
Visualizations	`Plotly`
Database	SQLite
Model serialization	`joblib`
Configuration	`python-dotenv`
Testing	`pytest`
---
Application Architecture
The application is organized into modular components:
```text
AI-Based-Server-Health-Monitoring/
├── app/
│   ├── core/             # Configuration and logging
│   ├── models/           # Typed telemetry data models
│   ├── collectors/       # CPU, memory, disk, network, and process metrics
│   ├── preprocessing/    # Validation, cleaning, rolling statistics, features
│   ├── database/         # SQLite schema, migrations, and repositories
│   ├── ml/               # Anomaly detection, health scoring, risk analysis
│   ├── dashboard/        # Streamlit pages, charts, and dashboard services
│   └── utils/            # Shared utilities
├── data/                 # Local telemetry database and data directories
├── models/               # Saved machine learning model artifacts
├── logs/                 # Runtime logs
├── docs/                 # Architecture documentation
├── tests/                # Automated test suite
├── .env.example          # Example environment configuration
├── requirements.txt      # Python dependencies
├── run.py                # Application command-line entry point
└── README.md
```
Data Flow
```text
Host Operating System
        │
        ▼
Metric Collectors
        │
        ▼
Validation and Preprocessing
        │
        ▼
Feature Engineering (39 features)
        │
        ├──────────────► SQLite Historical Storage
        │
        ▼
Anomaly Detection and Health Analysis
        │
        ▼
Risk Categorization
        │
        ▼
Streamlit Dashboard / CLI Logs
```
---
Metrics and Analysis
Collected metrics
CPU: Overall utilization and core information.
Memory: Total, used, available memory, and utilization.
Disk: Total, used, and free storage, along with utilization.
Network: Bytes sent and received, plus throughput.
Processes: Process count and resource usage of top processes.
Feature engineering
The preprocessing pipeline creates a 39-dimensional feature vector. Features include current resource utilization, changes between samples, rolling-window statistics, process usage, time indicators, and flags for missing metric domains.
Machine learning and risk analysis
The application uses an Isolation Forest model to detect unusual telemetry patterns. Its anomaly score is scaled to the range `[0, 1]`. A separate health-score calculator produces a score from `0` to `100`, and the risk analyzer assigns an operational category.
These outputs describe observed system behavior and resource stress. They should not be interpreted as calibrated probabilities of future hardware failure.
---
Dashboard
The Streamlit dashboard provides the following views:
System Overview: Current system status and CPU, memory, disk, network, and process metrics.
Health & Risk Analysis: Health score, anomaly score, risk category, and score breakdown.
Real-Time Monitoring: On-demand snapshots and background monitoring controls.
Historical Telemetry: Charts of stored metrics over selectable time ranges.
Anomaly Audit Log: Historical anomaly scores and risk categories.
Database Inspection: Record counts, sample timestamps, database size, and recent records.
---
Requirements
Python 3.12 or newer
Windows (the current project setup is Windows-focused)
Git (optional, for cloning the repository)
---
Installation
Clone the repository:
```powershell
git clone https://github.com/andhony07/AI-Based-Server-Health-Monitoring.git
cd AI-Based-Server-Health-Monitoring
```
Create and activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Install dependencies:
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
Create a local environment file:
```powershell
Copy-Item .env.example .env
```
Edit `.env` if you need to change the default application settings.
---
Usage
Launch the dashboard
```powershell
python run.py --dashboard
```
Alternatively, run Streamlit directly:
```powershell
python -m streamlit run app/dashboard/dashboard_main.py
```
Open the local address shown in the terminal. By default, Streamlit uses:
```text
http://localhost:8501
```
Start continuous monitoring from the command line
```powershell
python run.py
```
Press `Ctrl+C` to stop the monitoring process.
Capture one telemetry snapshot
```powershell
python run.py --single-shot
```
Train the anomaly detection model
```powershell
python run.py --train
```
The training workflow uses historical feature vectors stored in SQLite. A sufficient number of samples is required before training can proceed.
Run the tests
```powershell
pytest
```
The current project test suite is reported as 195 passing tests. Run the command above to verify the tests in your local environment.
---
Data Storage
Telemetry is stored locally in SQLite, by default under:
```text
data/system_metrics.db
```
The database stores system metric snapshots, engineered feature vectors, and preprocessing validation records. The application uses transactions to keep related records consistent and supports retention cleanup.
The database is local to the machine running the application; it is not a distributed storage system.
To inspect the number of collected samples:
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/system_metrics.db'); print('Samples:', conn.execute('SELECT COUNT(*) FROM system_metrics').fetchone()[0]); conn.close()"
```
---
Machine Learning Scope and Limitations
Isolation Forest identifies telemetry that differs from the patterns represented in the training data.
Health score is a deterministic indicator based on anomaly and resource-utilization penalties.
Risk categories summarize current observed conditions using configured thresholds.
If a trained model is unavailable or historical data is insufficient, the application can use a clearly identified heuristic fallback.
The repository does not contain authentic, labeled hardware-failure events. Therefore, the current system does not establish a validated probability or time-to-failure estimate. A supervised failure-prediction model would require suitable labeled data, a defined prediction horizon, and evaluation that avoids temporal data leakage.
---
Testing and Validation
Run all tests with:
```powershell
pytest
```
The reported suite contains 195 tests covering configuration, metric collectors, preprocessing, database operations, machine learning, dashboard services, and integration behavior.
Tests help verify software behavior; they do not by themselves demonstrate predictive accuracy on real-world hardware failures.
---
Configuration
Application settings can be customized through the `.env` file. The provided `.env.example` includes settings for application metadata, logging, metric collection intervals, process limits, preprocessing, and database behavior.
Do not commit secrets or machine-specific sensitive information to the repository.
---
Future Improvements
Evaluate the system with longer-running telemetry collected across different workloads.
Add support for importing labeled failure-event datasets.
Develop and validate supervised failure prediction when suitable ground-truth data is available.
Add remote-host monitoring and centralized storage if multi-machine monitoring is required.
Improve alert delivery and configurable notification thresholds.
---
License
Add a license file and update this section if you intend to distribute the project under a specific open-source license.
