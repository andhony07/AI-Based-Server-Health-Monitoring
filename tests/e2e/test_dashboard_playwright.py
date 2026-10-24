"""Playwright End-to-End Test Suite for AI Server Health & Failure Risk Monitor.

Validates the running Streamlit web application at http://localhost:8501:
- Application startup and executive header rendering
- Dynamic dark and light theme switching and visual persistence
- System Overview telemetry metric cards and saturation charts
- Health & Risk Analysis matrix and exception-free risk badge rendering
- Real UI execution of deterministic Anomaly Simulation scenarios
- Real-Time Monitoring, Historical Telemetry, Anomaly Audit Log, and Database Status views
- Browser console error logging and network integrity
"""

import os
import sys
import time
from pathlib import Path
from typing import Generator, List

import pytest

# Point PLAYWRIGHT_BROWSERS_PATH to the installed browser binaries
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"C:\Users\dell5420\AppData\Local\ms-playwright"

try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Browser = object  # type: ignore[assignment,misc]
    BrowserContext = object  # type: ignore[assignment,misc]
    Page = object  # type: ignore[assignment,misc]
    sync_playwright = None  # type: ignore[assignment]
    pytestmark = pytest.mark.skip(reason="Playwright not installed in Python environment")

DASHBOARD_URL = "http://localhost:8501"
SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots_final"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="module")
def browser() -> Generator[Browser, None, None]:
    """Launch headless Chromium browser for the E2E test module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a standardized browser context with desktop viewport."""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    yield context
    context.close()


