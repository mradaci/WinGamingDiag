"""
WinGamingDiag - WMI Helper Utilities
Safe Windows Management Instrumentation queries with error handling
"""

import sys
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import time
import re
import logging

try:
    import wmi
except ImportError:
    # This will be handled by the is_available check, but allows linting on non-Windows
    wmi = None



@dataclass
class WMIQueryResult:
    """Result from a WMI query"""
    success: bool
    data: Optional[Any] = None
    error_message: str = ""
    retry_count: int = 0
    query_time_ms: float = 0.0


class WMIHelper:
    """
    Helper class for safe WMI queries with retry logic and error handling.
    Designed to be resilient against WMI service timeouts and permission issues.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize WMI helper
        
        Args:
            max_retries: Maximum number of retry attempts for failed queries
            retry_delay: Delay in seconds between retries
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connection = None
        self._query_count = 0
        self._error_count = 0
        self._is_available = None  # Cache availability check
        
    @property
    def is_available(self) -> bool:
        """Check if WMI is available on this system"""
        if self._is_available is not None:
            return self._is_available
            
        if sys.platform != 'win32':
            self._is_available = False
            return False
            
        try:
            import wmi
            c = wmi.WMI()
            # Test with a simple query
            _ = c.Win32_ComputerSystem()[0]
            self._is_available = True
            return True
        except Exception:
            self._is_available = False
            return False
    
    def _get_connection(self):
        """Get or create WMI connection"""
        if self._connection is None:
            try:
                import wmi
                self._connection = wmi.WMI()
            except Exception as e:
                raise RuntimeError(f"Failed to initialize WMI connection: {e}")
        return self._connection
    
    def query(self, wmi_class: str, properties: Optional[List[str]] = None,
              where_clause: Optional[str] = None, 
              first_only: bool = False) -> WMIQueryResult:
        """
        Execute a WMI query with retry logic
        
        Args:
            wmi_class: WMI class name (e.g., "Win32_Processor")
            properties: List of properties to retrieve (None = all)
            where_clause: Optional WHERE clause for filtering
            first_only: If True, return only first result
            
        Returns:
            WMIQueryResult with success status and data
        """
        if not self.is_available:
            return WMIQueryResult(
                success=False,
                error_message="WMI is not available on this system"
            )
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                conn = self._get_connection()
                
                # Build query
                if properties:
                    props_str = ",".join(properties)
                else:
                    props_str = "*"
                
                query_str = f"SELECT {props_str} FROM {wmi_class}"
                if where_clause:
                    query_str += f" WHERE {where_clause}"
                
                # Execute query
                results = conn.query(query_str)
                
                # Convert to list of dictionaries
                data = []
                for item in results:
                    item_dict = {}
                    for prop in item.properties:
                        try:
                            value = getattr(item, prop, None)
                            item_dict[prop] = value
                        except Exception:
                            item_dict[prop] = None
                    data.append(item_dict)
                
                if first_only:
                    data = data[0] if data else None
                
                self._query_count += 1
                query_time = (time.time() - start_time) * 1000
                
                return WMIQueryResult(
                    success=True,
                    data=data,
                    retry_count=attempt,
                    query_time_ms=query_time
                )
                
            except wmi.x_wmi as wmi_error:
                last_error = wmi_error
                logging.error(f"WMI query failed on attempt {attempt + 1}/{self.max_retries}: {query_str}")
                logging.error(f"WMI specific error: {wmi_error}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._connection = None
            except Exception as e:
                last_error = e
                logging.error(f"Generic error during WMI query on attempt {attempt + 1}/{self.max_retries}: {query_str}")
                logging.error(f"Generic exception: {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._connection = None
            except Exception as e:
                last_error = e
                logging.error(f"Generic error during WMI query on attempt {attempt + 1}/{self.max_retries}: {query_str}")
                logging.error(f"Generic exception: {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self._connection = None
        
        # All retries failed
        self._error_count += 1
        query_time = (time.time() - start_time) * 1000
        
        return WMIQueryResult(
            success=False,
            error_message=str(last_error),
            retry_count=self.max_retries,
            query_time_ms=query_time
        )
    
    def get_single_property(self, wmi_class: str, property_name: str,
                           where_clause: Optional[str] = None) -> Optional[Any]:
        """
        Get a single property value from WMI
        
        Args:
            wmi_class: WMI class name
            property_name: Property to retrieve
            where_clause: Optional filter
            
        Returns:
            Property value or None if not found/error
        """
        result = self.query(wmi_class, [property_name], where_clause, first_only=True)
        if result.success and result.data:
            return result.data.get(property_name)
        return None
    
    def get_computer_system_info(self) -> Optional[Dict[str, Any]]:
        """Get basic computer system information"""
        result = self.query("Win32_ComputerSystem", first_only=True)
        return result.data if result.success else None
    
    def get_operating_system_info(self) -> Optional[Dict[str, Any]]:
        """Get operating system information"""
        result = self.query("Win32_OperatingSystem", first_only=True)
        return result.data if result.success else None
    
    def get_processor_info(self) -> List[Dict[str, Any]]:
        """Get processor information for all CPUs"""
        result = self.query("Win32_Processor")
        return result.data if result.success and result.data is not None else []
    
    def get_memory_info(self) -> List[Dict[str, Any]]:
        """Get physical memory information"""
        result = self.query("Win32_PhysicalMemory")
        return result.data if result.success and result.data is not None else []
    
    def get_video_controller_info(self) -> List[Dict[str, Any]]:
        """Get video controller/GPU information"""
        result = self.query("Win32_VideoController")
        return result.data if result.success and result.data is not None else []
    
    def get_disk_drive_info(self) -> List[Dict[str, Any]]:
        """Get disk drive information"""
        result = self.query("Win32_DiskDrive")
        return result.data if result.success and result.data is not None else []
    
    def get_logical_disk_info(self) -> List[Dict[str, Any]]:
        """Get logical disk (partition) information"""
        result = self.query("Win32_LogicalDisk")
        return result.data if result.success and result.data is not None else []
    
    def get_baseboard_info(self) -> Optional[Dict[str, Any]]:
        """Get motherboard information"""
        result = self.query("Win32_BaseBoard", first_only=True)
        return result.data if result.success else None
    
    def get_bios_info(self) -> Optional[Dict[str, Any]]:
        """Get BIOS/UEFI information"""
        result = self.query("Win32_BIOS", first_only=True)
        return result.data if result.success else None
    
    def get_fan_info(self) -> List[Dict[str, Any]]:
        """Get cooling fan information"""
        result = self.query("Win32_Fan")
        return result.data if result.success and result.data is not None else []
    
    def get_temperature_info(self) -> List[Dict[str, Any]]:
        """Get temperature sensor information"""
        result = self.query("Win32_TemperatureProbe")
        return result.data if result.success and result.data is not None else []
        
    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get battery information (for laptops)"""
        result = self.query("Win32_Battery", first_only=True)
        return result.data if result.success else None
    
    def get_network_adapter_info(self) -> List[Dict[str, Any]]:
        """Get network adapter information"""
        result = self.query("Win32_NetworkAdapter", 
                          where_clause="NetEnabled=True")
        return result.data if result.success and result.data is not None else []
    
    def get_pnp_device_info(self) -> List[Dict[str, Any]]:
        """Get Plug and Play device information"""
        result = self.query("Win32_PnPEntity")
        return result.data if result.success and result.data is not None else []
    
    def get_service_info(self) -> List[Dict[str, Any]]:
        """Get Windows service information"""
        result = self.query("Win32_Service")
        return result.data if result.success and result.data is not None else []
    
    def get_process_info(self) -> List[Dict[str, Any]]:
        """Get running process information"""
        result = self.query("Win32_Process")
        return result.data if result.success and result.data is not None else []
    
    def get_startup_command_info(self) -> List[Dict[str, Any]]:
        """Get startup program information"""
        result = self.query("Win32_StartupCommand")
        return result.data if result.success and result.data is not None else []
    
    def get_memory_info(self) -> List[Dict[str, Any]]:
        """Get physical memory information"""
        result = self.query("Win32_PhysicalMemory")
        return result.data if result.success else []
    
    def get_video_controller_info(self) -> List[Dict[str, Any]]:
        """Get video controller/GPU information"""
        result = self.query("Win32_VideoController")
        return result.data if result.success else []
    
    def get_disk_drive_info(self) -> List[Dict[str, Any]]:
        """Get disk drive information"""
        result = self.query("Win32_DiskDrive")
        return result.data if result.success else []
    
    def get_logical_disk_info(self) -> List[Dict[str, Any]]:
        """Get logical disk (partition) information"""
        result = self.query("Win32_LogicalDisk")
        return result.data if result.success else []
    
    def get_baseboard_info(self) -> Dict[str, Any]:
        """Get motherboard information"""
        result = self.query("Win32_BaseBoard", first_only=True)
        return result.data if result.success else {}
    
    def get_bios_info(self) -> Dict[str, Any]:
        """Get BIOS/UEFI information"""
        result = self.query("Win32_BIOS", first_only=True)
        return result.data if result.success else {}
    
    def get_fan_info(self) -> List[Dict[str, Any]]:
        """Get cooling fan information"""
        result = self.query("Win32_Fan")
        return result.data if result.success else []
    
    def get_temperature_info(self) -> List[Dict[str, Any]]:
        """Get temperature sensor information"""
        result = self.query("Win32_TemperatureProbe")
        return result.data if result.success else []
    
    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get battery information (for laptops)"""
        result = self.query("Win32_Battery", first_only=True)
        return result.data if result.success else None
    
    def get_network_adapter_info(self) -> List[Dict[str, Any]]:
        """Get network adapter information"""
        result = self.query("Win32_NetworkAdapter", 
                          where_clause="NetEnabled=True")
        return result.data if result.success else []
    
    def get_pnp_device_info(self) -> List[Dict[str, Any]]:
        """Get Plug and Play device information"""
        result = self.query("Win32_PnPEntity")
        return result.data if result.success else []
    
    def get_service_info(self) -> List[Dict[str, Any]]:
        """Get Windows service information"""
        result = self.query("Win32_Service")
        return result.data if result.success else []
    
    def get_process_info(self) -> List[Dict[str, Any]]:
        """Get running process information"""
        result = self.query("Win32_Process")
        return result.data if result.success else []
    
    def get_startup_command_info(self) -> List[Dict[str, Any]]:
        """Get startup program information"""
        result = self.query("Win32_StartupCommand")
        return result.data if result.success else []
    
    @staticmethod
    def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Safely get a value from WMI data with type conversion
        
        Args:
            data: Dictionary from WMI query
            key: Key to retrieve
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        value = data.get(key, default)
        
        # Handle WMI datetime format (e.g., "20210101120000.000000+000")
        if isinstance(value, str) and re.match(r'\d{14}\.\d{6}[\+\-]\d{3}', value):
            try:
                # Parse WMI datetime format
                year = int(value[0:4])
                month = int(value[4:6])
                day = int(value[6:8])
                hour = int(value[8:10])
                minute = int(value[10:12])
                second = int(value[12:14])
                return datetime(year, month, day, hour, minute, second)
            except (ValueError, IndexError):
                return value
        
        return value
    
    @staticmethod
    def convert_bytes_to_gb(bytes_value: Optional[int]) -> Optional[float]:
        """Convert bytes to gigabytes"""
        if bytes_value is None:
            return None
        return round(bytes_value / (1024 ** 3), 2)
    
    @staticmethod
    def convert_bytes_to_mb(bytes_value: Optional[int]) -> Optional[float]:
        """Convert bytes to megabytes"""
        if bytes_value is None:
            return None
        return round(bytes_value / (1024 ** 2), 2)
    
    @staticmethod
    def convert_mhz_to_ghz(mhz_value: Optional[int]) -> Optional[float]:
        """Convert MHz to GHz"""
        if mhz_value is None:
            return None
        return round(mhz_value / 1000, 2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        return {
            "total_queries": self._query_count,
            "error_count": self._error_count,
            "success_rate": (self._query_count - self._error_count) / max(self._query_count, 1) * 100,
            "is_available": self.is_available
        }


# Convenience functions for direct use
_wmi_helper = None

def get_wmi_helper() -> WMIHelper:
    """Get singleton WMI helper instance"""
    global _wmi_helper
    if _wmi_helper is None:
        _wmi_helper = WMIHelper()
    return _wmi_helper


__all__ = [
    'WMIQueryResult',
    'WMIHelper',
    'get_wmi_helper'
]
