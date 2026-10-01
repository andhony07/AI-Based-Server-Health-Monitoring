"""Interactive dashboard and visualization package.

Architectural Components:
- app.py: Streamlit application entry point.
- services/: DashboardService integration layer coordinating persistence, ML, and collectors.
- charts/: Plotly chart builders for health gauges, multi-metric time series, and anomaly scatter plots.
- components/: Reusable visual components (status header, metric cards, health cards).
- utils/: Formatting and presentation helpers.
"""

from app.dashboard.services.dashboard_service import DashboardService

__all__ = ["DashboardService"]
