"""FastAPI dependency injection providers.

Provides cached and test-overridable access to application Settings and
the central DashboardService coordinator.
"""

from __future__ import annotations

import threading
from typing import Optional

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.dashboard.services.dashboard_service import DashboardService

_service_instance: Optional[DashboardService] = None
_service_lock = threading.Lock()


def get_api_settings() -> Settings:
    """Provide application configuration settings for route dependencies.

    Returns:
        Active Settings instance.
    """
    return get_settings()


def get_dashboard_service(
    settings: Settings = Depends(get_api_settings),
) -> DashboardService:
    """Provide a shared DashboardService instance.

    Thread-safe lazy initialization ensures a single service coordinator
    is reused across API requests within the server process.

    Args:
        settings: Injected or resolved Settings instance.

    Returns:
        Configured DashboardService instance.
    """
    global _service_instance
    with _service_lock:
        if _service_instance is None:
            active_settings = settings if isinstance(settings, Settings) else get_api_settings()
            _service_instance = DashboardService(settings=active_settings)
        return _service_instance


def reset_dashboard_service(new_service: Optional[DashboardService] = None) -> None:
    """Reset or override the global service coordinator (primarily for testing).

    Args:
        new_service: Optional custom DashboardService to inject.
    """
    global _service_instance
    with _service_lock:
        _service_instance = new_service
