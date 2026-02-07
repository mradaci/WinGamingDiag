"""
WinGamingDiag - Driver Compatibility Checker
Checks driver versions and compatibility for gaming hardware
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re


class DriverStatus(Enum):
    """Driver compatibility status"""
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"
    CRITICAL = "critical"


class DriverCategory(Enum):
    """Categories of drivers"""
    GPU = "gpu"
    AUDIO = "audio"
    NETWORK = "network"
    CHIPSET = "chipset"
    STORAGE = "storage"
    USB = "usb"
    OTHER = "other"


@dataclass
class DriverInfo:
    """Represents a driver information"""
    name: str
    provider: str
    version: str
    date: Optional[str] = None
    signer: Optional[str] = None
    status: DriverStatus = DriverStatus.UNKNOWN
    category: DriverCategory = DriverCategory.OTHER
    device_name: Optional[str] = None
    hardware_id: Optional[str] = None
    inf_name: Optional[str] = None
    is_signed: bool = False
    is_whql: bool = False
    latest_version: Optional[str] = None
    update_url: Optional[str] = None
    release_notes: Optional[str] = None


@dataclass
class DriverCompatibilityResult:
    """Result of driver compatibility check"""
    total_drivers: int = 0
    up_to_date: int = 0
    update_available: int = 0
    outdated: int = 0
    critical: int = 0
    unknown: int = 0
    
    gpu_drivers: List[DriverInfo] = field(default_factory=list)
    audio_drivers: List[DriverInfo] = field(default_factory=list)
    network_drivers: List[DriverInfo] = field(default_factory=list)
    other_drivers: List[DriverInfo] = field(default_factory=list)
    
    critical_issues: List[DriverInfo] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DriverCompatibilityChecker:
    """
    Checks driver versions and compatibility for gaming systems.
    Compares installed drivers against known latest versions.
    """
    
    # Known latest driver versions (as of early 2025)
    # In production, these would be fetched from manufacturer APIs
    LATEST_DRIVERS = {
        # NVIDIA GPUs
        'nvidia': {
            'game_ready': '551.23',
            'studio': '551.23',
            'minimum_gaming': '545.00'
        },
        # AMD GPUs
        'amd': {
            'adrenalin': '24.1.1',
            'pro': '23.Q4',
            'minimum_gaming': '23.12.1'
        },
        # Intel GPUs
        'intel': {
            'arc': '31.0.101.5084',
            'xe': '31.0.101.5084',
            'minimum_gaming': '31.0.101.5000'
        },
        # Audio
        'realtek': {
            'hd_audio': '6.0.9235.1',
            'minimum': '6.0.9000.0'
        },
        # Network
        'intel_network': {
            'ethernet': '28.0.0',
            'wifi': '23.0.0'
        }
    }
    
    # Critical driver patterns
    CRITICAL_DRIVERS = [
        'nvidia', 'amd', 'intel.*graphics', 'realtek.*audio',
        'intel.*network', 'killer', 'broadcom'
    ]
    
    def __init__(self, wmi_helper=None):
        """
        Initialize driver compatibility checker
        
        Args:
            wmi_helper: WMI helper instance
        """
        self.wmi_helper = wmi_helper
        self.errors: List[str] = []
        self._load_external_drivers_db()
        
    def _load_external_drivers_db(self):
        """Load external drivers.json if available for version updates"""
        import json
        import os
        import sys
        
        # Check multiple locations for drivers.json
        paths_to_check = [
            os.path.join(os.getcwd(), 'drivers.json'),
        ]
        
        # If running as frozen executable, check executable directory
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            paths_to_check.append(os.path.join(exe_dir, 'drivers.json'))
        
        # Also check script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        paths_to_check.append(os.path.join(script_dir, '..', '..', 'drivers.json'))
            
        for path in paths_to_check:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Validate it's a proper driver database
                        if isinstance(data, dict) and 'nvidia' in data:
                            # Deep merge with existing defaults
                            for vendor, details in data.items():
                                if vendor in self.LATEST_DRIVERS:
                                    self.LATEST_DRIVERS[vendor].update(details)
                                else:
                                    self.LATEST_DRIVERS[vendor] = details
                            self.errors.append(f"Loaded external driver DB from {path}")
                            break 
                except Exception as e:
                    self.errors.append(f"Failed to load external drivers DB from {path}: {e}")
        
    def check_all_drivers(self) -> DriverCompatibilityResult:
        """
        Check all installed drivers for compatibility
        
        Returns:
            DriverCompatibilityResult with check results
        """
        result = DriverCompatibilityResult()
        
        try:
            # Collect driver information
            drivers = self._collect_driver_info()
            result.total_drivers = len(drivers)
            
            # Analyze each driver
            for driver in drivers:
                self._analyze_driver(driver)
                
                # Categorize driver
                if driver.category == DriverCategory.GPU:
                    result.gpu_drivers.append(driver)
                elif driver.category == DriverCategory.AUDIO:
                    result.audio_drivers.append(driver)
                elif driver.category == DriverCategory.NETWORK:
                    result.network_drivers.append(driver)
                else:
                    result.other_drivers.append(driver)
                
                # Count by status
                if driver.status == DriverStatus.UP_TO_DATE:
                    result.up_to_date += 1
                elif driver.status == DriverStatus.UPDATE_AVAILABLE:
                    result.update_available += 1
                elif driver.status == DriverStatus.OUTDATED:
                    result.outdated += 1
                elif driver.status == DriverStatus.CRITICAL:
                    result.critical += 1
                    result.critical_issues.append(driver)
                else:
                    result.unknown += 1
            
            # Generate recommendations
            result.recommendations = self._generate_recommendations(result)
            
        except Exception as e:
            self.errors.append(f"Driver check failed: {e}")
        
        return result
    
    def _collect_driver_info(self) -> List[DriverInfo]:
        """Collect information about installed drivers"""
        drivers = []
        
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                # Get driver information from WMI
                driver_query = """
                    SELECT * FROM Win32_SystemDriver 
                    WHERE State = 'Running'
                """
                
                result = self.wmi_helper.query_raw(driver_query)
                
                if hasattr(result, 'success') and result.success:
                    for driver_data in result.data:
                        driver = self._parse_system_driver(driver_data)
                        if driver:
                            drivers.append(driver)
                
                # Get device drivers from PnP
                pnp_drivers = self._collect_pnp_drivers()
                drivers.extend(pnp_drivers)
            
            # Alternative: Use setupapi if available
            if not drivers:
                drivers = self._collect_drivers_setupapi()
                
        except Exception as e:
            self.errors.append(f"Driver collection error: {e}")
        
        return drivers
    
    def _parse_system_driver(self, driver_data: Dict[str, Any]) -> Optional[DriverInfo]:
        """Parse system driver data from WMI"""
        try:
            name = driver_data.get('Name', 'Unknown')
            provider = driver_data.get('ServiceType', 'Unknown')
            
            # Try to get more details from file
            pathname = driver_data.get('PathName', '')
            version = self._get_file_version(pathname) if pathname else 'Unknown'
            
            # Determine category
            category = self._categorize_driver(name, pathname)
            
            return DriverInfo(
                name=name,
                provider=provider,
                version=version,
                device_name=name,
                category=category
            )
            
        except Exception:
            return None
    
    def _collect_pnp_drivers(self) -> List[DriverInfo]:
        """Collect PnP signed drivers"""
        drivers = []
        
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                # Query signed drivers
                query = "SELECT * FROM Win32_PnPSignedDriver"
                result = self.wmi_helper.query_raw(query)
                
                if hasattr(result, 'success') and result.success:
                    for driver_data in result.data:
                        driver = self._parse_pnp_driver(driver_data)
                        if driver:
                            drivers.append(driver)
                            
        except Exception as e:
            self.errors.append(f"PnP driver collection error: {e}")
        
        return drivers
    
    def _parse_pnp_driver(self, driver_data: Dict[str, Any]) -> Optional[DriverInfo]:
        """Parse PnP signed driver data"""
        try:
            device_name = driver_data.get('DeviceName', 'Unknown Device')
            driver_provider = driver_data.get('DriverProviderName', 'Unknown')
            driver_version = driver_data.get('DriverVersion', 'Unknown')
            driver_date = driver_data.get('DriverDate')
            
            # Format date
            if driver_date and hasattr(driver_date, 'strftime'):
                driver_date = driver_date.strftime('%Y-%m-%d')
            
            # Check signer
            signer = driver_data.get('Signer', '')
            is_whql = 'Microsoft' in signer or 'WHQL' in signer
            is_signed = bool(signer)
            
            # Determine category
            device_id = driver_data.get('DeviceID', '')
            category = self._categorize_driver(device_name, device_id)
            
            # Check if it's a critical driver
            is_critical = self._is_critical_driver(device_name, driver_provider)
            
            return DriverInfo(
                name=device_name,
                provider=driver_provider,
                version=driver_version,
                date=driver_date,
                signer=signer,
                is_signed=is_signed,
                is_whql=is_whql,
                device_name=device_name,
                hardware_id=device_id,
                category=category
            )
            
        except Exception:
            return None
    
    def _collect_drivers_setupapi(self) -> List[DriverInfo]:
        """Collect drivers using setupapi (fallback)"""
        drivers = []
        
        try:
            import ctypes
            from ctypes import wintypes
            
            # This is a simplified version
            # Full implementation would enumerate all devices
            setupapi = ctypes.windll.setupapi
            
            # Enumerate device classes
            # Implementation would go here for detailed enumeration
            
        except ImportError:
            pass
        except Exception as e:
            self.errors.append(f"SetupAPI collection error: {e}")
        
        return drivers
    
    def _analyze_driver(self, driver: DriverInfo) -> None:
        """Analyze a driver for compatibility issues"""
        driver_name_lower = driver.name.lower()
        provider_lower = driver.provider.lower() if driver.provider else ''
        
        # Check GPU drivers
        if driver.category == DriverCategory.GPU:
            self._analyze_gpu_driver(driver)
        
        # Check audio drivers
        elif driver.category == DriverCategory.AUDIO:
            self._analyze_audio_driver(driver)
        
        # Check if driver is unsigned
        if not driver.is_signed and driver.category in [DriverCategory.GPU, DriverCategory.AUDIO]:
            driver.status = DriverStatus.CRITICAL
            return
        
        # Check version against known versions
        latest = self._get_latest_version(driver)
        if latest and driver.version != 'Unknown':
            comparison = self._compare_versions(driver.version, latest)
            
            if comparison < 0:
                driver.status = DriverStatus.UPDATE_AVAILABLE
                driver.latest_version = latest
            elif comparison == 0:
                driver.status = DriverStatus.UP_TO_DATE
            else:
                driver.status = DriverStatus.UP_TO_DATE  # Newer than known
    
    def _analyze_gpu_driver(self, driver: DriverInfo) -> None:
        """Analyze GPU driver specifically"""
        driver_name = driver.name.lower()
        
        if 'nvidia' in driver_name or 'geforce' in driver_name:
            minimum = self.LATEST_DRIVERS['nvidia']['minimum_gaming']
            latest = self.LATEST_DRIVERS['nvidia']['game_ready']
            
            if driver.version != 'Unknown':
                if self._compare_versions(driver.version, minimum) < 0:
                    driver.status = DriverStatus.CRITICAL
                elif self._compare_versions(driver.version, latest) < 0:
                    driver.status = DriverStatus.UPDATE_AVAILABLE
                    driver.latest_version = latest
                else:
                    driver.status = DriverStatus.UP_TO_DATE
                
                driver.update_url = 'https://www.nvidia.com/drivers'
        
        elif 'amd' in driver_name or 'radeon' in driver_name:
            minimum = self.LATEST_DRIVERS['amd']['minimum_gaming']
            latest = self.LATEST_DRIVERS['amd']['adrenalin']
            
            if driver.version != 'Unknown':
                if self._compare_versions(driver.version, minimum) < 0:
                    driver.status = DriverStatus.CRITICAL
                elif self._compare_versions(driver.version, latest) < 0:
                    driver.status = DriverStatus.UPDATE_AVAILABLE
                    driver.latest_version = latest
                else:
                    driver.status = DriverStatus.UP_TO_DATE
                
                driver.update_url = 'https://www.amd.com/support'
        
        elif 'intel' in driver_name and ('arc' in driver_name or 'xe' in driver_name):
            minimum = self.LATEST_DRIVERS['intel']['minimum_gaming']
            latest = self.LATEST_DRIVERS['intel']['arc']
            
            if driver.version != 'Unknown':
                if self._compare_versions(driver.version, minimum) < 0:
                    driver.status = DriverStatus.CRITICAL
                elif self._compare_versions(driver.version, latest) < 0:
                    driver.status = DriverStatus.UPDATE_AVAILABLE
                    driver.latest_version = latest
                else:
                    driver.status = DriverStatus.UP_TO_DATE
                
                driver.update_url = 'https://www.intel.com/content/www/us/en/download-center'
    
    def _analyze_audio_driver(self, driver: DriverInfo) -> None:
        """Analyze audio driver"""
        driver_name = driver.name.lower()
        
        if 'realtek' in driver_name:
            minimum = self.LATEST_DRIVERS['realtek']['minimum']
            
            if driver.version != 'Unknown':
                if self._compare_versions(driver.version, minimum) < 0:
                    driver.status = DriverStatus.UPDATE_AVAILABLE
                else:
                    driver.status = DriverStatus.UP_TO_DATE
    
    def _categorize_driver(self, name: str, device_id: str) -> DriverCategory:
        """Categorize a driver based on name and device ID"""
        name_lower = name.lower()
        device_lower = device_id.lower()
        
        if any(kw in name_lower for kw in ['nvidia', 'amd', 'radeon', 'geforce', 'intel.*graphics', 'display']):
            return DriverCategory.GPU
        elif any(kw in name_lower for kw in ['audio', 'sound', 'realtek']):
            return DriverCategory.AUDIO
        elif any(kw in name_lower for kw in ['network', 'ethernet', 'wifi', 'wireless', 'killer', 'broadcom']):
            return DriverCategory.NETWORK
        elif any(kw in name_lower for kw in ['chipset', 'sata', 'intel.*management']):
            return DriverCategory.CHIPSET
        elif any(kw in name_lower for kw in ['storage', 'nvme', 'sata', 'intel.*rst']):
            return DriverCategory.STORAGE
        elif any(kw in name_lower for kw in ['usb', ' xhci']):
            return DriverCategory.USB
        else:
            return DriverCategory.OTHER
    
    def _is_critical_driver(self, name: str, provider: str) -> bool:
        """Check if a driver is critical for gaming"""
        name_lower = name.lower()
        provider_lower = provider.lower() if provider else ''
        
        for pattern in self.CRITICAL_DRIVERS:
            if re.search(pattern, name_lower) or re.search(pattern, provider_lower):
                return True
        return False
    
    def _get_latest_version(self, driver: DriverInfo) -> Optional[str]:
        """Get latest known version for a driver"""
        name_lower = driver.name.lower()
        
        if 'nvidia' in name_lower or 'geforce' in name_lower:
            return self.LATEST_DRIVERS['nvidia']['game_ready']
        elif 'amd' in name_lower or 'radeon' in name_lower:
            return self.LATEST_DRIVERS['amd']['adrenalin']
        elif 'intel' in name_lower and 'graphics' in name_lower:
            return self.LATEST_DRIVERS['intel']['arc']
        
        return None
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings
        Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        try:
            # Extract numeric parts
            v1_parts = re.findall(r'\d+', str(version1))
            v2_parts = re.findall(r'\d+', str(version2))
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend(['0'] * (max_len - len(v1_parts)))
            v2_parts.extend(['0'] * (max_len - len(v2_parts)))
            
            # Compare parts
            for i in range(max_len):
                if int(v1_parts[i]) < int(v2_parts[i]):
                    return -1
                elif int(v1_parts[i]) > int(v2_parts[i]):
                    return 1
            
            return 0
        except:
            return 0
    
    def _get_file_version(self, filepath: str) -> str:
        """Get version from file"""
        try:
            import ctypes
            from ctypes import wintypes
            
            wapi = ctypes.windll.version
            
            # Get file version info size
            dwLen = wapi.GetFileVersionInfoSizeW(filepath, None)
            if dwLen == 0:
                return 'Unknown'
            
            # Get version info
            buf = ctypes.create_string_buffer(dwLen)
            wapi.GetFileVersionInfoW(filepath, 0, dwLen, buf)
            
            # Query version value
            uLen = wintypes.UINT()
            lpBuf = ctypes.c_void_p()
            
            if wapi.VerQueryValueW(buf, r'\\VarFileInfo\\Translation', ctypes.byref(lpBuf), ctypes.byref(uLen)):
                lang = ctypes.cast(lpBuf, ctypes.POINTER(wintypes.DWORD)).contents.value
                
                str_info = f'\\StringFileInfo\\{lang:08x}\\FileVersion'
                
                if wapi.VerQueryValueW(buf, str_info, ctypes.byref(lpBuf), ctypes.byref(uLen)):
                    return ctypes.wstring_at(lpBuf.value)
            
            return 'Unknown'
            
        except:
            return 'Unknown'
    
    def _generate_recommendations(self, result: DriverCompatibilityResult) -> List[str]:
        """Generate recommendations based on driver check results"""
        recommendations = []
        
        if result.critical > 0:
            recommendations.append(
                f"CRITICAL: {result.critical} driver(s) require immediate update. "
                "These may cause crashes or stability issues."
            )
        
        if result.update_available > 0:
            recommendations.append(
                f"{result.update_available} driver(s) have updates available. "
                "Consider updating for improved performance and stability."
            )
        
        # GPU specific recommendations
        gpu_outdated = sum(1 for d in result.gpu_drivers if d.status in [DriverStatus.UPDATE_AVAILABLE, DriverStatus.CRITICAL])
        if gpu_outdated > 0:
            recommendations.append(
                "GPU driver update recommended. Newer drivers often include "
                "game optimizations and bug fixes."
            )
        
        # Audio recommendations
        audio_unsigned = sum(1 for d in result.audio_drivers if not d.is_signed)
        if audio_unsigned > 0:
            recommendations.append(
                "Unsigned audio drivers detected. These may cause audio issues in games. "
                "Consider updating to signed drivers."
            )
        
        return recommendations
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during check"""
        return self.errors


__all__ = [
    'DriverCompatibilityChecker',
    'DriverCompatibilityResult',
    'DriverInfo',
    'DriverStatus',
    'DriverCategory'
]