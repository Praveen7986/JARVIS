"""
GitHub Activity & PR Radar Desktop Widget Module.
"""

from .widget import GitHubRadarWidget
from .settings_dialog import GitHubSettingsDialog
from .github_service import fetch_github_data

__all__ = ["GitHubRadarWidget", "GitHubSettingsDialog", "fetch_github_data"]
