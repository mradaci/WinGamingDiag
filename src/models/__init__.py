"""
WinGamingDiag - Windows Gaming Diagnostic Agent
Core data models for system state, issues, and hardware components
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import hashlib


class IssueSeverity(Enum):
    """Severity levels for detected issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categories of issues"""
    HARDWARE = "hardware"
    SOFTWARE = "software"
    PERFORMANCE = "performance"
    STABILITY = "stability"
    SECURITY = "security"
    GAMING = "gaming"
    NETWORK = "network"


@dataclass
class Evidence:
    """Evidence supporting an issue diagnosis"""
    source: str  # Where this evidence came from (e.g., "WMI", "Event Log", "Registry")
    data: Any    # The actual evidence data
    timestamp: Optional[datetime] = None
    raw_value: Optional[str] = None  # Original value before processing
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Issue:
    """Represents a detected system issue"""
    id: str
    title: str
    description: str
    category: IssueCategory
    severity: IssueSeverity
    confidence: float  # 0.0 to 1.0
    evidence: List[Evidence] = field(default_factory=list)
    recommendation: str = ""
    auto_fixable: bool = False
    fix_commands: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # URLs to documentation
    related_issues: List[str] = field(default_factory=list)  # IDs of related issues
    
    def __post_init__(self):
        # Generate ID if not provided
        if not self.id:
            hash_input = f"{self.title}{self.description}{datetime.now().isoformat()}"
            self.id = hashlib.md5(hash_input.encode()).hexdigest()[:12]


@dataclass
class CPUInfo:
    """CPU information"""
    name: str
    manufacturer: str
    architecture: str
    cores: int
    threads: int
    base_clock_mhz: float
    max_clock_mhz: float
    current_clock_mhz: Optional[float] = None
    virtualization_enabled: bool = False
    virtualization_support: bool = False
    l3_cache_mb: Optional[float] = None
    socket: Optional[str] = None
    microcode: Optional[str] = None
    stepping: Optional[str] = None
    temperature_celsius: Optional[float] = None
    load_percent: Optional[float] = None


@dataclass
class MemoryInfo:
    """Memory/RAM information"""
    total_gb: float
    used_gb: float
    available_gb: float
    speed_mhz: Optional[int] = None
    type: Optional[str] = None  # DDR4, DDR5, etc.
    slots_used: int = 0
    slots_total: int = 0
    xmp_enabled: bool = False
    xmp_profile: Optional[str] = None
    voltage: Optional[float] = None
    timings: Optional[str] = None
    modules: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GPUInfo:
    """GPU/Graphics card information"""
    name: str
    manufacturer: str  # NVIDIA, AMD, Intel
    vram_mb: int
    driver_version: str
    driver_date: Optional[str] = None
    whql_signed: bool = False
    
    # Clock speeds
    core_clock_mhz: Optional[int] = None
    memory_clock_mhz: Optional[int] = None
    boost_clock_mhz: Optional[int] = None
    
    # Temperature & Power
    temperature_celsius: Optional[float] = None
    power_draw_watts: Optional[float] = None
    power_limit_watts: Optional[float] = None
    
    # Utilization
    gpu_utilization: Optional[float] = None
    vram_utilization: Optional[float] = None
    
    # Display outputs
    connected_displays: int = 0
    display_outputs: List[str] = field(default_factory=list)
    
    # API Support
    directx_version: Optional[str] = None
    vulkan_support: bool = False
    opengl_version: Optional[str] = None
    
    # Features
    ray_tracing: bool = False
    dlss_support: bool = False
    fsr_support: bool = False
    gsync_support: bool = False
    freesync_support: bool = False


@dataclass
class StorageInfo:
    """Storage device information"""
    model: str
    interface: str  # NVMe, SATA, USB, etc.
    type: str  # SSD, HDD, etc.
    total_gb: float
    used_gb: float
    free_gb: float
    
    # Health
    health_percent: Optional[float] = None
    temperature_celsius: Optional[float] = None
    power_on_hours: Optional[int] = None
    
    # Performance
    read_speed_mbps: Optional[float] = None
    write_speed_mbps: Optional[float] = None
    
    # Partition info
    partitions: List[Dict[str, Any]] = field(default_factory=list)
    drive_letter: Optional[str] = None
    is_system_drive: bool = False
    
    # SMART data (if available)
    smart_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MotherboardInfo:
    """Motherboard information"""
    manufacturer: str
    model: str
    version: str
    serial_number: Optional[str] = None
    bios_version: str = ""
    bios_date: Optional[str] = None
    bios_mode: Optional[str] = None  # UEFI or Legacy
    
    # Chipset
    chipset: Optional[str] = None
    
    # Features
    secure_boot_enabled: bool = False
    tpm_version: Optional[str] = None
    tpm_enabled: bool = False


@dataclass
class CoolingInfo:
    """Cooling system information"""
    cpu_fan_rpm: Optional[int] = None
    case_fans: List[Dict[str, Any]] = field(default_factory=list)
    
    # Water cooling (if detected)
    water_cooling_detected: bool = False
    pump_rpm: Optional[int] = None
    flow_rate: Optional[float] = None  # L/min
    coolant_temp: Optional[float] = None


@dataclass
class PowerInfo:
    """Power supply information"""
    estimated_wattage: Optional[int] = None
    psu_model: Optional[str] = None
    efficiency_rating: Optional[str] = None  # 80 Plus rating
    
    # Power consumption
    total_power_draw: Optional[float] = None


@dataclass
class HardwareSnapshot:
    """Complete hardware inventory"""
    cpu: Optional[CPUInfo] = None
    memory: Optional[MemoryInfo] = None
    gpus: List[GPUInfo] = field(default_factory=list)
    storage_devices: List[StorageInfo] = field(default_factory=list)
    motherboard: Optional[MotherboardInfo] = None
    cooling: Optional[CoolingInfo] = None
    power: Optional[PowerInfo] = None
    
    # Peripherals
    monitors: List[Dict[str, Any]] = field(default_factory=list)
    peripherals: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HardwareSnapshot':
        """Creates a HardwareSnapshot from a dictionary."""
        return cls(
            cpu=CPUInfo(**data['cpu']) if data.get('cpu') else None,
            memory=MemoryInfo(**data['memory']) if data.get('memory') else None,
            gpus=[GPUInfo(**gpu_data) for gpu_data in data.get('gpus', [])],
            storage_devices=[StorageInfo(**storage_data) for storage_data in data.get('storage_devices', [])],
            motherboard=MotherboardInfo(**data['motherboard']) if data.get('motherboard') else None,
            cooling=CoolingInfo(**data['cooling']) if data.get('cooling') else None,
            power=PowerInfo(**data['power']) if data.get('power') else None,
        )



@dataclass
class WindowsInfo:
    """Windows operating system information"""
    version: str
    build: str
    edition: str  # Home, Pro, Enterprise, etc.
    architecture: str  # 64-bit or 32-bit
    install_date: Optional[str] = None
    activation_status: str = "Unknown"
    
    # Updates
    last_update_check: Optional[str] = None
    pending_updates: int = 0
    update_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Features
    game_mode_enabled: bool = False
    hardware_gpu_scheduling: bool = False
    variable_refresh_rate: bool = False
    auto_hdr: bool = False


@dataclass
class SystemSnapshot:
    """Complete system state at a point in time"""
    timestamp: datetime
    hardware: HardwareSnapshot
    windows: WindowsInfo
    
    # Runtime metrics
    uptime_seconds: float = 0.0
    boot_time: Optional[datetime] = None
    
    # Collected metadata
    collection_duration_seconds: float = 0.0
    collectors_used: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    
    # Phase 2 Results (stored as Any to avoid circular imports)
    event_summary: Any = None
    driver_result: Any = None
    launcher_result: Any = None
    network_result: Any = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class DiagnosticResult:
    """Complete diagnostic result"""
    snapshot: SystemSnapshot
    issues: List[Issue] = field(default_factory=list)
    
    # Metadata
    scan_id: str = ""
    scan_version: str = "1.0.0"
    scan_duration_seconds: float = 0.0
    
    # Summary statistics
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    def __post_init__(self):
        if not self.scan_id:
            self.scan_id = hashlib.sha256(
                f"{self.snapshot.timestamp.isoformat()}".encode()
            ).hexdigest()[:16]
        
        # Calculate severity counts
        for issue in self.issues:
            if issue.severity == IssueSeverity.CRITICAL:
                self.critical_count += 1
            elif issue.severity == IssueSeverity.HIGH:
                self.high_count += 1
            elif issue.severity == IssueSeverity.MEDIUM:
                self.medium_count += 1
            else:
                self.low_count += 1
    
    @property
    def health_score(self) -> int:
        """Calculate overall health score (0-100)"""
        if not self.issues:
            return 100
        
        # Weight issues by severity
        weights = {
            IssueSeverity.CRITICAL: 25,
            IssueSeverity.HIGH: 15,
            IssueSeverity.MEDIUM: 5,
            IssueSeverity.LOW: 1
        }
        
        total_penalty = sum(
            weights.get(issue.severity, 0) 
            for issue in self.issues
        )
        
        return max(0, 100 - total_penalty)


__all__ = [
    'IssueSeverity',
    'IssueCategory', 
    'Evidence',
    'Issue',
    'CPUInfo',
    'MemoryInfo',
    'GPUInfo',
    'StorageInfo',
    'MotherboardInfo',
    'CoolingInfo',
    'PowerInfo',
    'HardwareSnapshot',
    'WindowsInfo',
    'SystemSnapshot',
    'DiagnosticResult'
]
