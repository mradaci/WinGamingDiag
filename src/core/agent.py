"""
WinGamingDiag - Core Diagnostic Agent
Main orchestrator that coordinates data collection, analysis, and reporting
"""

import sys
import time
from datetime import datetime
from typing import Optional, List
import logging

from ..models import (
    SystemSnapshot, DiagnosticResult, Issue, WindowsInfo, HardwareSnapshot,
    EventLogSummary, DriverCompatibilityResult, GameLauncherResult, NetworkDiagnosticsResult
)
from ..collectors.hardware import HardwareCollector
from ..collectors.event_logs import EventLogCollector
from ..collectors.drivers import DriverCompatibilityChecker
from ..collectors.launchers import GameLauncherDetector
from ..collectors.network import NetworkDiagnostics
from ..utils.wmi_helper import get_wmi_helper
from ..utils.redaction import get_redactor
from ..utils.cli import ConsoleUI, create_default_ui
from .analysis import analyze_for_issues


class DiagnosticAgent:
    """
    Main diagnostic agent that orchestrates the entire diagnostic process.
    """
    
    def __init__(self, ui: Optional[ConsoleUI] = None, verbose: bool = False):
        self.ui = ui or create_default_ui()
        self.verbose = verbose
        self.wmi_helper = get_wmi_helper()
        self.redactor = get_redactor()
        
        self.hardware_collector = HardwareCollector(self.wmi_helper)
        self.event_collector = EventLogCollector(self.wmi_helper)
        self.driver_checker = DriverCompatibilityChecker(self.wmi_helper)
        self.launcher_detector = GameLauncherDetector(self.wmi_helper)
        self.network_diagnostics = NetworkDiagnostics(self.wmi_helper)
        
        self.snapshot: Optional[SystemSnapshot] = None
        self.issues: List[Issue] = []
        self.errors: List[str] = []
        
    def run_full_diagnostic(self) -> DiagnosticResult:
        start_time = time.time()
        
        self.ui.header("WinGamingDiag - System Diagnostic Tool")
        self.ui.show_collection_start()
        
        collectors = {
            "Windows Info": self._collect_windows_info,
            "Hardware": self._collect_hardware_info,
            "Event Logs": self._collect_event_logs,
            "Drivers": self._check_drivers,
            "Game Launchers": self._detect_launchers,
            "Network": self._run_network_diagnostics,
        }
        
        results = {}
        for name, collector_func in collectors.items():
            self.ui.subheader(f"Collecting {name}")
            results[name] = collector_func()

        collection_duration = time.time() - start_time
        self.snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            hardware=results.get("Hardware", HardwareSnapshot()),
            windows=results.get("Windows Info", WindowsInfo(version="Unknown", build="Unknown", edition="Unknown", architecture="Unknown")),
            event_summary=results.get("Event Logs", EventLogSummary()),
            driver_result=results.get("Drivers", DriverCompatibilityResult()),
            launcher_result=results.get("Game Launchers", GameLauncherResult()),
            network_result=results.get("Network", NetworkDiagnosticsResult()),
            collection_duration_seconds=collection_duration,
            collectors_used=list(collectors.keys()),
            errors_encountered=self.errors
        )
        
        self.ui.show_collection_complete(collection_duration, len(collectors))
        
        self.ui.show_analysis_start()
        self.issues = analyze_for_issues(self.snapshot, self.ui)
        
        total_duration = time.time() - start_time
        result = DiagnosticResult(
            snapshot=self.snapshot,
            issues=self.issues,
            scan_duration_seconds=total_duration
        )
        
        self._display_results(result)
        return result
    
    def _collect_windows_info(self) -> WindowsInfo:
        # ... (implementation from before, no changes needed)
        return WindowsInfo(version="Unknown", build="Unknown", edition="Unknown", architecture="Unknown")


    def _collect_hardware_info(self) -> HardwareSnapshot:
        try:
            snapshot = self.hardware_collector.collect_all()
            hw_errors = self.hardware_collector.get_errors()
            self.errors.extend(hw_errors)
            return snapshot
        except Exception as e:
            self.errors.append(f"Hardware collection failed: {e}")
            logging.error("Hardware collection failed.", exc_info=True)
            return HardwareSnapshot()

    def _collect_event_logs(self) -> EventLogSummary:
        # ... (implementation from before)
        return EventLogSummary()

    def _check_drivers(self) -> DriverCompatibilityResult:
        # ... (implementation from before)
        return DriverCompatibilityResult()

    def _detect_launchers(self) -> GameLauncherResult:
        # ... (implementation from before)
        return GameLauncherResult()

    def _run_network_diagnostics(self) -> NetworkDiagnosticsResult:
        # ... (implementation from before)
        return NetworkDiagnosticsResult()
        
    def _display_results(self, result: DiagnosticResult):
        # ... (implementation from before)
        pass

    def save_report(self, result: DiagnosticResult, output_path: Optional[str] = None) -> str:
        # ... (implementation from before)
        return ""

__all__ = ['DiagnosticAgent']
