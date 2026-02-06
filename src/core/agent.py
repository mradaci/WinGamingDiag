"""
WinGamingDiag - Core Diagnostic Agent
Main orchestrator that coordinates data collection, analysis, and reporting
"""

import sys
import time
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Import our modules
from ..models import (
    SystemSnapshot, DiagnosticResult, Issue, IssueSeverity,
    IssueCategory, Evidence, WindowsInfo, HardwareSnapshot
)
from ..collectors.hardware import HardwareCollector
from ..collectors.event_logs import EventLogCollector, EventLogSummary
from ..collectors.drivers import DriverCompatibilityChecker, DriverCompatibilityResult
from ..collectors.launchers import GameLauncherDetector, GameLauncherResult
from ..collectors.network import NetworkDiagnostics, NetworkDiagnosticsResult
from ..utils.wmi_helper import WMIHelper, get_wmi_helper
from ..utils.redaction import get_redactor
from ..utils.cli import ConsoleUI, create_default_ui


class DiagnosticAgent:
    """
    Main diagnostic agent that orchestrates the entire diagnostic process.
    Collects system data, analyzes for issues, and generates reports.
    """
    
    def __init__(self, ui: Optional[ConsoleUI] = None, verbose: bool = False):
        """
        Initialize diagnostic agent
        
        Args:
            ui: Console UI instance (creates default if not provided)
            verbose: Enable verbose output
        """
        self.ui = ui or create_default_ui()
        self.verbose = verbose
        self.wmi_helper = get_wmi_helper()
        self.redactor = get_redactor()
        
        # Collectors
        self.hardware_collector = HardwareCollector(self.wmi_helper)
        self.event_collector = EventLogCollector(self.wmi_helper)
        self.driver_checker = DriverCompatibilityChecker(self.wmi_helper)
        self.launcher_detector = GameLauncherDetector(self.wmi_helper)
        self.network_diagnostics = NetworkDiagnostics(self.wmi_helper)
        
        # Results
        self.snapshot: Optional[SystemSnapshot] = None
        self.issues: List[Issue] = []
        self.errors: List[str] = []
        
    def run_full_diagnostic(self) -> DiagnosticResult:
        """
        Run complete system diagnostic
        
        Returns:
            DiagnosticResult with snapshot and all detected issues
        """
        start_time = time.time()
        
        self.ui.header("WinGamingDiag - System Diagnostic Tool")
        self.ui.show_collection_start()
        
        # Phase 1: Collect Windows info
        self.ui.subheader("Collecting Windows System Information")
        windows_info = self._collect_windows_info()
        
        # Phase 2: Collect hardware info
        self.ui.subheader("Collecting Hardware Information")
        hardware_snapshot = self._collect_hardware_info()
        
        # Phase 3: Collect event logs (Phase 2)
        self.ui.subheader("Analyzing System Event Logs")
        event_summary = self._collect_event_logs()
        
        # Phase 4: Check driver compatibility (Phase 2)
        self.ui.subheader("Checking Driver Compatibility")
        driver_result = self._check_drivers()
        
        # Phase 5: Detect game launchers (Phase 2)
        self.ui.subheader("Detecting Game Launchers")
        launcher_result = self._detect_launchers()
        
        # Phase 6: Network diagnostics (Phase 2)
        self.ui.subheader("Running Network Diagnostics")
        network_result = self._run_network_diagnostics()
        
        # Create system snapshot
        collection_duration = time.time() - start_time
        self.snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            hardware=hardware_snapshot,
            windows=windows_info,
            collection_duration_seconds=collection_duration,
            collectors_used=['hardware', 'windows', 'event_logs', 'drivers', 'launchers', 'network'],
            errors_encountered=self.errors
        )
        
        # Store Phase 2 results in snapshot for later analysis
        self.snapshot.event_summary = event_summary
        self.snapshot.driver_result = driver_result
        self.snapshot.launcher_result = launcher_result
        self.snapshot.network_result = network_result
        
        self.ui.show_collection_complete(collection_duration, 6)
        
        # Phase 3: Analyze for issues
        self.ui.show_analysis_start()
        self.issues = self._analyze_for_issues()
        
        # Create final result
        total_duration = time.time() - start_time
        result = DiagnosticResult(
            snapshot=self.snapshot,
            issues=self.issues,
            scan_duration_seconds=total_duration
        )
        
        # Display results
        self._display_results(result)
        
        return result
    
    def _collect_windows_info(self) -> WindowsInfo:
        """Collect Windows operating system information"""
        windows_data = {}
        
        if not self.wmi_helper.is_available:
            self.ui.warning("WMI not available, using fallback methods")
            return self._collect_windows_fallback()
        
        # Progress bar for Windows collection
        progress = self.ui.progress_bar(4, title="Collecting Windows Data")
        
        try:
            # OS Info
            os_info = self.wmi_helper.get_operating_system_info()
            progress.update(1, "Operating System")
            
            windows_data['version'] = os_info.get('Caption', 'Unknown')
            windows_data['build'] = os_info.get('BuildNumber', 'Unknown')
            windows_data['architecture'] = os_info.get('OSArchitecture', 'Unknown')
            windows_data['install_date'] = str(os_info.get('InstallDate', ''))
            
            # System info
            sys_info = self.wmi_helper.get_computer_system_info()
            progress.update(1, "System Configuration")
            
            # Try to determine edition
            caption = os_info.get('Caption', '')
            if 'Pro' in caption:
                windows_data['edition'] = 'Pro'
            elif 'Home' in caption:
                windows_data['edition'] = 'Home'
            elif 'Enterprise' in caption:
                windows_data['edition'] = 'Enterprise'
            else:
                windows_data['edition'] = 'Unknown'
            
            # Activation status (simplified)
            windows_data['activation_status'] = 'Unknown'  # Would require registry check
            
            # Check Windows features
            progress.update(1, "Gaming Features")
            # These would require registry checks in real implementation
            windows_data['game_mode_enabled'] = False
            windows_data['hardware_gpu_scheduling'] = False
            windows_data['variable_refresh_rate'] = False
            windows_data['auto_hdr'] = False
            
            progress.update(1, "Complete")
            progress.finish()
            
        except Exception as e:
            self.errors.append(f"Windows info collection error: {e}")
            self.ui.error(f"Error collecting Windows info: {e}")
        
        return WindowsInfo(**windows_data)
    
    def _collect_windows_fallback(self) -> WindowsInfo:
        """Fallback Windows collection using platform module"""
        import platform
        
        return WindowsInfo(
            version=platform.version(),
            build=platform.version(),
            edition='Unknown',
            architecture=platform.machine(),
            install_date=None,
            activation_status='Unknown'
        )
    
