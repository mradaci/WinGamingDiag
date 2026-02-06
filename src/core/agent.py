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
        
        # Create system snapshot
        collection_duration = time.time() - start_time
        self.snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            hardware=hardware_snapshot,
            windows=windows_info,
            collection_duration_seconds=collection_duration,
            collectors_used=['hardware', 'windows'],
            errors_encountered=self.errors
        )
        
        self.ui.show_collection_complete(collection_duration, 2)
        
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
    
    def _collect_hardware_info(self) -> HardwareSnapshot:
        """Collect hardware information"""
        progress = self.ui.progress_bar(6, title="Collecting Hardware Data")
        
        try:
            snapshot = self.hardware_collector.collect_all()
            progress.finish("Hardware collection complete")
            
            # Collect any errors from hardware collector
            hw_errors = self.hardware_collector.get_errors()
            self.errors.extend(hw_errors)
            
            return snapshot
            
        except Exception as e:
            self.errors.append(f"Hardware collection error: {e}")
            self.ui.error(f"Error collecting hardware info: {e}")
            return HardwareSnapshot()
    
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
        if output_path is None:
            # Default to Desktop
            desktop = Path.home() / "Desktop"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = desktop / f"WinGamingDiag_Report_{timestamp}.txt"
        
        output_path = Path(output_path)
        
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return str(output_path)


__all__ = ['DiagnosticAgent']
