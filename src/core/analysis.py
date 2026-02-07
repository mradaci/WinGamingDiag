"""
WinGamingDiag - Analysis Engine
Analyzes system snapshot to identify specific issues and generate recommendations
"""

from typing import List, Optional
from ..models import (
    SystemSnapshot, Issue, IssueSeverity, IssueCategory, Evidence
)
from ..utils.cli import ConsoleUI

def analyze_for_issues(snapshot: SystemSnapshot, ui: Optional[ConsoleUI] = None) -> List[Issue]:
    """
    Analyze the system snapshot and return a list of detected issues.
    
    This is the core intelligence that converts raw system data into
    actionable gaming performance recommendations.
    """
    issues = []
    
    # 1. Hardware Analysis
    if snapshot.hardware:
        # Memory Check
        if snapshot.hardware.memory:
            total_ram = snapshot.hardware.memory.total_gb
            if total_ram < 8:
                issues.append(Issue(
                    id="hw_low_ram_critical",
                    title="Critical Low Memory",
                    description=f"System has only {total_ram:.1f}GB of RAM. Modern gaming requires at least 8GB, preferably 16GB. This will cause severe performance issues and crashes in modern titles.",
                    category=IssueCategory.HARDWARE,
                    severity=IssueSeverity.CRITICAL,
                    confidence=1.0,
                    recommendation="Upgrade system RAM to at least 16GB for stable gaming performance. 8GB is the absolute minimum and will struggle with modern games.",
                    evidence=[Evidence(
                        source="Hardware Collector",
                        data={"total_ram_gb": total_ram, "recommended_minimum": 16}
                    )]
                ))
            elif total_ram < 16:
                issues.append(Issue(
                    id="hw_low_ram_warn",
                    title="Low Memory for Modern Games",
                    description=f"System has {total_ram:.1f}GB of RAM. While functional, 16GB is the recommended standard for modern titles and smooth multitasking.",
                    category=IssueCategory.HARDWARE,
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.9,
                    recommendation="Consider upgrading to 16GB RAM for better multitasking, smoother gameplay, and future-proofing."
                ))
            
            # Check memory speed (XMP detection)
            memory = snapshot.hardware.memory
            if memory.speed_mhz and memory.speed_mhz < 2400 and memory.type in ['DDR4', 'DDR5']:
                issues.append(Issue(
                    id="hw_slow_ram",
                    title="Slow Memory Speed Detected",
                    description=f"RAM running at {memory.speed_mhz}MHz. {memory.type} memory should run at 3000MHz+ for optimal gaming performance.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.85,
                    recommendation="Enable XMP/DOCP profile in BIOS to run RAM at rated speed. Check BIOS settings under Memory or Overclocking section."
                ))
                
        # Storage Check
        for drive in snapshot.hardware.storage_devices:
            if drive.is_system_drive and drive.type == 'HDD':
                issues.append(Issue(
                    id="hw_hdd_system",
                    title="System Running on Mechanical Hard Drive",
                    description="Windows is installed on a mechanical Hard Disk Drive (HDD). This significantly impacts boot times, system responsiveness, and game loading times.",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.HIGH,
                    confidence=1.0,
                    recommendation="Migrate Windows to an SSD (SATA or NVMe). This is the single most impactful upgrade for system responsiveness and game loading times."
                ))
            
            # Check for nearly full drives
            if drive.total_gb > 0:
                usage_percent = ((drive.total_gb - drive.free_gb) / drive.total_gb) * 100
                if usage_percent > 90:
                    issues.append(Issue(
                        id=f"hw_disk_full_{drive.model[:20]}",
                        title=f"Drive Nearly Full: {drive.model[:30]}",
                        description=f"Drive is {usage_percent:.1f}% full ({drive.free_gb:.1f}GB free). Low disk space causes performance degradation and update failures.",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.HIGH,
                        confidence=1.0,
                        recommendation="Free up disk space immediately. Delete unnecessary files, uninstall unused games, or move data to external storage. Windows needs at least 10-15GB free for updates."
                    ))
        
        # GPU Checks
        if snapshot.hardware.gpus:
            for gpu in snapshot.hardware.gpus:
                # Check for very old drivers
                if gpu.driver_date:
                    try:
                        from datetime import datetime
                        driver_date = datetime.strptime(gpu.driver_date, '%Y-%m-%d')
                        days_old = (datetime.now() - driver_date).days
                        if days_old > 180:
                            issues.append(Issue(
                                id=f"hw_old_gpu_driver_{gpu.name[:20]}",
                                title=f"Outdated GPU Driver: {gpu.name[:40]}",
                                description=f"GPU driver is {days_old} days old (from {gpu.driver_date}). Old drivers may cause crashes, poor performance, and missing features.",
                                category=IssueCategory.GAMING,
                                severity=IssueSeverity.HIGH,
                                confidence=0.9,
                                recommendation=f"Update {gpu.manufacturer} drivers. Use GeForce Experience (NVIDIA), AMD Adrenalin, or Intel Arc Control for latest updates."
                            ))
                    except:
                        pass
        
        # CPU Temperature Check (if available)
        if snapshot.hardware.cpu and snapshot.hardware.cpu.temperature_celsius:
            temp = snapshot.hardware.cpu.temperature_celsius
            if temp > 85:
                issues.append(Issue(
                    id="hw_cpu_overheating",
                    title="CPU Overheating Detected",
                    description=f"CPU temperature is {temp}°C. This is dangerously high and will cause thermal throttling, reduced performance, and potential hardware damage.",
                    category=IssueCategory.HARDWARE,
                    severity=IssueSeverity.CRITICAL,
                    confidence=0.95,
                    recommendation="Check CPU cooling immediately: 1) Clean dust from heatsink and fans, 2) Ensure proper airflow in case, 3) Check thermal paste (may need reapplication), 4) Verify fans are spinning properly"
                ))
            elif temp > 75:
                issues.append(Issue(
                    id="hw_cpu_hot",
                    title="CPU Running Hot",
                    description=f"CPU temperature is {temp}°C. This is above ideal operating temperatures and may cause performance degradation during gaming.",
                    category=IssueCategory.HARDWARE,
                    severity=IssueSeverity.MEDIUM,
                    confidence=0.85,
                    recommendation="Improve cooling: Clean dust from PC, ensure good case airflow, check that CPU cooler is properly seated."
                ))

    # 2. Prerequisites Analysis
    if snapshot.prerequisites_result:
        for item in snapshot.prerequisites_result.items:
            if not item.installed and item.critical:
                issues.append(Issue(
                    id=f"prereq_missing_{item.name.replace(' ', '_').lower()}",
                    title=f"Missing Critical Component: {item.name}",
                    description=f"{item.name} is not detected. {item.details} Many games will fail to launch without this.",
                    category=IssueCategory.GAMING,
                    severity=IssueSeverity.HIGH,
                    confidence=1.0,
                    recommendation="Download and install from Microsoft's official website. This is a fundamental requirement for most modern games."
                ))
        
        if not snapshot.prerequisites_result.game_mode_enabled:
            issues.append(Issue(
                id="conf_game_mode_off",
                title="Windows Game Mode Disabled",
                description="Windows Game Mode is currently turned off. This feature helps prioritize game processes and reduce background task interruptions.",
                category=IssueCategory.GAMING,
                severity=IssueSeverity.LOW,
                confidence=0.9,
                recommendation="Enable Game Mode in Windows Settings > Gaming > Game Mode. This can help reduce background interruptions during gameplay."
            ))

    # 3. Process Analysis (Bloatware)
    if snapshot.process_issues:
        for p_issue in snapshot.process_issues:
            # Determine severity based on process type
            severity = IssueSeverity.MEDIUM
            if any(x in p_issue.name.lower() for x in ['antivirus', 'security', 'mcafee', 'norton']):
                severity = IssueSeverity.HIGH
            
            issues.append(Issue(
                id=f"proc_bloat_{p_issue.name.replace('.', '_')}",
                title=f"Background Process Interfering: {p_issue.name}",
                description=f"Process '{p_issue.name}' (PID: {p_issue.pid}) is running. {p_issue.description}",
                category=IssueCategory.PERFORMANCE,
                severity=severity,
                confidence=0.8,
                recommendation="Close this application before gaming to free up resources and prevent background activity that can cause frame drops or stutters."
            ))

    # 4. Network Analysis
    if snapshot.network_result:
        if not snapshot.network_result.is_connected:
            issues.append(Issue(
                id="net_no_connection",
                title="No Network Connection",
                description="System is not connected to the internet. This will prevent online gaming, game updates, and DRM verification.",
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.HIGH,
                confidence=1.0,
                recommendation="Check network cable, WiFi connection, or network adapter settings."
            ))
        else:
            for issue_text in snapshot.network_result.issues:
                severity = IssueSeverity.MEDIUM
                if "high latency" in issue_text.lower():
                    severity = IssueSeverity.HIGH
                elif "packet loss" in issue_text.lower():
                    severity = IssueSeverity.HIGH
                
                issues.append(Issue(
                    id=f"net_{abs(hash(issue_text)) % 10000}",
                    title="Network Issue Detected",
                    description=issue_text,
                    category=IssueCategory.NETWORK,
                    severity=severity,
                    confidence=0.9,
                    recommendation=snapshot.network_result.recommendations[0] if snapshot.network_result.recommendations else "Check your network connection and consider troubleshooting steps."
                ))
            
            # Check for WiFi vs Ethernet
            if snapshot.network_result.connection_type and snapshot.network_result.connection_type.value == 'wifi':
                issues.append(Issue(
                    id="net_wifi_gaming",
                    title="Using WiFi for Gaming",
                    description="System is connected via WiFi. While functional, WiFi can introduce latency spikes and packet loss compared to a wired Ethernet connection.",
                    category=IssueCategory.NETWORK,
                    severity=IssueSeverity.LOW,
                    confidence=0.85,
                    recommendation="For competitive gaming or best stability, use an Ethernet cable connection. If WiFi is necessary, ensure strong signal and 5GHz band."
                ))

    # 5. Benchmark Analysis
    if snapshot.benchmark_result and snapshot.benchmark_result.results:
        for bench in snapshot.benchmark_result.results:
            if bench.name == "Disk I/O (Seq)" and 'error' not in bench.details:
                write_speed = bench.details.get('write_speed_mbps', 0)
                read_speed = bench.details.get('read_speed_mbps', 0)
                
                if write_speed > 0 and write_speed < 100:
                    issues.append(Issue(
                        id="bench_slow_disk_write",
                        title="Poor Disk Write Performance",
                        description=f"Measured disk write speed is only {write_speed:.1f} MB/s. For an SSD, this indicates it may be full or failing. For an HDD, this is normal but slow.",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        confidence=1.0,
                        recommendation="If this is an SSD: check available space (should have 15%+ free), run manufacturer diagnostic tools, or consider replacement if old. If HDD, consider upgrading to SSD."
                    ))
                elif write_speed > 0 and write_speed < 50:
                    issues.append(Issue(
                        id="bench_very_slow_disk",
                        title="Very Poor Disk Performance",
                        description=f"Disk write speed is critically low at {write_speed:.1f} MB/s. This will cause extreme loading times and system lag.",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.HIGH,
                        confidence=1.0,
                        recommendation="This drive is severely underperforming. Check SMART status, disk health, available space. If SSD, may be failing. If HDD, consider immediate upgrade to SSD."
                    ))
    
    # 6. Driver Analysis
    if snapshot.driver_result:
        if snapshot.driver_result.critical > 0:
            for driver in snapshot.driver_result.critical_issues:
                issues.append(Issue(
                    id=f"driver_critical_{driver.name.replace(' ', '_')[:20]}",
                    title=f"Critical Driver Issue: {driver.name}",
                    description=f"Driver '{driver.name}' version {driver.version} is critically outdated or unsigned. This can cause system instability and crashes.",
                    category=IssueCategory.HARDWARE,
                    severity=IssueSeverity.CRITICAL,
                    confidence=0.95,
                    recommendation=f"Update {driver.name} immediately from {driver.update_url or 'manufacturer website'}. Critical driver issues can cause crashes and security vulnerabilities."
                ))
        
        if snapshot.driver_result.gpu_drivers:
            for gpu_driver in snapshot.driver_result.gpu_drivers:
                if hasattr(gpu_driver, 'status') and gpu_driver.status.value == 'update_available':
                    issues.append(Issue(
                        id=f"driver_gpu_update_{gpu_driver.name.replace(' ', '_')[:20]}",
                        title=f"GPU Driver Update Available: {gpu_driver.name}",
                        description=f"GPU driver {gpu_driver.version} has an update available (latest: {gpu_driver.latest_version}). Newer drivers often include game optimizations and bug fixes.",
                        category=IssueCategory.GAMING,
                        severity=IssueSeverity.MEDIUM,
                        confidence=0.9,
                        recommendation=f"Update to version {gpu_driver.latest_version} from {gpu_driver.update_url or 'manufacturer website'}. Game Ready drivers often improve performance in new releases."
                    ))
    
    # 7. Event Log Analysis (Crash Detection)
    if snapshot.event_summary:
        if hasattr(snapshot.event_summary, 'critical_errors') and snapshot.event_summary.critical_errors > 0:
            issues.append(Issue(
                id="sys_recent_crashes",
                title=f"Recent System Crashes Detected: {snapshot.event_summary.critical_errors}",
                description=f"Found {snapshot.event_summary.critical_errors} critical system errors in recent event logs. This indicates system instability.",
                category=IssueCategory.STABILITY,
                severity=IssueSeverity.HIGH,
                confidence=0.85,
                recommendation="Review detailed report for specific error codes. Common causes: faulty RAM, overheating, driver issues, or failing hardware. Check temperatures and run memory tests."
            ))
        
        if hasattr(snapshot.event_summary, 'app_crashes') and snapshot.event_summary.app_crashes > 0:
            issues.append(Issue(
                id="sys_app_crashes",
                title=f"Recent Application Crashes: {snapshot.event_summary.app_crashes}",
                description=f"Detected {snapshot.event_summary.app_crashes} application crashes recently. This may indicate software conflicts or hardware issues.",
                category=IssueCategory.STABILITY,
                severity=IssueSeverity.MEDIUM,
                confidence=0.8,
                recommendation="Check if crashes correlate with specific games or applications. Update those applications and their dependencies. Verify system files with 'sfc /scannow'"
            ))
    
    # 8. Game Launcher Analysis
    if snapshot.launcher_result:
        running_count = len(snapshot.launcher_result.running_launchers)
        if running_count > 3:
            issues.append(Issue(
                id="launchers_too_many",
                title=f"Too Many Launchers Running: {running_count}",
                description=f"{running_count} game launchers are currently running. Each launcher consumes RAM and CPU resources, and their overlays can conflict.",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                confidence=0.9,
                recommendation="Close launchers you're not actively using. Keep only the one for the game you're playing open. Disable auto-start for launchers you rarely use."
            ))
    
    # Sort issues by severity
    severity_order = {
        IssueSeverity.CRITICAL: 0,
        IssueSeverity.HIGH: 1,
        IssueSeverity.MEDIUM: 2,
        IssueSeverity.LOW: 3
    }
    issues.sort(key=lambda x: severity_order.get(x.severity, 4))
    
    return issues