import subprocess
import json
import tempfile

# ... (inside DiagnosticAgent class)

    def _collect_hardware_info_subprocess(self) -> HardwareSnapshot:
        """Runs the hardware collector in a separate process to isolate crashes."""
        logging.info("Hardware Collector: Starting subprocess.")
        snapshot = HardwareSnapshot()
        
        try:
            # Determine the path to the collector script
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # In a frozen app, the script is bundled with the exe
                base_path = Path(sys._MEIPASS)
                collector_script_path = base_path / 'src' / 'collectors' / 'collector_script.py'
            else:
                base_path = Path(__file__).parent.parent
                collector_script_path = base_path / 'collectors' / 'collector_script.py'
            
            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as tmpfile:
                output_path = tmpfile.name
            
            logging.info(f"Hardware Collector: Subprocess script path: {collector_script_path}")
            logging.info(f"Hardware Collector: Subprocess output file: {output_path}")

            # Run the collector script as a subprocess
            process = subprocess.run(
                [sys.executable, str(collector_script_path), output_path],
                capture_output=True,
                text=True,
                timeout=120  # 2-minute timeout
            )

            if process.returncode == 0:
                logging.info("Hardware Collector: Subprocess completed successfully.")
                # Read the output from the temporary file
                with open(output_path, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct the HardwareSnapshot from the dictionary
                # This needs to be more robust, parsing each dataclass
                snapshot = HardwareSnapshot.from_dict(data)
                self.errors.extend(data.get('errors', []))

            else:
                logging.error(f"Hardware Collector: Subprocess failed with return code {process.returncode}.")
                logging.error(f"Subprocess stdout: {process.stdout}")
                logging.error(f"Subprocess stderr: {process.stderr}")
                self.errors.append("Hardware collection subprocess failed.")

            # Clean up the temporary file
            Path(output_path).unlink()

        except subprocess.TimeoutExpired:
            logging.error("Hardware Collector: Subprocess timed out.")
            self.errors.append("Hardware collection timed out.")
        except Exception as e:
            logging.critical("Hardware Collector: Failed to run subprocess.", exc_info=True)
            self.errors.append(f"Failed to execute hardware collector subprocess: {e}")
            
        return snapshot

    def _collect_hardware_info(self) -> HardwareSnapshot:
        """Collect hardware information using the subprocess method."""
        return self._collect_hardware_info_subprocess()

    
    def _collect_event_logs(self) -> EventLogSummary:
        """Collect and analyze event logs"""
        try:
            summary = self.event_collector.collect_all()
            
            # Collect errors
            event_errors = self.event_collector.get_errors()
            self.errors.extend(event_errors)
            
            # Show summary
            if summary.gaming_related_events:
                self.ui.info(f"Found {len(summary.gaming_related_events)} gaming-related events")
            if summary.recent_crashes:
                self.ui.warning(f"Detected {len(summary.recent_crashes)} recent crashes")
            
            return summary
            
        except Exception as e:
            self.errors.append(f"Event log collection error: {e}")
            self.ui.error(f"Error collecting event logs: {e}")
            return EventLogSummary()
    
    def _check_drivers(self) -> DriverCompatibilityResult:
        """Check driver compatibility"""
        try:
            result = self.driver_checker.check_all_drivers()
            
            # Collect errors
            driver_errors = self.driver_checker.get_errors()
            self.errors.extend(driver_errors)
            
            # Show summary
            if result.critical > 0:
                self.ui.warning(f"{result.critical} critical driver(s) need attention")
            if result.update_available > 0:
                self.ui.info(f"{result.update_available} driver update(s) available")
            
            return result
            
        except Exception as e:
            self.errors.append(f"Driver check error: {e}")
            self.ui.error(f"Error checking drivers: {e}")
            return DriverCompatibilityResult()
    
    def _detect_launchers(self) -> GameLauncherResult:
        """Detect game launchers"""
        try:
            result = self.launcher_detector.detect_all_launchers()
            
            # Collect errors
            launcher_errors = self.launcher_detector.get_errors()
            self.errors.extend(launcher_errors)
            
            # Show summary
            if result.installed_launchers:
                self.ui.success(f"Found {len(result.installed_launchers)} game launcher(s)")
                self.ui.info(f"Total games detected: {result.total_games}")
            
            return result
            
        except Exception as e:
            self.errors.append(f"Launcher detection error: {e}")
            self.ui.error(f"Error detecting launchers: {e}")
            return GameLauncherResult()
    
    def _run_network_diagnostics(self) -> NetworkDiagnosticsResult:
        """Run network diagnostics"""
        try:
            result = self.network_diagnostics.run_diagnostics()
            
            # Collect errors
            network_errors = self.network_diagnostics.get_errors()
            self.errors.extend(network_errors)
            
            # Show summary
            if result.is_connected:
                conn_type = result.connection_type.value if result.connection_type else "unknown"
                self.ui.success(f"Network connected via {conn_type}")
                if result.dns_latency_ms:
                    self.ui.info(f"DNS latency: {result.dns_latency_ms:.1f}ms")
            else:
                self.ui.warning("No network connection detected")
            
            return result
            
        except Exception as e:
            self.errors.append(f"Network diagnostics error: {e}")
            self.ui.error(f"Error running network diagnostics: {e}")
            return NetworkDiagnosticsResult()
    
    def _analyze_for_issues(self) -> List[Issue]:
        """Analyze collected data for issues"""
        issues = []
        
        self.ui.info("Analyzing hardware configuration...")
        
        # Analyze CPU
        if self.snapshot and self.snapshot.hardware.cpu:
            cpu_issues = self._analyze_cpu(self.snapshot.hardware.cpu)
            issues.extend(cpu_issues)
        
        # Analyze Memory
        if self.snapshot and self.snapshot.hardware.memory:
            memory_issues = self._analyze_memory(self.snapshot.hardware.memory)
            issues.extend(memory_issues)
        
        # Analyze GPUs
        if self.snapshot and self.snapshot.hardware.gpus:
            for gpu in self.snapshot.hardware.gpus:
                gpu_issues = self._analyze_gpu(gpu)
                issues.extend(gpu_issues)
        
        # Analyze Storage
        if self.snapshot and self.snapshot.hardware.storage_devices:
            for storage in self.snapshot.hardware.storage_devices:
                storage_issues = self._analyze_storage(storage)
                issues.extend(storage_issues)
        
        # Phase 2: Analyze Event Logs
        if self.snapshot and self.snapshot.event_summary:
            event_issues = self._analyze_event_logs(self.snapshot.event_summary)
            issues.extend(event_issues)
        
        # Phase 2: Analyze Drivers
        if self.snapshot and self.snapshot.driver_result:
            driver_issues = self._analyze_drivers(self.snapshot.driver_result)
            issues.extend(driver_issues)
        
        # Phase 2: Analyze Launchers
        if self.snapshot and self.snapshot.launcher_result:
            launcher_issues = self._analyze_launchers(self.snapshot.launcher_result)
            issues.extend(launcher_issues)
        
        # Phase 2: Analyze Network
        if self.snapshot and self.snapshot.network_result:
            network_issues = self._analyze_network(self.snapshot.network_result)
            issues.extend(network_issues)
        
        return issues
    
    def _analyze_cpu(self, cpu) -> List[Issue]:
        """Analyze CPU for issues"""
        issues = []
        
        # Check for thermal throttling indicators
        if cpu.temperature_celsius and cpu.temperature_celsius > 85:
            issues.append(Issue(
                id="",
                title="CPU Running Hot",
                description=f"CPU temperature is {cpu.temperature_celsius}°C, which is above recommended levels",
                category=IssueCategory.HARDWARE,
                severity=IssueSeverity.HIGH,
                confidence=0.85,
                recommendation="Check CPU cooler installation, clean dust from heatsink, verify thermal paste",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"temperature": cpu.temperature_celsius},
                        raw_value=f"{cpu.temperature_celsius}C"
                    )
                ]
            ))
        
        # Check virtualization support for gaming VMs
        if not cpu.virtualization_support:
            issues.append(Issue(
                id="",
                title="Virtualization Not Supported",
                description="CPU does not support virtualization (VT-x/AMD-V)",
                category=IssueCategory.HARDWARE,
                severity=IssueSeverity.LOW,
                confidence=0.95,
                recommendation="Enable virtualization in BIOS if available. Not critical for most gaming.",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"virtualization": cpu.virtualization_support},
                        raw_value=str(cpu.virtualization_support)
                    )
                ]
            ))
        
        return issues
    
    def _analyze_memory(self, memory) -> List[Issue]:
        """Analyze memory for issues"""
        issues = []
        
        # Check memory usage
        usage_percent = (memory.used_gb / memory.total_gb * 100) if memory.total_gb > 0 else 0
        
        if usage_percent > 90:
            issues.append(Issue(
                id="",
                title="Critical Memory Usage",
                description=f"RAM is {usage_percent:.1f}% utilized ({memory.used_gb:.1f}GB / {memory.total_gb:.1f}GB)",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.CRITICAL,
                confidence=0.90,
                recommendation="Close unnecessary applications before gaming. Consider upgrading to 32GB for modern games.",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"usage_percent": usage_percent, "total": memory.total_gb, "used": memory.used_gb},
                        raw_value=f"{memory.used_gb}/{memory.total_gb}"
                    )
                ]
            ))
        elif usage_percent > 80:
            issues.append(Issue(
                id="",
                title="High Memory Usage",
                description=f"RAM is {usage_percent:.1f}% utilized",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation="Close browser tabs and background applications before gaming",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"usage_percent": usage_percent},
                        raw_value=f"{usage_percent}%"
                    )
                ]
            ))
        
        return issues
    
    def _analyze_gpu(self, gpu) -> List[Issue]:
        """Analyze GPU for issues"""
        issues = []
        
        # Check for outdated driver (simplified check)
        if gpu.driver_version:
            # This is a simplified check - real implementation would compare against latest
            issues.append(Issue(
                id="",
                title="GPU Driver Version",
                description=f"{gpu.manufacturer} {gpu.name} with driver {gpu.driver_version}",
                category=IssueCategory.GAMING,
                severity=IssueSeverity.LOW,
                confidence=0.60,
                recommendation="Verify you have the latest GPU driver from manufacturer website",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"driver": gpu.driver_version, "whql": gpu.whql_signed},
                        raw_value=gpu.driver_version
                    )
                ]
            ))
        
        # Check VRAM
        if gpu.vram_mb and gpu.vram_mb < 4096:
            issues.append(Issue(
                id="",
                title="Low GPU Memory",
                description=f"GPU has only {gpu.vram_mb}MB VRAM, which may limit game settings",
                category=IssueCategory.HARDWARE,
                severity=IssueSeverity.MEDIUM,
                confidence=0.80,
                recommendation="Consider lowering texture quality in games or upgrading GPU",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"vram_mb": gpu.vram_mb},
                        raw_value=f"{gpu.vram_mb}MB"
                    )
                ]
            ))
        
        return issues
    
    def _analyze_storage(self, storage) -> List[Issue]:
        """Analyze storage for issues"""
        issues = []
        
        # Check disk space
        if storage.total_gb > 0:
            usage_percent = (storage.used_gb / storage.total_gb) * 100
            
            if usage_percent > 95:
                issues.append(Issue(
                    id="",
                    title=f"Critical Disk Space on {storage.model}",
                    description=f"Drive is {usage_percent:.1f}% full ({storage.free_gb:.1f}GB remaining)",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.CRITICAL,
                    confidence=0.95,
                    recommendation="Free up space immediately. Games need free space for updates and virtual memory.",
                    evidence=[
                        Evidence(
                            source="WMI",
                            data={"usage_percent": usage_percent, "free_gb": storage.free_gb},
                            raw_value=f"{usage_percent}%"
                        )
                    ]
                ))
            elif usage_percent > 85:
                issues.append(Issue(
                    id="",
                    title=f"Low Disk Space on {storage.model}",
                    description=f"Drive is {usage_percent:.1f}% full",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.HIGH,
                    confidence=0.90,
                    recommendation="Consider cleaning up old games and files. Move games to external storage.",
                    evidence=[
                        Evidence(
                            source="WMI",
                            data={"usage_percent": usage_percent},
                            raw_value=f"{usage_percent}%"
                        )
                    ]
                ))
        
        # Check if HDD for system drive (slow)
        if storage.is_system_drive and storage.type == 'HDD':
            issues.append(Issue(
                id="",
                title="System Drive on HDD",
                description="Windows is installed on a mechanical hard drive, which impacts game loading times",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                confidence=0.90,
                recommendation="Consider migrating Windows and games to an SSD for significantly faster loading",
                evidence=[
                    Evidence(
                        source="WMI",
                        data={"type": storage.type, "is_system": storage.is_system_drive},
                        raw_value=storage.type
                    )
                ]
            ))
        
        return issues
    
    def _analyze_event_logs(self, event_summary) -> List[Issue]:
        """Analyze event logs for issues"""
        issues = []
        
        # Check for recent crashes
        if event_summary.recent_crashes:
            crash_count = len(event_summary.recent_crashes)
            if crash_count >= 3:
                issues.append(Issue(
                    id="",
                    title=f"Frequent Application Crashes ({crash_count} in last {event_summary.analysis_period_days} days)",
                    description=f"Detected {crash_count} application crashes or hangs in the past {event_summary.analysis_period_days} days",
                    category=IssueCategory.STABILITY,
                    severity=IssueSeverity.HIGH,
                    confidence=0.90,
                    recommendation="Check for overheating, update drivers, verify game files, check for conflicting software",
                    evidence=[
                        Evidence(
                            source="Event Log",
                            data={"crash_count": crash_count, "period_days": event_summary.analysis_period_days},
                            raw_value=str(crash_count)
                        )
                    ]
                ))
        
        # Check for gaming-related events
        if event_summary.gaming_related_events:
            gaming_event_count = len(event_summary.gaming_related_events)
            if gaming_event_count > 0:
                issues.append(Issue(
                    id="",
                    title=f"Gaming-Related System Events ({gaming_event_count})",
                    description=f"Found {gaming_event_count} gaming-related events in system logs",
                    category=IssueCategory.GAMING,
                    severity=IssueSeverity.LOW,
                    confidence=0.75,
                    recommendation="Review Windows Event Viewer for more details on these events",
                    evidence=[
                        Evidence(
                            source="Event Log",
                            data={"gaming_events": gaming_event_count},
                            raw_value=str(gaming_event_count)
                        )
                    ]
                ))
        
        return issues
    
    def _analyze_drivers(self, driver_result) -> List[Issue]:
        """Analyze drivers for issues"""
        issues = []
        
        # Check for critical driver issues
        if driver_result.critical > 0:
            issues.append(Issue(
                id="",
                title=f"Critical Driver Issues ({driver_result.critical})",
                description=f"Found {driver_result.critical} critical driver(s) that require immediate attention",
                category=IssueCategory.HARDWARE,
                severity=IssueSeverity.CRITICAL,
                confidence=0.95,
                recommendation="Update critical drivers immediately from manufacturer websites. GPU drivers are especially important for gaming.",
                evidence=[
                    Evidence(
                        source="Driver Check",
                        data={"critical_count": driver_result.critical},
                        raw_value=str(driver_result.critical)
                    )
                ]
            ))
        
        # Check for outdated drivers
        if driver_result.outdated > 0:
            issues.append(Issue(
                id="",
                title=f"Outdated Drivers ({driver_result.outdated})",
                description=f"Detected {driver_result.outdated} outdated driver(s)",
                category=IssueCategory.HARDWARE,
                severity=IssueSeverity.MEDIUM,
                confidence=0.85,
                recommendation="Update drivers for better performance and stability. Check manufacturer websites for latest versions.",
                evidence=[
                    Evidence(
                        source="Driver Check",
                        data={"outdated_count": driver_result.outdated},
                        raw_value=str(driver_result.outdated)
                    )
                ]
            ))
        
        # GPU driver specific check
        gpu_outdated = sum(1 for d in driver_result.gpu_drivers if hasattr(d, 'status') and d.status.value in ['update_available', 'outdated'])
        if gpu_outdated > 0:
            issues.append(Issue(
                id="",
                title="GPU Driver Update Available",
                description="Your graphics driver is not up to date",
                category=IssueCategory.GAMING,
                severity=IssueSeverity.HIGH,
                confidence=0.90,
                recommendation="Update GPU driver for better game performance and bug fixes. Use NVIDIA GeForce Experience, AMD Adrenalin, or Intel Arc Control.",
                evidence=[
                    Evidence(
                        source="Driver Check",
                        data={"gpu_outdated": True},
                        raw_value="GPU driver outdated"
                    )
                ]
            ))
        
        return issues
    
    def _analyze_launchers(self, launcher_result) -> List[Issue]:
        """Analyze game launchers for issues"""
        issues = []
        
        # Check for multiple overlays
        overlays_enabled = sum(1 for l in launcher_result.installed_launchers if hasattr(l, 'overlay_enabled') and l.overlay_enabled)
        if overlays_enabled > 1:
            issues.append(Issue(
                id="",
                title=f"Multiple Overlays Enabled ({overlays_enabled})",
                description="Multiple game launcher overlays are enabled, which may cause conflicts",
                category=IssueCategory.GAMING,
                severity=IssueSeverity.MEDIUM,
                confidence=0.80,
                recommendation="Disable overlays for launchers you don't use frequently. Steam, Discord, and NVIDIA overlays can conflict.",
                evidence=[
                    Evidence(
                        source="Launcher Detection",
                        data={"overlays_enabled": overlays_enabled},
                        raw_value=str(overlays_enabled)
                    )
                ]
            ))
        
        # Check for storage issues
        if launcher_result.storage_used_gb > 500:
            issues.append(Issue(
                id="",
                title=f"Large Game Library ({launcher_result.storage_used_gb:.1f} GB)",
                description="Your game library is consuming significant storage space",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.LOW,
                confidence=0.85,
                recommendation="Consider archiving unused games or moving them to external storage to free up space",
                evidence=[
                    Evidence(
                        source="Launcher Detection",
                        data={"storage_used_gb": launcher_result.storage_used_gb},
                        raw_value=f"{launcher_result.storage_used_gb:.1f} GB"
                    )
                ]
            ))
        
        # Check for auto-start launchers
        auto_start_count = sum(1 for l in launcher_result.installed_launchers if hasattr(l, 'auto_start') and l.auto_start)
        if auto_start_count > 2:
            issues.append(Issue(
                id="",
                title=f"Too Many Auto-Start Launchers ({auto_start_count})",
                description=f"{auto_start_count} game launchers are set to start with Windows",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.LOW,
                confidence=0.75,
                recommendation="Disable auto-start for launchers you don't use frequently to improve boot time",
                evidence=[
                    Evidence(
                        source="Launcher Detection",
                        data={"auto_start_count": auto_start_count},
                        raw_value=str(auto_start_count)
                    )
                ]
            ))
        
        return issues
    
    def _analyze_network(self, network_result) -> List[Issue]:
        """Analyze network configuration for issues"""
        issues = []
        
        # Check connectivity
        if not network_result.is_connected:
            issues.append(Issue(
                id="",
                title="No Network Connection",
                description="System is not connected to a network",
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.CRITICAL,
                confidence=0.99,
                recommendation="Check network cable, WiFi connection, or contact your ISP",
                evidence=[
                    Evidence(
                        source="Network Diagnostics",
                        data={"connected": False},
                        raw_value="Not connected"
                    )
                ]
            ))
            return issues
        
        # Check connection type
        if network_result.connection_type and network_result.connection_type.value == 'wifi':
            issues.append(Issue(
                id="",
                title="WiFi Connection Detected",
                description="Using WiFi connection which may have higher latency and packet loss",
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.LOW,
                confidence=0.85,
                recommendation="Consider using Ethernet connection for better gaming performance and lower latency",
                evidence=[
                    Evidence(
                        source="Network Diagnostics",
                        data={"connection_type": "wifi"},
                        raw_value="WiFi"
                    )
                ]
            ))
        
        # Check DNS latency
        if network_result.dns_latency_ms and network_result.dns_latency_ms > 100:
            issues.append(Issue(
                id="",
                title="High DNS Latency",
                description=f"DNS resolution is slow ({network_result.dns_latency_ms:.0f}ms)",
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.MEDIUM,
                confidence=0.80,
                recommendation="Consider switching to Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1)",
                evidence=[
                    Evidence(
                        source="Network Diagnostics",
                        data={"dns_latency_ms": network_result.dns_latency_ms},
                        raw_value=f"{network_result.dns_latency_ms:.0f}ms"
                    )
                ]
            ))
        
        # Check for gaming server latency issues
        high_latency_servers = [s for s in network_result.gaming_servers if s.avg_ms > 150]
        if high_latency_servers:
            issues.append(Issue(
                id="",
                title="High Latency to Gaming Servers",
                description=f"High ping detected to {len(high_latency_servers)} gaming server(s)",
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.MEDIUM,
                confidence=0.75,
                recommendation="High latency may affect online gaming. Check your internet connection or consider a gaming VPN",
                evidence=[
                    Evidence(
                        source="Network Diagnostics",
                        data={"high_latency_count": len(high_latency_servers)},
                        raw_value=f"{len(high_latency_servers)} servers"
                    )
                ]
            ))
        
        return issues
    
    def _display_results(self, result: DiagnosticResult):
        """Display diagnostic results to user"""
        self.ui.show_health_score(result.health_score)
        self.ui.show_issue_summary(
            result.critical_count,
            result.high_count,
            result.medium_count,
            result.low_count
        )
        
        # Show issue details
        if result.issues:
            self.ui.subheader("Detailed Findings")
            for issue in result.issues:
                self.ui.show_issue_detail(
                    title=issue.title,
                    severity=issue.severity.value,
                    category=issue.category.value,
                    description=issue.description,
                    recommendation=issue.recommendation,
                    confidence=issue.confidence
                )
    
    def save_report(self, result: DiagnosticResult, output_path: Optional[str] = None) -> str:
        """
        Save diagnostic report to file
        
        Args:
            result: Diagnostic result to save
            output_path: Path to save report (default: Desktop)
            
        Returns:
            Path to saved report
        """
        # Determine output path
        if output_path is None:
            # Default to Desktop
            desktop = Path.home() / "Desktop"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = desktop / f"WinGamingDiag_Report_{timestamp}.txt"
        else:
            output_file = Path(output_path)
        
        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate report content
        report_lines = [
            "=" * 70,
            "WinGamingDiag - System Diagnostic Report",
            "=" * 70,
            f"Generated: {result.snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Scan ID: {result.scan_id}",
            f"Duration: {result.scan_duration_seconds:.1f} seconds",
            "",
            f"HEALTH SCORE: {result.health_score}/100",
            "",
            "ISSUE SUMMARY:",
            f"  Critical: {result.critical_count}",
            f"  High: {result.high_count}",
            f"  Medium: {result.medium_count}",
            f"  Low: {result.low_count}",
            "",
            "=" * 70,
            "DETAILED FINDINGS",
            "=" * 70,
            ""
        ]
        
        for issue in result.issues:
            report_lines.extend([
                f"[{issue.severity.value.upper()}] {issue.title}",
                f"Category: {issue.category.value}",
                f"Confidence: {issue.confidence*100:.0f}%",
                "",
                f"Description: {issue.description}",
                "",
                f"Recommendation: {issue.recommendation}",
                "",
                "-" * 70,
                ""
            ])
        
        # Add system information
        report_lines.extend([
            "",
            "=" * 70,
            "SYSTEM INFORMATION",
            "=" * 70,
            ""
        ])
        
        if result.snapshot.hardware.cpu:
            cpu = result.snapshot.hardware.cpu
            report_lines.extend([
                "CPU:",
                f"  Model: {cpu.name}",
                f"  Cores/Threads: {cpu.cores}/{cpu.threads}",
                f"  Base Clock: {cpu.base_clock_mhz} MHz",
                ""
            ])
        
        if result.snapshot.hardware.memory:
            mem = result.snapshot.hardware.memory
            report_lines.extend([
                "Memory:",
                f"  Total: {mem.total_gb} GB",
                f"  Used: {mem.used_gb} GB",
                f"  Speed: {mem.speed_mhz} MHz" if mem.speed_mhz else "",
                ""
            ])
        
        # Write report
        with open(str(output_file), 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return str(output_file)


__all__ = ['DiagnosticAgent']