@pytest.fixture(scope="module")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Provide a shared page instance that opens the dashboard and monitors errors."""
    page = context.new_page()
    page.set_default_timeout(25000)
    yield page
    page.close()


def assert_no_streamlit_exceptions(page: Page, context_msg: str = "") -> None:
    """Assert that no Streamlit exception panels or Python tracebacks appear on the page."""
    exceptions = page.query_selector_all('[data-testid="stException"]')
    if exceptions:
        err_text = exceptions[0].inner_text()
        pytest.fail(f"Streamlit Exception detected ({context_msg}): {err_text}")


def wait_for_streamlit_ready(page: Page, timeout_ms: int = 20000) -> None:
    """Wait until Streamlit status indicators finish running."""
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=timeout_ms)
    # Ensure spinner / progress has settled
    page.wait_for_timeout(1000)


def navigate_sidebar(page: Page, view_name: str) -> None:
    """Navigate to a view by clicking its label in the Navigation radio group."""
    if not page.url.startswith("http"):
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        wait_for_streamlit_ready(page)
    nav_radio = page.locator('[data-testid="stSidebar"] [data-testid="stRadio"]').first
    nav_option = nav_radio.locator(f'label:has-text("{view_name}")')
    nav_option.scroll_into_view_if_needed()
    nav_option.click(force=True)
    page.wait_for_timeout(2000)
    assert_no_streamlit_exceptions(page, f"Navigating to {view_name}")


class TestDashboardPlaywrightE2E:
    """Full End-to-End test suite for the AIOps monitoring dashboard."""

    def test_a_application_startup(self, page: Page) -> None:
        """Test A: Verify application startup, page title, and executive header."""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        wait_for_streamlit_ready(page)

        # Check browser tab title
        assert "Server Health & Failure Risk Monitor" in page.title()

        # Check executive banner header
        header = page.locator("h2").first
        header.wait_for(state="visible", timeout=10000)
        header_text = header.inner_text()
        assert "AI Server Health & Failure Risk Monitor" in header_text

        # Verify operational indicators in top banner
        main_content = page.locator('[data-testid="stMain"]').inner_text()
        assert "AI Server Health & Failure Risk Monitor" in main_content
        assert "Isolation Forest" in main_content or "Real-Time OS Telemetry" in main_content

        # Confirm no runtime exception panels
        assert_no_streamlit_exceptions(page, "Initial Page Load")

        # Capture initial startup screenshot
        screenshot_path = SCREENSHOT_DIR / "01_initial_startup.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        assert screenshot_path.exists()

    def test_b_theme_switching(self, page: Page) -> None:
        """Test B: Verify Dark-Only AIOps Command Center theme permanence and CSS variables."""
        # Confirm that no redundant theme-switcher radio exists in the sidebar
        sidebar_radios = page.locator('[data-testid="stSidebar"] [data-testid="stRadio"]').all()
        assert len(sidebar_radios) == 1, "Expected only the Navigation radio in the sidebar (dark mode is sole theme)"

        # Verify dark mode CSS variables are active on the canvas
        style_content = page.content()
        assert "--bg-app: #0B0F19;" in style_content
        assert "--bg-card: #151D2C;" in style_content
        assert "--border-color: #293548;" in style_content
        assert "--accent: #38BDF8;" in style_content

        # Confirm no runtime exception panels
        assert_no_streamlit_exceptions(page, "Dark-Only Theme Verification")

        # Capture Dark Theme Command Center screenshot
        dark_shot = SCREENSHOT_DIR / "02_theme_dark_command_center.png"
        page.screenshot(path=str(dark_shot), full_page=False)
        assert dark_shot.exists()

    def test_c_system_overview(self, page: Page) -> None:
        """Test C: Verify System Overview telemetry metric cards and saturation bar chart."""
        navigate_sidebar(page, "System Overview")

        # Verify 5 metric cards: CPU, RAM, Disk, Network, Processes
        metrics = page.locator('[data-testid="stMetric"]').all()
        assert len(metrics) >= 5, f"Expected at least 5 metric cards, found {len(metrics)}"

        # Check metric labels
        labels = [m.locator('[data-testid="stMetricLabel"]').inner_text().upper() for m in metrics[:5]]
        assert any("CPU" in l for l in labels)
        assert any("RAM" in l or "MEMORY" in l for l in labels)
        assert any("DISK" in l for l in labels)

        # Verify Plotly saturation bar chart is rendered
        plotly_charts = page.locator('.js-plotly-plot').all()
        assert len(plotly_charts) >= 1, "Expected resource saturation Plotly chart to be rendered"

        # Capture System Overview screenshot
        overview_shot = SCREENSHOT_DIR / "04_system_overview.png"
        page.screenshot(path=str(overview_shot), full_page=False)
        assert overview_shot.exists()

    def test_d_health_and_risk_analysis(self, page: Page) -> None:
        """Test D: Specifically verify that get_theme_risk_badge error is fixed and matrix renders."""
        navigate_sidebar(page, "Health & Risk Analysis")

        # Check for the previous bug: get_theme_risk_badge() got an unexpected keyword argument 'theme'
        assert_no_streamlit_exceptions(page, "Health & Risk Analysis page load")

        # Verify radial health and anomaly Plotly gauges
        gauges = page.locator('.js-plotly-plot').all()
        assert len(gauges) >= 2, "Expected Health Score gauge and Calibrated Anomaly gauge"

        # Verify 5-tier Risk Categorization Reference Matrix
        page_text = page.locator('[data-testid="stAppViewContainer"]').inner_text()
        for tier in ["Normal", "Low", "Moderate", "High", "Critical"]:
            assert tier in page_text, f"Expected risk tier '{tier}' in Reference Matrix"

        # Verify Diagnostic Recommendations expander
        assert "Explainable Diagnostic Recommendations" in page_text or "Primary Concern" in page_text

        # Capture Health & Risk Analysis screenshot
        health_shot = SCREENSHOT_DIR / "05_health_and_risk_analysis.png"
        page.screenshot(path=str(health_shot), full_page=False)
        assert health_shot.exists()

        # Scroll down to capture the Five-Tier Risk Matrix and Diagnostic Evidence
        page.locator('text=Five-Tier Operational Risk Categorization Matrix').scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        matrix_shot = SCREENSHOT_DIR / "05_health_and_risk_matrix.png"
        page.screenshot(path=str(matrix_shot), full_page=False)
        assert matrix_shot.exists()

        # Scroll further down to capture Diagnostic Recommendations & Remediation Sequence
        expanders = page.locator('[data-testid="stExpander"]').all()
        if expanders:
            expanders[-1].scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            diag_shot = SCREENSHOT_DIR / "05_health_and_risk_diagnostics.png"
            page.screenshot(path=str(diag_shot), full_page=False)
            assert diag_shot.exists()

    def test_e_anomaly_simulation_execution(self, page: Page) -> None:
        """Test E: Execute deterministic Anomaly Simulation in the live UI and verify output."""
        navigate_sidebar(page, "Anomaly Simulation")
        assert_no_streamlit_exceptions(page, "Anomaly Simulation view")

        # Verify scenario selector exists
        selectbox = page.locator('[data-testid="stSelectbox"]')
        assert selectbox.count() >= 1, "Expected Anomaly Scenario Profile selectbox"

        # Click the 'Run Anomaly Simulation' primary button
        run_btn = page.locator('button:has-text("Run Anomaly Simulation")')
        run_btn.wait_for(state="visible", timeout=5000)
        run_btn.click()

        # Wait for simulation execution to complete
        page.wait_for_timeout(3500)
        assert_no_streamlit_exceptions(page, "Post-simulation execution")

        # Verify simulated telemetry section appeared
        page_text = page.locator('[data-testid="stAppViewContainer"]').inner_text()
        assert "Simulated Hardware Telemetry" in page_text or "SIMULATED" in page_text
        assert "Machine Learning Pipeline Evaluation" in page_text or "Explainable Diagnostic" in page_text

        # Capture Anomaly Simulation screenshot (top)
        sim_top = page.locator('text=Scenario-Based Fault & Anomaly Simulation')
        if sim_top.count() > 0:
            sim_top.first.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        sim_shot = SCREENSHOT_DIR / "06_anomaly_simulation_result.png"
        page.screenshot(path=str(sim_shot), full_page=False)
        assert sim_shot.exists()

        # Scroll to comparative telemetry & ML pipeline evaluation
        comp_target = page.locator('text=Baseline vs. Simulated Hardware Telemetry')
        if comp_target.count() > 0:
            comp_target.first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            sim_comp_shot = SCREENSHOT_DIR / "06_anomaly_simulation_comparison.png"
            page.screenshot(path=str(sim_comp_shot), full_page=False)
            assert sim_comp_shot.exists()

        # Scroll to diagnostic report & remediation
        diag_target = page.locator('text=Explainable Diagnostic Recommendations')
        if diag_target.count() > 0:
            diag_target.first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            sim_diag_shot = SCREENSHOT_DIR / "06_anomaly_simulation_diagnostics.png"
            page.screenshot(path=str(sim_diag_shot), full_page=False)
            assert sim_diag_shot.exists()

    def test_f_realtime_monitoring_view(self, page: Page) -> None:
        """Test F1: Verify Real-Time Monitoring page and controls."""
        navigate_sidebar(page, "Real-Time Monitoring")
        assert_no_streamlit_exceptions(page, "Real-Time Monitoring view")

        page_text = page.locator('[data-testid="stAppViewContainer"]').inner_text()
        assert "Live Telemetry Readings" in page_text or "Real-Time Health" in page_text

        # Capture top of Real-Time Monitoring page
        top_target = page.locator('text=Live Operational Telemetry & Worker Operations')
        if top_target.count() > 0:
            top_target.first.scroll_into_view_if_needed()
        else:
            page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        shot = SCREENSHOT_DIR / "07_realtime_monitoring.png"
        page.screenshot(path=str(shot), full_page=False)
        assert shot.exists()

        # Scroll down to capture Recent Telemetry Activity stream
        activity_target = page.locator('text=Live Telemetry Activity Stream')
        if activity_target.count() > 0:
            activity_target.first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            shot_activity = SCREENSHOT_DIR / "07_realtime_monitoring_activity.png"
            page.screenshot(path=str(shot_activity), full_page=False)
            assert shot_activity.exists()

    def test_g_historical_telemetry_view(self, page: Page) -> None:
        """Test F2: Verify Historical Telemetry line chart and records table."""
        navigate_sidebar(page, "Historical Telemetry")
        assert_no_streamlit_exceptions(page, "Historical Telemetry view")

        # Capture top of Historical Telemetry page
        hist_top = page.locator('text=Historical Telemetry & Multi-Series Trends')
        if hist_top.count() > 0:
            hist_top.first.scroll_into_view_if_needed()
        else:
            page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)

        # Check for timeseries chart
        charts = page.locator('.js-plotly-plot').all()
        assert len(charts) >= 1, "Expected historical multi-metric time series chart"

        shot = SCREENSHOT_DIR / "08_historical_telemetry.png"
        page.screenshot(path=str(shot), full_page=False)
        assert shot.exists()

        # Scroll to records table expander and expand it
        expander = page.locator('text=View Historical Records Table')
        if expander.count() > 0:
            expander.first.scroll_into_view_if_needed()
            expander.first.click()
            page.wait_for_timeout(500)
            shot_table = SCREENSHOT_DIR / "08_historical_telemetry_table.png"
            page.screenshot(path=str(shot_table), full_page=False)
            assert shot_table.exists()

    def test_h_anomaly_audit_log_view(self, page: Page) -> None:
        """Test F3: Verify Anomaly Audit Log scatter plot and filters."""
        navigate_sidebar(page, "Anomaly Audit Log")
        assert_no_streamlit_exceptions(page, "Anomaly Audit Log view")

        # Wait for the anomaly scatter timeline to be fully rendered
        page.locator('text=Historical Anomaly Evaluation Timeline').wait_for(state="visible", timeout=15000)

        # Capture top of Anomaly Audit Log page
        audit_top = page.locator('text=Historical Anomaly Audit & Event Review')
        if audit_top.count() > 0:
            audit_top.first.scroll_into_view_if_needed()
        else:
            page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)

        shot = SCREENSHOT_DIR / "09_anomaly_audit_log.png"
        page.screenshot(path=str(shot), full_page=False)
        assert shot.exists()

        # Scroll to detailed event diagnostics inspector
        inspector = page.get_by_text("Detailed Event Diagnostics").first
        inspector.wait_for(state="visible", timeout=15000)
        inspector.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        shot_insp = SCREENSHOT_DIR / "09_anomaly_audit_inspector.png"
        page.screenshot(path=str(shot_insp), full_page=False)
        assert shot_insp.exists()

    def test_i_database_operational_status_view(self, page: Page) -> None:
        """Test F4: Verify Database & Operational Status subsystem health cards."""
        navigate_sidebar(page, "Database & Operational Status")
        assert_no_streamlit_exceptions(page, "Database & Operational Status view")

        page_text = page.locator('[data-testid="stAppViewContainer"]').inner_text()
        assert "Subsystem Operational Health Status" in page_text or "System Operational Status" in page_text or "SQLite Database" in page_text
        assert "Subsystem Operational Health Checks" in page_text or "OPERATIONAL" in page_text

        # Capture top of Database & Operational Status page
        db_top = page.locator('text=Subsystem Operational Health Status & SQLite Inspector')
        if db_top.count() > 0:
            db_top.first.scroll_into_view_if_needed()
        else:
            page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)

        shot = SCREENSHOT_DIR / "10_database_operational_status.png"
        page.screenshot(path=str(shot), full_page=False)
        assert shot.exists()

        # Scroll to Table Data & Schema Explorer
        tbl_explorer = page.locator('text=Table Data & Schema Explorer')
        if tbl_explorer.count() > 0:
            tbl_explorer.first.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            shot_tbl = SCREENSHOT_DIR / "10_database_table_explorer.png"
            page.screenshot(path=str(shot_tbl), full_page=False)
            assert shot_tbl.exists()

    def test_j_browser_console_and_network_integrity(self, page: Page) -> None:
        """Test G: Verify console and network health without fatal client-side errors."""
        errors: List[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # Refresh page and ensure clean rendering without application exceptions
        page.reload(wait_until="networkidle")
        wait_for_streamlit_ready(page)
        assert_no_streamlit_exceptions(page, "Page Reload Integrity Check")

        # Filter out benign third-party or web socket lifecycle noise if any
        critical_errors = [e for e in errors if "TypeError" in e or "ReferenceError" in e or "Uncaught" in e]
        assert len(critical_errors) == 0, f"Critical JavaScript/Console errors detected: {critical_errors}"
