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
    SystemSnapshot, DiagnosticResult, Issue, WindowsInfo, HardwareSnapshot
)
from ..collectors.hardware import HardwareCollector
from ..collectors.event_logs import EventLogCollector, EventLogSummary
from ..collectors.drivers import DriverCompatibilityChecker, DriverCompatibilityResult
from ..collectors.launchers import GameLauncherDetector, GameLauncherResult
from ..collectors.network import NetworkDiagnostics, NetworkDiagnosticsResult
from ..collectors.prerequisites import PrerequisitesChecker, PrerequisitesResult
from ..collectors.processes import ProcessAnalyzer
from ..utils.benchmark import PerformanceBenchmark, BenchmarkSuite, BenchmarkSize
from ..utils.wmi_helper import get_wmi_helper
from ..utils.redaction import get_redactor
from ..utils.cli import ConsoleUI, create_default_ui
from .analysis import analyze_for_issues


class DiagnosticAgent:
    """
    Main diagnostic agent that orchestrates the entire diagnostic process.
    """
    
    def __init__(self, ui: Optional[ConsoleUI] = None, verbose: bool = False, quick_mode: bool = False):
        self.ui = ui or create_default_ui()
        self.verbose = verbose
        self.quick_mode = quick_mode
        self.wmi_helper = get_wmi_helper()
        self.redactor = get_redactor()
        
        self.hardware_collector = HardwareCollector(self.wmi_helper)
        self.event_collector = EventLogCollector(self.wmi_helper)
        self.driver_checker = DriverCompatibilityChecker(self.wmi_helper)
        self.launcher_detector = GameLauncherDetector(self.wmi_helper)
        self.network_diagnostics = NetworkDiagnostics(self.wmi_helper)
        self.prereq_checker = PrerequisitesChecker()
        self.process_analyzer = ProcessAnalyzer(self.wmi_helper)
        
        # Use smaller disk benchmark in quick mode
        bench_size = BenchmarkSize.QUICK if quick_mode else BenchmarkSize.DEFAULT
        self.benchmark = PerformanceBenchmark(disk_test_size=bench_size)
        
        self.snapshot: Optional[SystemSnapshot] = None
        self.issues: List[Issue] = []
        self.errors: List[str] = []
        
    def run_full_diagnostic(self) -> DiagnosticResult:
        start_time = time.time()
        
        self.ui.header("WinGamingDiag - System Diagnostic Tool")
        self.ui.show_collection_start()
        
        # Define all collectors
        collectors = {
            "Windows Info": self._collect_windows_info,
            "Hardware": self._collect_hardware_info,
            "Event Logs": self._collect_event_logs,
            "Drivers": self._check_drivers,
            "Game Launchers": self._detect_launchers,
            "Network": self._run_network_diagnostics,
            "Prerequisites": self._check_prerequisites,
            "Process Analysis": self._analyze_processes,
        }
        
        # Skip benchmarks in quick mode
        if not self.quick_mode:
            collectors["Benchmarks"] = self._run_benchmarks
        
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
            prerequisites_result=results.get("Prerequisites", PrerequisitesResult()),
            process_issues=results.get("Process Analysis", []),
            benchmark_result=results.get("Benchmarks", BenchmarkSuite(timestamp=datetime.now(), total_duration_ms=0)),
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
        
        # EMERGENCY FALLBACK: Print summary directly to ensure user sees results
        print("\n" + "="*70, flush=True)
        print(f"DIAGNOSTIC COMPLETE - Health Score: {result.health_score}/100", flush=True)
        print(f"Issues Found: {len(result.issues)} (Critical: {result.critical_count}, High: {result.high_count}, Medium: {result.medium_count}, Low: {result.low_count})", flush=True)
        print("="*70, flush=True)
        
        # Ensure all output is flushed before returning
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        
        return result
    
    def _collect_windows_info(self) -> WindowsInfo:
        """Collect Windows OS information"""
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                os_info = self.wmi_helper.get_operating_system_info()
                if os_info:
                    # Get Windows feature states
                    game_mode = self._check_game_mode_enabled()
                    hw_gpu_sched = self._check_hardware_gpu_scheduling()
                    
                    return WindowsInfo(
                        version=os_info.get('Version', 'Unknown'),
                        build=os_info.get('BuildNumber', 'Unknown'),
                        edition=os_info.get('Caption', 'Unknown'),
                        architecture=os_info.get('OSArchitecture', 'Unknown'),
                        install_date=str(os_info.get('InstallDate')),
                        activation_status=self._get_activation_status(),
                        game_mode_enabled=game_mode,
                        hardware_gpu_scheduling=hw_gpu_sched
                    )
        except Exception as e:
            self.errors.append(f"Windows Info collection failed: {e}")
            logging.error("Windows Info collection failed.", exc_info=True)
            
        return WindowsInfo(version="Unknown", build="Unknown", edition="Unknown", architecture="Unknown")

    def _check_game_mode_enabled(self) -> bool:
        """Check if Windows Game Mode is enabled"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
            winreg.CloseKey(key)
            return val == 1
        except:
            return True  # Default is on
    
    def _check_hardware_gpu_scheduling(self) -> bool:
        """Check if Hardware-Accelerated GPU Scheduling is enabled"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "HwSchMode")
            winreg.CloseKey(key)
            return val == 2
        except:
            return False
    
    def _get_activation_status(self) -> str:
        """Get Windows activation status"""
        try:
            # Try WMI first
            result = self.wmi_helper.query("SoftwareLicensingProduct", 
                                          where_clause="Name like 'Windows%' AND PartialProductKey IS NOT NULL",
                                          first_only=True)
            if result.success and result.data:
                license_status = result.data.get('LicenseStatus')
                if license_status == 1:
                    return "Activated"
                elif license_status == 0:
                    return "Unlicensed"
                else:
                    return f"Status: {license_status}"
        except:
            pass
        return "Unknown"

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
        """Collect and analyze Windows Event Logs for crashes and errors"""
        try:
            return self.event_collector.collect_summary(days_back=7)
        except Exception as e:
            self.errors.append(f"Event logs collection failed: {e}")
            logging.error("Event logs collection failed.", exc_info=True)
            return EventLogSummary()

    def _check_drivers(self) -> DriverCompatibilityResult:
        try:
            return self.driver_checker.check_all_drivers()
        except Exception as e:
            self.errors.append(f"Driver check failed: {e}")
            logging.error("Driver check failed.", exc_info=True)
            return DriverCompatibilityResult()

    def _detect_launchers(self) -> GameLauncherResult:
        try:
            return self.launcher_detector.detect_all_launchers()
        except Exception as e:
            self.errors.append(f"Launcher detection failed: {e}")
            logging.error("Launcher detection failed.", exc_info=True)
            return GameLauncherResult()

    def _run_network_diagnostics(self) -> NetworkDiagnosticsResult:
        try:
            return self.network_diagnostics.run_diagnostics()
        except Exception as e:
            self.errors.append(f"Network diagnostics failed: {e}")
            logging.error("Network diagnostics failed.", exc_info=True)
            return NetworkDiagnosticsResult()

    def _check_prerequisites(self) -> PrerequisitesResult:
        """Check for gaming prerequisites (VC++, DirectX, Game Mode)"""
        try:
            return self.prereq_checker.check_all()
        except Exception as e:
            self.errors.append(f"Prerequisites check failed: {e}")
            logging.error("Prerequisites check failed.", exc_info=True)
            return PrerequisitesResult()

    def _analyze_processes(self) -> List:
        """Analyze running processes for bloatware and interferers"""
        try:
            issues = self.process_analyzer.check_processes()
            if issues and self.ui:
                self.ui.info(f"Found {len(issues)} potentially interfering processes")
            return issues
        except Exception as e:
            self.errors.append(f"Process analysis failed: {e}")
            logging.error("Process analysis failed.", exc_info=True)
            return []

    def _run_benchmarks(self) -> BenchmarkSuite:
        """Run performance benchmarks"""
        try:
            if self.ui:
                self.ui.info("Running CPU, Memory, and Disk benchmarks...")
            return self.benchmark.run_benchmarks()
        except Exception as e:
            self.errors.append(f"Benchmarks failed: {e}")
            logging.error("Benchmarks failed.", exc_info=True)
            return BenchmarkSuite(timestamp=datetime.now(), total_duration_ms=0)
        
    def _display_results(self, result: DiagnosticResult):
        """Display diagnostic results to user"""
        self.ui.show_health_score(result.health_score)
        
        # Count issues by severity
        critical = result.critical_count
        high = result.high_count
        medium = result.medium_count
        low = result.low_count
        
        self.ui.show_issue_summary(critical, high, medium, low)
        
        # Display detailed issues (prioritize critical and high)
        display_count = 0
        max_display = 10
        
        # Show all critical issues
        for issue in result.issues:
            if issue.severity.value == "critical":
                self.ui.show_issue_detail(
                    issue.title, 
                    issue.severity.value,
                    issue.category.value,
                    issue.description,
                    issue.recommendation,
                    issue.confidence
                )
                display_count += 1
        
        # Show high issues if space permits
        for issue in result.issues:
            if issue.severity.value == "high" and display_count < max_display:
                self.ui.show_issue_detail(
                    issue.title, 
                    issue.severity.value,
                    issue.category.value,
                    issue.description,
                    issue.recommendation,
                    issue.confidence
                )
                display_count += 1
                
        # Show medium if space permits
        for issue in result.issues:
            if issue.severity.value == "medium" and display_count < max_display:
                self.ui.show_issue_detail(
                    issue.title, 
                    issue.severity.value,
                    issue.category.value,
                    issue.description,
                    issue.recommendation,
                    issue.confidence
                )
                display_count += 1
                
        if len(result.issues) > display_count:
            print(f"\n... and {len(result.issues) - display_count} more issues not shown in summary.")
            
        # Show benchmark summary if available
        if (result.snapshot.benchmark_result and 
            result.snapshot.benchmark_result.results and 
            not self.quick_mode):
            self.ui.subheader("Performance Benchmarks")
            for bench in result.snapshot.benchmark_result.results:
                if 'error' not in bench.details:
                    self.ui.metric(bench.name, f"{bench.score:.2f}", bench.unit, indent=1)

    def save_report(self, result: DiagnosticResult, output_path: Optional[str] = None) -> str:
        """Save diagnostic report to file"""
        try:
            from pathlib import Path
            import json
            from dataclasses import asdict
            import os
            
            # Default to desktop, fallback to current directory
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"WinGamingDiag_Report_{timestamp}.txt"
                
                # Try Desktop first
                desktop = Path.home() / "Desktop"
                if desktop.exists() and os.access(desktop, os.W_OK):
                    output_path = desktop / filename
                else:
                    # Fallback to current directory
                    output_path = Path(filename)
            else:
                output_path = Path(output_path)
            
            # Generate report content
            lines = []
            lines.append("=" * 70)
            lines.append("WinGamingDiag - System Diagnostic Report")
            lines.append("=" * 70)
            lines.append(f"Scan ID: {result.scan_id}")
            lines.append(f"Timestamp: {result.snapshot.timestamp}")
            lines.append(f"Duration: {result.scan_duration_seconds:.2f} seconds")
            lines.append(f"Health Score: {result.health_score}/100")
            lines.append("")
            
            lines.append("-" * 70)
            lines.append("ISSUE SUMMARY")
            lines.append("-" * 70)
            lines.append(f"Critical: {result.critical_count}")
            lines.append(f"High: {result.high_count}")
            lines.append(f"Medium: {result.medium_count}")
            lines.append(f"Low: {result.low_count}")
            lines.append("")
            
            if result.issues:
                lines.append("-" * 70)
                lines.append("DETAILED FINDINGS")
                lines.append("-" * 70)
                for issue in result.issues:
                    lines.append("")
                    lines.append(f"[{issue.severity.value.upper()}] {issue.title}")
                    lines.append(f"Category: {issue.category.value}")
                    lines.append(f"Confidence: {issue.confidence*100:.0f}%")
                    lines.append("")
                    lines.append(issue.description)
                    lines.append("")
                    lines.append(f"Recommendation: {issue.recommendation}")
                    lines.append("-" * 70)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return str(output_path)
            
        except Exception as e:
            self.errors.append(f"Failed to save report: {e}")
            logging.error("Report save failed.", exc_info=True)
            return ""

__all__ = ['DiagnosticAgent']
