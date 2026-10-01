# AI-Based Predictive System Health Monitoring and Failure Risk Analysis

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20(planned)-lightgrey.svg)]()
[![Code Style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-brightgreen.svg)]()
[![Tests: Pytest](https://img.shields.io/badge/tests-195%20passed-brightgreen.svg)]()

---

## 1. Project Overview

**AI-Based Predictive System Health Monitoring and Failure Risk Analysis** is an academic software platform engineered to continuously observe computer and server operational telemetry, identify behavioral anomalies, and forecast potential hardware or operating system failure risks using machine learning algorithms.

Modern server reliability requires proactive risk estimation rather than passive error reaction. This application establishes a decoupled, modular foundation that ingests host operating system metrics (CPU, RAM, Disk, Network, Process table), processes time-series operational patterns, flags statistical and ML anomalies, and projects potential failure probabilities via a rich, real-time web dashboard.

> [!NOTE]
> **Important Milestone Notice**: Phase 7 (System Testing, Validation & Finalization) is fully implemented. The complete test suite contains **195 passing tests** across 30 test modules covering live hardware telemetry, 39-feature engineering, SQLite persistence (PRAGMA integrity verified), Isolation Forest anomaly detection, health scoring, all 6 dashboard views, and end-to-end integration workflows.

---

## 2. Project Objectives

1. **Continuous Telemetry Observation**: Collect high-resolution, low-overhead hardware and OS operational metrics from the host computer.
2. **Data Cleaning & Standardization**: Sanitize raw telemetry, handle missing metrics, clamp out-of-range readings, and prevent non-finite values from reaching ML models.
3. **Feature Engineering**: Compute rate-of-change indicators, moving window statistics, and temporal signals into fixed-dimension numerical feature vectors.
4. **Historical Analytics**: Maintain local, lightweight, atomic time-series metric persistence using SQLite (Phase 4).
5. **Anomaly Detection & Risk Scoring**: Detect subtle non-linear degradation and evaluate risk using unsupervised/supervised ML models (Phase 5).
6. **Interactive Operator Dashboard**: Provide visualization gauges, telemetry charts, and alert dashboards using Streamlit and Plotly (Phase 6).

---

## 3. Technology Stack

* **Programming Language**: Python 3.12+
* **System Telemetry**: `psutil` (hardware, OS, and process performance probes)
* **Machine Learning & Analytics**: `scikit-learn`, `numpy`, `pandas` (anomaly detection and risk modeling)
* **Interactive Dashboard**: `streamlit` (rapid web application UI)
* **Visualization Engine**: `plotly` (interactive dynamic charts, gauges, and heatmaps)
* **Database & Storage**: `sqlite3` (built-in relational time-series database with WAL mode and foreign key cascades)
* **Configuration & Environment**: `python-dotenv` and Python standard `dataclasses`
* **Logging System**: Python standard `logging` (simultaneous console and rotating file output)
* **Testing Framework**: `pytest` (automated unit and integration test suites)

---

## 4. Project Directory Structure

```text
AI-Predictive-System-Health-Monitoring/
│
├── app/                              # Core application source code
│   ├── __init__.py                   # Package metadata and version info
│   ├── main.py                       # Application lifecycle, periodic monitoring loop, and persistence integration
│   │
│   ├── core/                         # Foundational application infrastructure (Phase 1)
│   │   ├── __init__.py               # Exports Settings, get_settings, setup_logging
│   │   ├── config.py                 # Centralized, immutable configuration management (with DB settings)
│   │   └── logging_config.py         # Structured console and file logging setup
│   │
│   ├── models/                       # Telemetry data models (Phase 2)
│   │   ├── __init__.py               # Exports all metric dataclasses
│   │   └── metrics.py                # CPUMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics, ProcessMetrics, SystemMetrics
│   │
│   ├── collectors/                   # Telemetry metric collection engines (Phase 2)
│   │   ├── __init__.py               # Package exports for all collectors
│   │   ├── base.py                   # BaseCollector abstract base class
│   │   ├── cpu_collector.py          # Real-time CPU utilization & core counters
│   │   ├── memory_collector.py       # Virtual memory (RAM) utilization & capacities
│   │   ├── disk_collector.py         # Partition capacity & storage utilization
│   │   ├── network_collector.py      # Network I/O counters & throughput calculation
│   │   ├── process_collector.py      # Top resource-consuming process table monitor
│   │   └── system_collector.py       # Orchestrator with failure isolation & periodic loop
│   │
│   ├── preprocessing/                # Feature engineering & data cleaning (Phase 3)
│   │   ├── __init__.py               # Package exports for preprocessing modules
│   │   ├── validator.py              # Range, type, timestamp, and NaN/inf validation
│   │   ├── cleaner.py                # Imputation, percentage clamping, quality indicators
│   │   ├── rolling.py                # Bounded rolling circular buffer & window statistics
│   │   ├── feature_engineer.py       # 39-dimension numerical feature vector generator
│   │   └── pipeline.py               # PreprocessingPipeline coordinator
│   │
│   ├── database/                     # SQLite persistence & data repositories (Phase 4)
│   │   ├── __init__.py               # Package exports for database subsystem
│   │   ├── connection.py             # WAL mode, foreign key enforcement, busy timeout, and transactions
│   │   ├── schema.py                 # Normalized table DDLs, column definitions, and indexes
│   │   ├── migrations.py             # Idempotent schema migration and version tracking
│   │   ├── models.py                 # Typed database records (SystemMetricRecord, FeatureVectorRecord, etc.)
│   │   ├── repository.py             # Parameterized SQL queries, CRUD, time-range, and retention methods
│   │   └── service.py                # PersistenceService orchestrating atomic multi-table transactions
│   │
│   ├── ml/                           # ML models & failure risk estimators (Phase 5)
│   │   ├── __init__.py               # Exports IsolationForestDetector, HealthScoreCalculator, etc.
│   │   ├── models.py                 # AnomalyResult, HealthScoreResult, PredictionResult, RiskCategory
│   │   ├── feature_schema.py         # 39-feature schema validation, ordering, and matrix conversions
│   │   ├── data_loader.py            # Historical feature vector loading from SQLite
│   │   ├── anomaly_detector.py       # Isolation Forest wrapper with calibrated [0, 1] anomaly scores
│   │   ├── health_score.py           # Transparent 0-100 system health score with resource penalties
│   │   ├── risk_analyzer.py          # Multi-tier risk categorization (Normal, Low, Moderate, High, Critical)
│   │   ├── model_manager.py          # Atomic model persistence via joblib and JSON metadata validation
│   │   ├── supervised.py             # Supervised failure classification extension point & requirements
│   │   ├── prediction_service.py     # Inference coordinator with heuristic fallback & hot-reload
│   │   └── training.py               # Model training workflow and CLI runner
│   │
│   ├── dashboard/                    # Streamlit & Plotly UI visualization (Phase 6)
│   │   ├── __init__.py               # Exports DashboardService
│   │   ├── app.py                    # Streamlit web application entry point
│   │   ├── components/               # Status header, metric cards, health cards
│   │   ├── charts/                   # Plotly gauges, time-series, and scatter builders
│   │   ├── services/                 # DashboardService data access and coordinator
│   │   └── utils/                    # Presentation and formatting helpers
│   │
│   └── utils/                        # Shared cross-cutting utility functions
│       └── __init__.py               # Module description and interface definitions
│
├── tests/                            # Automated test suite (161 tests, 100% passing)
│   ├── test_config.py                # Configuration and logging test suite (21 tests)
│   ├── test_cpu_collector.py         # CPU collector tests (unit & live) (3 tests)
│   ├── test_memory_collector.py      # Memory collector tests (unit & live) (3 tests)
│   ├── test_disk_collector.py        # Disk collector tests (unit & live) (4 tests)
│   ├── test_network_collector.py     # Network throughput and counter tests (5 tests)
│   ├── test_process_collector.py     # Process monitoring and exception tests (4 tests)
│   ├── test_system_collector.py      # System coordinator and periodic loop tests (6 tests)
│   ├── test_preprocessing_validator.py # Metrics validation test suite (6 tests)
│   ├── test_preprocessing_cleaner.py # Cleaning, clamping, imputation tests (4 tests)
│   ├── test_preprocessing_rolling.py # Rolling buffer, deltas, and gap tests (6 tests)
│   ├── test_preprocessing_feature_engineer.py # Feature extraction tests (3 tests)
│   ├── test_preprocessing_pipeline.py # End-to-end pipeline & live tests (4 tests)
│   ├── test_database_connection.py   # Connection PRAGMAs, WAL, transactions, rollbacks (6 tests)
│   ├── test_database_schema.py       # DDL, 39 features, FK constraints, idempotency (5 tests)
│   ├── test_database_repository.py   # CRUD, range queries, counts, retention purges (7 tests)
│   ├── test_database_service.py      # Service orchestration, rollbacks, retention (5 tests)
│   ├── test_database_integration.py  # End-to-end collector -> pipeline -> DB (3 tests)
│   ├── test_ml_feature_schema.py     # 39-feature schema, ordering, NaN/inf validation (8 tests)
│   ├── test_ml_anomaly_detector.py   # Isolation Forest fit, score calibration, determinism (9 tests)
│   ├── test_ml_health_score.py       # Health score bounds [0, 100], penalties, clamping (7 tests)
│   ├── test_ml_risk_analyzer.py      # Risk categories, threshold configs, explanations (4 tests)
│   ├── test_ml_model_manager.py      # Model persistence, metadata, corruption/drift rejection (6 tests)
│   ├── test_ml_data_loader.py        # SQLite historical vector retrieval & sample minimums (5 tests)
│   ├── test_ml_supervised.py         # Ground-truth label inspection & classifier stub (3 tests)
│   ├── test_ml_prediction_service.py # Inference coordination, fallback, hot-reload (4 tests)
│   ├── test_ml_training.py           # Model training pipeline & baseline metrics (2 tests)
│   ├── test_dashboard_utils.py       # Formatting and presentation utility tests (6 tests)
│   ├── test_dashboard_charts.py      # Plotly chart builders and traces (5 tests)
│   └── test_dashboard_service.py     # Dashboard coordinator, lifecycle, and queries (7 tests)
│
├── data/                             # Data storage (git-ignored, kept via .gitkeep)
│   ├── raw/
│   │   └── .gitkeep
│   ├── processed/
│   │   └── .gitkeep
│   └── system_metrics.db             # Default SQLite database file (Phase 4)
│
├── models/                           # Persisted ML model checkpoints (Phase 5)
│   ├── .gitkeep
│   ├── isolation_forest.joblib       # Serialized Isolation Forest model
│   └── isolation_forest_metadata.json# Companion schema and training metadata
│
├── logs/                             # Application runtime log files
│   ├── .gitkeep
│   └── system_monitor.log
│
├── docs/                             # Technical architecture and design docs
│   └── architecture.md               # Detailed module specifications & data flow
│
├── .env.example                      # Template for local environment variable overrides
├── .gitignore                        # Git ignore rules
├── pytest.ini                        # Pytest configuration with pythonpath set
├── requirements.txt                  # Python package dependency specifications
├── README.md                         # Project documentation and user guide
└── run.py                            # Root-level command-line execution runner
```

---

## 5. Supported Telemetry Metrics & Engineered Features

### 5.1 Raw Metrics (Phase 2)
Harvested directly from host OS APIs via `psutil`:
* **CPU**: Overall utilization %, logical core count, physical core count, per-core utilization %.
* **Memory**: Total, available, used physical RAM (bytes and MB), utilization %.
* **Disk**: Partition mount point, total, used, free space (GB), utilization %.
* **Network**: Cumulative bytes/packets sent & received, instantaneous upload and download throughput (bytes/s).
* **Processes**: Top N processes sorted by CPU and memory %, with PID, process name, status.

### 5.2 Engineered Numerical Feature Vector (Phase 3)
The preprocessing pipeline transforms each telemetry snapshot into 39 continuous numerical features:

| Domain | Feature Identifier | Units | Description |
| :--- | :--- | :--- | :--- |
| **CPU** | `cpu_utilization_percent` | % | Current host CPU utilization percentage |
| | `cpu_utilization_delta` | % | CPU percentage change from previous sample |
| | `cpu_utilization_rolling_mean` | % | Moving average of CPU utilization over window |
| | `cpu_utilization_rolling_max` | % | Maximum CPU utilization observed over window |
| | `cpu_utilization_rolling_min` | % | Minimum CPU utilization observed over window |
| | `cpu_cores_logical` | count | Total logical cores / hyperthreads |
| **Memory** | `memory_utilization_percent` | % | Physical RAM utilization percentage |
| | `memory_used_mb` | MB | Physical RAM in active use |
| | `memory_available_mb` | MB | Physical RAM available for allocation |
| | `memory_utilization_delta` | % | Memory utilization change from previous sample |
| | `memory_used_delta_mb` | MB | Memory volume change in MB from previous sample |
| | `memory_utilization_rolling_mean` | % | Moving average of RAM utilization over window |
| | `memory_utilization_rolling_max` | % | Peak RAM utilization over window |
| **Disk** | `disk_utilization_percent` | % | Aggregate filesystem storage utilization |
| | `disk_used_gb` | GB | Total disk space consumed |
| | `disk_free_gb` | GB | Total free disk space remaining |
| | `disk_utilization_delta` | % | Disk utilization change from previous sample |
| | `disk_utilization_rolling_mean`| % | Moving average of disk utilization over window |
| **Network**| `network_bytes_sent_per_sec` | B/s | Upload throughput rate |
| | `network_bytes_recv_per_sec` | B/s | Download throughput rate |
| | `network_sent_delta_per_sec` | B/s | Rate-of-change in upload throughput |
| | `network_recv_delta_per_sec` | B/s | Rate-of-change in download throughput |
| | `network_bytes_sent_rolling_mean`| B/s | Moving average upload rate over window |
| | `network_bytes_recv_rolling_mean`| B/s | Moving average download rate over window |
| | `network_bytes_sent_rolling_max` | B/s | Peak upload throughput rate over window |
| | `network_bytes_recv_rolling_max` | B/s | Peak download throughput rate over window |
| **Process**| `process_count` | count | Count of monitored processes |
| | `top_process_cpu_percent` | % | Peak CPU utilization of any single process |
| | `top_process_memory_percent` | % | Peak RAM utilization of any single process |
| | `top_processes_total_cpu_percent`| % | Aggregate CPU consumption across top processes |
| | `top_processes_total_memory_percent`| %| Aggregate RAM consumption across top processes |
| **Time** | `sample_interval_sec` | seconds | Actual elapsed time since previous sample |
| | `hour_of_day` | 0 - 23 | Time-of-day diurnal indicator |
| | `day_of_week` | 0 - 6 | Day-of-week indicator (Monday=0, Sunday=6) |
| **Quality**| `is_cpu_missing` | 0.0 / 1.0 | 1.0 if CPU domain was missing/unreadable |
| | `is_memory_missing` | 0.0 / 1.0 | 1.0 if Memory domain was missing/unreadable |
| | `is_disk_missing` | 0.0 / 1.0 | 1.0 if Disk domain was missing/unreadable |
| | `is_network_missing` | 0.0 / 1.0 | 1.0 if Network domain was missing/unreadable |
| | `is_processes_missing` | 0.0 / 1.0 | 1.0 if Process domain was missing/unreadable |

---

## 6. Preprocessing Architecture & Data Flow

```text
[Raw SystemMetrics Snapshot]
              │
              ▼
   [MetricsValidator]
   ├── Inspects physical bounds & ranges
   ├── Flags missing domains without halting pipeline
   └── Rejects non-finite values (NaN, +inf, -inf)
              │ ValidationResult
              ▼
    [MetricsCleaner]
   ├── Clamps percentages to [0.0, 100.0]
   ├── Imputes missing domains (zero, last_valid)
   └── Sets missing indicator flags (is_*_missing)
              │ CleanedSystemMetrics
              ▼
  [RollingWindowBuffer]
   ├── Bounded circular deque (max_history_size=60)
   ├── Moving window statistics (window_size=12)
   ├── Step delta calculations (current - previous)
   └── Auto-resets on clock regression or large gaps
              │ Historical Context
              ▼
   [FeatureEngineer]
   ├── Synthesizes 39 numerical features
   └── Packages into structured FeatureVector
              │
              ▼
    [ProcessedTelemetry]
```

---

## 7. Installation & Setup

### 7.1 Virtual Environment Setup

```powershell
# Navigate to workspace
cd "e:\DSA\AI-Based Server Health Monitoring"

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

### 7.2 Configuration

Create `.env` from template:

```powershell
copy .env.example .env
```

Available environment variables:
```ini
# Application Metadata
APP_NAME="AI-Based Predictive System Health Monitoring"
APP_ENV=development
LOG_LEVEL=INFO

# Metric Collection Settings (seconds between sampling intervals)
METRIC_COLLECTION_INTERVAL=5.0

# Process Telemetry Limits
MAX_PROCESSES=10

# Preprocessing & Feature Engineering Settings (Phase 3)
ROLLING_WINDOW_SIZE=12
MAX_HISTORY_SIZE=60
MISSING_VALUE_STRATEGY=zero

# Database Persistence Settings (Phase 4)
# DB_PATH=system_metrics.db
# DB_CONNECTION_TIMEOUT=30.0
# DB_AUTO_INIT=true
# DB_RETENTION_DAYS=30
```

---

## 8. SQLite Data Persistence (Phase 4)

Phase 4 implements a zero-dependency, normalized SQLite persistence layer managed through `app/database/`.

### 8.1 Database Architecture & Schema

The relational store maintains four primary tables in `data/system_metrics.db`:

1. **`schema_migrations`**:
   - Tracks version history (`version`, `applied_at`, `description`) to guarantee idempotent initialization without data loss.
2. **`system_metrics`**:
   - Stores raw telemetry captured by Phase 2 collectors.
   - Fields: `id`, `timestamp` (UTC ISO 8601), `cpu_percent`, `cpu_logical_cores`, `cpu_physical_cores`, `memory_total_bytes`, `memory_used_bytes`, `memory_available_bytes`, `memory_percent`, `disk_total_bytes`, `disk_used_bytes`, `disk_free_bytes`, `disk_percent`, `network_bytes_sent`, `network_bytes_recv`, `network_bytes_sent_per_sec`, `network_bytes_recv_per_sec`, `process_count`, `top_process_pid`, `top_process_name`, `top_process_cpu_percent`, `top_process_memory_percent`, and full raw `raw_payload_json`.
   - Index on `timestamp`.
3. **`feature_vectors`**:
   - Stores the 39 engineered continuous numerical features computed in Phase 3.
   - Foreign key: `metric_id REFERENCES system_metrics(id) ON DELETE CASCADE`.
   - Fields: `id`, `metric_id`, `timestamp`, 39 distinct typed `REAL` columns matching `FeatureVector.feature_names` (e.g., `cpu_utilization_percent`, `memory_used_delta_mb`, `network_bytes_recv_rolling_mean`, etc.), plus `features_json` and `metadata_json`.
   - Indexes on `timestamp` and `metric_id`.
4. **`validation_logs`**:
   - Audit trail of preprocessing validation results.
   - Foreign key: `metric_id REFERENCES system_metrics(id) ON DELETE CASCADE`.
   - Fields: `id`, `metric_id`, `timestamp`, `is_valid` (0/1), `issues_count`, `has_errors` (0/1), and `issues_json` (structured list of issue domains, types, and messages).
   - Indexes on `timestamp` and `metric_id`.

### 8.2 Database Operations & Integrity

* **Connection PRAGMAs**: Automatically enables Write-Ahead Logging (`PRAGMA journal_mode = WAL;`), strict foreign key enforcement (`PRAGMA foreign_keys = ON;`), normal synchronous flushing (`PRAGMA synchronous = NORMAL;`), and busy timeouts (`PRAGMA busy_timeout = 30000;`).
* **Atomic Transactions**: Telemetry samples are persisted atomically via `PersistenceService.persist_sample()`. If writing to any of `system_metrics`, `feature_vectors`, or `validation_logs` fails, the transaction rolls back completely, preventing orphaned or partial records.
* **Failure Isolation**: Database operational failures log descriptive warnings without halting or crashing the host telemetry collection loop.
* **Retention Policy**: `PersistenceService.apply_retention_policy(retention_days)` safely purges records older than a configured threshold with cascade deletes.

### 8.3 Inspecting Stored Telemetry

Stored records can be inspected directly via Python or any SQLite client:

```powershell
# Quick row count query via Python
python -c "import sqlite3; conn = sqlite3.connect('data/system_metrics.db'); print('Samples:', conn.execute('SELECT COUNT(*) FROM system_metrics').fetchone()[0])"
```

Using Python interactive session:
```python
from app.core.config import get_settings
from app.database.service import PersistenceService

service = PersistenceService(settings=get_settings())
latest_metrics = service.get_latest_metrics(limit=5)
latest_features = service.get_latest_features(limit=5)
counts = service.get_record_counts()
print("Database summary:", counts)
```

### 8.4 SQLite Limitations

* **Single Writer Concurrency**: SQLite supports multiple concurrent readers in WAL mode, but only one active writer at a time. The built-in busy timeout ensures threads wait rather than fail, but high-concurrency multi-node architectures should migrate to PostgreSQL in future production deployments.
* **Local Disk Dependency**: SQLite stores data in a local file (`data/system_metrics.db`), which is ideal for single-host server health monitoring but not distributed cluster-wide aggregation.

---

## 9. Machine Learning & Failure Risk Analysis (Phase 5)

Phase 5 introduces a modular, robust machine learning and health risk evaluation subsystem that translates 39 continuous engineered features into anomaly scores, system health indices, and tiered operational risk levels.

### 9.1 Architecture & Pipeline Flow

The ML subsystem operates in two distinct workflows:

```text
[Training Workflow]
SQLite Database (feature_vectors)
       │ (FeatureDataLoader: validates 39 features, NaN/inf safe)
       ▼
Feature Matrix (N x 39)
       │
       ▼
IsolationForestDetector.fit()
       │
       ▼
ModelManager.save_model() ──► models/isolation_forest.joblib
                              models/isolation_forest_metadata.json

[Inference Workflow]
ProcessedTelemetry (Live 39-feature vector)
       │
       ▼
PredictionService
       ├── ModelManager.load_latest_model()
       ├── IsolationForestDetector.predict()  ──► AnomalyResult (score in [0, 1], is_anomaly)
       ├── HealthScoreCalculator.calculate() ──► HealthScoreResult (0.0 to 100.0)
       └── RiskAnalyzer.evaluate()           ──► RiskCategory (Normal, Low, Moderate, High, Critical)
```

### 9.2 Historical Data Loading & Feature Schema

* **Data Retrieval**: `FeatureDataLoader` queries historical vectors from SQLite via `PersistenceService.get_features_in_range()` or latest-$N$ queries without bypassing the persistence layer.
* **Schema Enforcement**: `feature_schema.py` strictly verifies that feature arrays conform to the canonical 39 features in exact order (`EXPECTED_FEATURE_COUNT = 39`).
* **Data Sanitization**: Rejects non-finite values (NaN, $+\infty$, $-\infty$) and requires at least `ML_MIN_TRAINING_SAMPLES` (default: 20) before fitting.

### 9.3 Isolation Forest Anomaly Detection

* **Algorithm**: `sklearn.ensemble.IsolationForest` configured with deterministic `random_state` (default: 42), `n_estimators` (default: 100), and `contamination` (default: 0.05).
* **Calibrated Anomaly Scoring**: Raw decision scores ($>0$ for nominal, $<0$ for outliers) are calibrated into a continuous probability-like score in $[0.0, 1.0]$ via a centered logistic transform:
  $$\text{score} = \frac{1}{1 + e^{8 \cdot \text{decision\_function}(x)}}$$
  - $\text{score} \approx 0.0$: highly nominal / central cluster.
  - $\text{score} = 0.5$: exact decision boundary ($\text{decision\_function} = 0$).
  - $\text{score} \to 1.0$: extreme outlier / high behavioral anomaly.
* **Semantic Meaning**: The anomaly detector flags *unusual metric patterns* relative to baseline telemetry. It does **not** confirm physical hardware breakdown.

### 9.4 Deterministic System Health Score (0–100)

`HealthScoreCalculator` computes a transparent, reproducible health score from 0.0 to 100.0:

$$\text{Health Score} = \max\Big(0.0,\, \min\big(100.0,\, 100.0 - (\text{Anomaly Penalty} + \text{Resource Penalties})\big)\Big)$$

1. **Anomaly Penalty**: Up to 60.0 points deducted proportional to the calibrated anomaly score:
   $$\text{Anomaly Penalty} = \text{calibrated\_anomaly\_score} \times 60.0$$
2. **Resource Stress Penalties**: Up to 40.0 points deducted for extreme host saturation:
   - CPU $> 80.0\%$: up to 15.0 points ($\frac{\text{CPU} - 80}{20} \times 15.0$)
   - RAM $> 85.0\%$: up to 15.0 points ($\frac{\text{RAM} - 85}{15} \times 15.0$)
   - Disk $> 90.0\%$: up to 10.0 points ($\frac{\text{Disk} - 90}{10} \times 10.0$)
3. **Availability State**: If no trained model or telemetry is available, the calculator flags `is_available=False` rather than reporting an unsubstantiated score.

### 9.5 Anomaly-Based Risk Categorization

`RiskAnalyzer` maps the combined anomaly score and resource indicators into 5 actionable risk tiers:

| Risk Category | Anomaly Score Threshold | Health Score Range | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **Normal** | $< 0.35$ | $80.0 - 100.0$ | Metrics within historical normal baseline distribution. |
| **Low** | $0.35 \le s < 0.55$ | $65.0 - 79.9$ | Mild variation; metrics slightly deviating from nominal. |
| **Moderate** | $0.55 \le s < 0.75$ | $45.0 - 64.9$ | Notable behavioral anomaly or sustained metric elevation. |
| **High** | $0.75 \le s < 0.90$ | $25.0 - 44.9$ | Significant multi-metric outlier; immediate attention recommended. |
| **Critical** | $\ge 0.90$ (or override) | $0.0 - 24.9$ | Extreme anomaly, health $\le 20.0$, or hardware saturation $\ge 95\%$. |

* **Hardware Override**: If CPU, RAM, or Disk utilization reaches $\ge 95\%$, the risk analyzer automatically elevates the tier to **Critical** regardless of model prediction.

### 9.6 Model Artifact Management & Validation

* **Storage Location**: Artifacts reside in `models/` as `isolation_forest.joblib` and companion `isolation_forest_metadata.json`.
* **Atomic Serialization**: Models are saved via atomic temporary file renames, preventing corrupted models if disk writes are interrupted.
* **Schema Drift Protection**: Metadata stores feature count, feature names in order, training timestamp, and sample counts. When loading, `ModelManager` verifies exact feature schema compatibility; mismatched models are rejected with `ModelIncompatibleError`.
* **Safe Fallback**: If no model is trained or a model artifact is corrupt, `PredictionService` automatically operates in a transparent heuristic fallback mode without halting the host monitoring loop.

### 9.7 Supervised Failure Classification (Prerequisites & Extension Point)

* **Ground-Truth Distinction**: The project repository and host telemetry contain continuous operational metrics, but **no authentic labeled hardware failure events** (e.g., thermal shutdowns, disk sector failures, kernel panics).
* **Academic Integrity**: Unsupervised anomaly scores are never disguised as "failure probability". Fabricating labels or treating anomalies as true failures is strictly rejected.
* **Extension Point**: `app/ml/supervised.py` provides `SupervisedFailureClassifier` (and `inspect_labeled_data_availability()`).
* **Requirements for True Failure Prediction**:
  1. Multi-host dataset with recorded ground-truth failure timestamps.
  2. Temporal window labeling (e.g., failures occurring within next $k$ hours).
  3. Class imbalance mitigation (e.g., SMOTE, cost-sensitive learning).
  4. Time-series cross-validation (rolling-origin or group temporal split) avoiding data leakage.
  5. Calibrated probability scoring (e.g., isotonic regression or Platt scaling).

---

## 10. Interactive Web Dashboard (Phase 6)

Phase 6 implements a web-based monitoring dashboard built with **Streamlit** and **Plotly**. The dashboard integrates with the telemetry collection engine (Phase 2), preprocessing pipeline (Phase 3), SQLite persistence layer (Phase 4), and Isolation Forest risk engine (Phase 5).

### 10.1 Modular Dashboard Architecture

The dashboard is structured under `app/dashboard/` to maintain clean separation of concerns:

```text
app/dashboard/
├── app.py                      # Streamlit application entry point & page router
├── services/
│   ├── __init__.py
│   └── dashboard_service.py    # Coordination layer (metrics, predictions, history, lifecycle)
├── charts/
│   ├── __init__.py
│   └── builders.py             # Plotly chart builders (gauges, time-series, bars, scatter)
├── components/
│   ├── __init__.py
│   ├── status_header.py        # System health banner & operational indicators
│   ├── metrics_cards.py        # Resource metric cards (CPU, RAM, Disk, Net, Procs)
│   └── health_card.py          # Health score, risk matrix, & deductions breakdown
└── utils/
    ├── __init__.py
    └── formatting.py           # Unit conversion, badge generators, & threshold checks
```

### 10.2 Dedicated Dashboard Views

The sidebar navigation provides access to 6 purpose-built views:

1. **System Overview**: Executive snapshot displaying system status, last refresh timestamp, and metric cards for CPU, RAM, Disk, Network TX/RX throughput, and active processes, complete with warning indicators.
2. **Health & Risk Analysis**: In-depth evaluation displaying the 0–100 Health Score radial gauge, calibrated anomaly probability gauge, risk classification tier (Normal, Low, Moderate, High, Critical), transparent deduction breakdown, and model availability notice.
3. **Real-Time Monitoring**: Live telemetry interface with safe background worker controls. Users can capture single telemetry snapshots on demand or toggle continuous background collection safely.
4. **Historical Telemetry**: Multi-metric Plotly time-series visualization querying real persisted SQLite telemetry over customizable time ranges (1 hour, 6 hours, 24 hours, 7 days, or all time) with dual y-axes for percentage and throughput metrics.
5. **Anomaly Audit Log**: Scatter plot timeline of historical anomaly scores color-coded by risk category, accompanied by an interactive audit table with risk severity badges.
6. **Database Inspection**: Storage summary displaying total counts across `system_metrics`, `feature_vectors`, and `validation_logs`, earliest and latest sample timestamps, database file size on disk, and a bounded raw records table.

### 10.3 Thread-Safe Monitoring Lifecycle

Running background tasks in Streamlit requires rigorous lifecycle management to prevent multiple competing collection threads from spawning upon user interaction:

* **Worker Coordination**: `DashboardService` employs a module-level `threading.Lock` and `threading.Event` (`_stop_event`).
* **Singleton Worker Guarantee**: If a background thread is already active, subsequent start requests are safely ignored.
* **Graceful Termination**: Toggling "Stop Monitoring" sets the stop event, allowing the worker thread to finish its active iteration, release database connections, and terminate cleanly without blocking the UI.
* **Decoupled Architecture**: Operators can run continuous monitoring as a standalone background process (`python run.py`) and view the dashboard independently (`python run.py --dashboard`), or control collection directly within the dashboard.

### 10.4 Heuristic Fallback & Academic Integrity

* **Heuristic Transparency**: When no trained model exists in `models/` or the database has insufficient samples, the dashboard explicitly labels predictions as **Heuristic Fallback Mode** and does not fabricate ML confidence.
* **Academic Disclaimer**: The dashboard features an explicit disclaimer clarifying that *statistical anomaly detection identifies unusual host behavior and does not confirm physical hardware failure*.

---

## 11. How to Start the Application

### 11.1 Launching the Interactive Web Dashboard

To start the Streamlit web dashboard:

```powershell
# Using the run.py CLI shortcut (Recommended)
python run.py --dashboard

# Or using the Streamlit CLI directly
streamlit run app/dashboard/app.py --server.port 8501
```

Once launched, navigate to `http://localhost:8501` in your web browser.

### 11.2 Continuous Periodic Monitoring (CLI)

Execute the continuous background monitoring process:

```powershell
python run.py
```

The application initiates telemetry collection, preprocessing, database persistence, and ML inference:
```text
2026-10-01 12:55:00 [INFO] [app]: Starting AI-Based Predictive System Health Monitoring (v0.1.0)
2026-10-01 12:55:00 [INFO] [app.ml.model_manager]: Loaded model IsolationForestDetector (v1.0.0)
2026-10-01 12:55:01 [INFO] [app]: [METRICS] CPU:  12.4% (8 cores) | RAM:  52.1% (8,210/15,765 MB) | Disk:  58.2% (276.4 GB used)
2026-10-01 12:55:01 [INFO] [app]: [ML INFERENCE] Score: 0.1377 | Health: 91.7/100 | Risk: Normal | Status: Nominal
```

Press **Ctrl+C** to trigger clean shutdown.

### 11.3 Single-Shot Telemetry & Inference Snapshot

```powershell
python run.py --single-shot
```

Output:
```text
2026-10-01 12:56:10 [INFO] [app]: Collected telemetry snapshot: CPU:   0.0% (8 cores) | RAM:  51.9%
2026-10-01 12:56:10 [INFO] [app]: Extracted 39 numerical features (validation_valid=True, issues=0)
2026-10-01 12:56:10 [INFO] [app]: Persisted sample to database (metric_id=14, feature_id=14, validation_id=14)
2026-10-01 12:56:10 [INFO] [app]: [ML INFERENCE] Score: 0.1377 | Health: 91.7/100 | Risk: Normal | Status: Nominal
```

### 11.4 Training the Machine Learning Model

To train or retrain the Isolation Forest model using historical telemetry stored in SQLite:

```powershell
# Using run.py CLI
python run.py --train

# Or using the training module directly (with custom sample requirements)
python -m app.ml.training --min-samples 20 --contamination 0.05
```

Output:
```text
2026-10-01 12:53:15 [INFO] [app.ml.training]: Starting Isolation Forest model training pipeline...
2026-10-01 12:53:15 [INFO] [app.ml.data_loader]: Loaded 25 feature records from SQLite
2026-10-01 12:53:15 [INFO] [app.ml.training]: Training IsolationForestDetector on 25 samples (39 features)...
2026-10-01 12:53:15 [INFO] [app.ml.model_manager]: Model artifact successfully saved to models/isolation_forest.joblib
2026-10-01 12:53:15 [INFO] [app.ml.training]: Model training completed successfully!
```

---

## 12. How to Run Tests

Run the full automated test suite using `pytest`:

```powershell
pytest
```

All **195 tests** pass with 100% success rate across 30 test files:
* **Configuration (20 tests)**: Phase 1 & 2 settings, Phase 3 rolling parameters, Phase 4 database connection and retention settings, Phase 5 ML configuration, and Phase 6 dashboard settings.
* **Collectors (25 tests)**: Unit and live integration tests for CPU, Memory, Disk, Network, Process, and System collectors.
* **Preprocessing (21 tests)**:
  - Validator: Range, non-finite (NaN/inf), missing domain isolation, future timestamp checks.
  - Cleaner: Out-of-bounds percentage clamping, NaN/inf replacement, missing indicator flags, `last_valid` imputation.
  - Rolling Buffer: Bounded history, rolling mean/max/min over sliding window, step deltas, timestamp regression reset, large gap reset.
  - Feature Engineer: Schema and typing verification, `to_dict()`, `to_numpy()`, sequential delta calculations.
  - Pipeline: End-to-end processing with mock and live hardware telemetry, reset behavior.
* **Database Persistence (28 tests)**:
  - Connection (`test_database_connection.py` - 6 tests): Connection PRAGMAs, WAL mode, foreign keys, transaction commits, rollbacks, session management.
  - Schema (`test_database_schema.py` - 5 tests): Schema migrations, versioning, 39 feature columns, foreign key enforcement, idempotent re-runs.
  - Repository (`test_database_repository.py` - 7 tests): Parameterized CRUD, range queries, latest-N queries, count queries, injection prevention, retention deletion.
  - Service (`test_database_service.py` - 5 tests): PersistenceService initialization, atomic multi-table commit, failure rollback, retention policy, range lookups.
  - Integration (`test_database_integration.py` - 3 tests): Full collector -> pipeline -> persistence flow, cascade delete, single-shot execution.
* **Machine Learning & Risk Analysis (48 tests)**:
  - Feature Schema (`test_ml_feature_schema.py` - 8 tests): 39-feature schema enforcement, strict column ordering, matrix conversions, NaN/inf validation.
  - Anomaly Detector (`test_ml_anomaly_detector.py` - 9 tests): Isolation Forest fit, calibrated score bounds $[0, 1]$, deterministic seed, dimension mismatch rejection, unfitted state handling.
  - Health Score (`test_ml_health_score.py` - 7 tests): Score bounds $[0, 100]$, anomaly penalty calculation, CPU/RAM/Disk saturation penalties, clamping, unavailable state.
  - Risk Analyzer (`test_ml_risk_analyzer.py` - 4 tests): Tier categorization (Normal, Low, Moderate, High, Critical), threshold configuration, hardware saturation overrides, structured explanation.
  - Model Manager (`test_ml_model_manager.py` - 6 tests): Atomic saving/loading, companion JSON metadata, corrupt artifact handling, schema mismatch rejection.
  - Data Loader (`test_ml_data_loader.py` - 5 tests): Historical feature loading from SQLite, empty DB handling, insufficient sample exception.
  - Supervised (`test_ml_supervised.py` - 3 tests): Ground-truth inspection, prerequisite documentation, classifier interface stub.
  - Prediction Service (`test_ml_prediction_service.py` - 4 tests): End-to-end inference coordination, heuristic fallback when model missing, hot-reloading.
  - Training Pipeline (`test_ml_training.py` - 2 tests): End-to-end training execution, metadata persistence, baseline validation metrics.
* **Interactive Web Dashboard (18 tests)**:
  - Formatting Utilities (`test_dashboard_utils.py` - 6 tests): Unit conversions (`format_bytes`, `format_percent`, `format_throughput`, `format_timestamp`), risk badge HTML generation across all 5 tiers, and resource utilization threshold status classification.
  - Plotly Chart Builders (`test_dashboard_charts.py` - 5 tests): Radial health gauges (0–100), calibrated anomaly gauges (0.0–1.0), multi-metric dual-axis time-series charts with throughput handling, resource breakdown bar charts with threshold lines, and risk-categorized anomaly scatter charts.
  - Dashboard Service (`test_dashboard_service.py` - 7 tests): Service initialization, latest metrics and prediction retrieval, single-shot telemetry snapshots, historical metrics and feature filtering, database summary statistics, and thread-safe background monitoring start/stop lifecycle.
* **Phase 7 — System Integration, Reliability & Edge Cases (34 tests)** (`test_phase7_integration.py`):
  - End-to-End Data Flow (4 tests): Live hardware harvest to SQLite and dashboard, 39-dimension schema verification, multi-sample accumulation, dashboard retrieval cycle.
  - Edge Cases & Reliability (7 tests): Empty database resilience, prediction without model (heuristic fallback), missing model file handling, corrupted JSON metadata handling, schema dimension mismatch rejection, missing subsystem recovery with quality indicators, non-finite feature handling, out-of-order timestamp insertion.
  - Database Integrity (5 tests): SQLite `PRAGMA integrity_check`, foreign key cascade consistency (`PRAGMA foreign_key_check`), atomic transaction rollback on failure, retention policy purge, idempotent migration re-execution.
  - ML Pipeline Validation (9 tests): 39-feature dimension agreement between schema and DB, feature mapping validation, Isolation Forest fit & score bounds, unfitted exception handling, health score [0, 100] bounds, risk category thresholds, hardware saturation overrides, atomic model save/load roundtrips, PredictionService integration with trained model.
  - Dashboard Edge Cases (4 tests): Background worker start/stop lifecycle and double-start rejection, live snapshot persist and predict, historical anomaly evaluation on empty database, database summary file size reporting.
  - Preprocessing Edge Cases (3 tests): Partial collector failure resilience with indicator imputation, validator range and NaN/inf detection, pipeline rolling buffer reset.

To run only the Phase 7 integration test suite:
```powershell
pytest tests/test_phase7_integration.py
```

---

## 13. Development Phases and Roadmap

| Phase | Milestone Name | Status | Deliverables |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Project Foundation & Architecture** | **COMPLETED** | Modular directory layout, configuration system, structured logging, entry points, unit tests, architecture specification. |
| **Phase 2** | **Metric Collection Engine** | **COMPLETED** | `psutil` collectors for CPU, Memory, Disk, Network, and Process health; typed metric data models; failure isolation; periodic sampling loop; unit & integration tests. |
| **Phase 3** | **Data Preprocessing & Feature Engineering** | **COMPLETED** | Telemetry validator, data cleaner with imputation strategies, bounded rolling window buffer, 39 engineered features, end-to-end preprocessing pipeline, unit & integration tests. |
| **Phase 4** | **SQLite Data Persistence** | **COMPLETED** | SQLite connection manager (WAL mode, FKs), versioned schema migrations, normalized tables for raw metrics, 39-feature vectors, and validation logs, atomic transactions, retention cleanup, full test suite (94 passing tests). |
| **Phase 5** | **Machine Learning & Failure Risk Engine** | **COMPLETED** | Historical SQLite data loader, Isolation Forest anomaly detector, logistic score calibration, deterministic 0–100 health scoring, multi-tier risk analyzer, atomic model persistence, supervised failure classification extension point, 48 ML unit/integration tests (143 total passing tests). |
| **Phase 6** | **Interactive Web Dashboard** | **COMPLETED** | Modular Streamlit web application, Plotly visualizers, thread-safe background monitoring controls, 6 dedicated views, database inspector, 18 new unit & integration tests (161 total passing tests). |
| **Phase 7** | **System Testing, Validation & Finalization** | **COMPLETED** | 34 comprehensive integration tests (195 total passing tests), live hardware pipeline validation, SQLite PRAGMA verification, background worker lifecycle stability, academic integrity documentation, and demonstration readiness report. |

---

## 14. Academic Integrity & Machine Learning Scope

In academic research and system engineering, precision of terminology is essential. The capabilities of this software platform are structured into distinct analytical layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SYSTEM HEALTH & RISK ARCHITECTURE                     │
├────────────────────────────────────────────────────────────────────────┤
│  1. Unsupervised Anomaly Detection (Isolation Forest)                   │
│     • Identifies statistical divergence from historical baseline       │
│     • Calibrated anomaly score in [0.0, 1.0]                          │
│     • Does NOT equal calibrated failure probability                   │
├────────────────────────────────────────────────────────────────────────┤
│  2. Hardware Saturation & Safety Rules (Deterministic)                  │
│     • Evaluates CPU, RAM, and Disk capacity exhaustion                │
│     • Hard override triggers Critical tier when resources >= 95%      │
├────────────────────────────────────────────────────────────────────────┤
│  3. Composite System Health Score (Heuristic 0–100)                     │
│     • Transparent weighted formula balancing anomaly penalties         │
│       and hardware resource saturation                                 │
│     • Categorizes operational status: Optimal, Good, Fair, Poor, Crit.│
├────────────────────────────────────────────────────────────────────────┤
│  4. Supervised Hardware Failure Prediction (Future / Labeled Data)      │
│     • Requires ground-truth failure events (kernel panic, crash logs)  │
│     • Requires defined prediction horizon tau and run-to-failure data  │
│     • Formal interface defined in app/ml/supervised.py                 │
└────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Anomaly Score ≠ Failure Probability**: The Isolation Forest anomaly score reflects the degree to which a 39-dimensional telemetry snapshot is statistically isolated from historical operational patterns. An anomalous state may result from a benign batch job, a software compilation, or metric spikes, and does not inherently imply imminent physical hardware failure. Genuine failure prediction requires supervised run-to-failure trajectories, as documented in [`app/ml/supervised.py`](file:///e:/DSA/AI-Based%20Server%20Health%20Monitoring/app/ml/supervised.py).

