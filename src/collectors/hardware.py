"""
WinGamingDiag - Hardware Inventory Collector
Collects comprehensive hardware information from the system
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import platform
import sys

from ..models import (
    CPUInfo, MemoryInfo, GPUInfo, StorageInfo, MotherboardInfo,
    CoolingInfo, PowerInfo, HardwareSnapshot
)
from ..utils.wmi_helper import WMIHelper, get_wmi_helper
from ..utils.redaction import redact_sensitive_data


class HardwareCollector:
    """
    Collects comprehensive hardware information from the system.
    Uses WMI as primary source, with fallbacks for when WMI is unavailable.
    """
    
    def __init__(self, wmi_helper: Optional[WMIHelper] = None):
        """
        Initialize hardware collector
        
        Args:
            wmi_helper: WMI helper instance (creates new if not provided)
        """
        self.wmi = wmi_helper or get_wmi_helper()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def collect_all(self) -> HardwareSnapshot:
        """
        Collect complete hardware inventory
        
        Returns:
            HardwareSnapshot with all hardware information
        """
        snapshot = HardwareSnapshot()
        
        try:
            snapshot.cpu = self.collect_cpu_info()
        except Exception as e:
            self.errors.append(f"CPU collection failed: {e}")
        
        try:
            snapshot.memory = self.collect_memory_info()
        except Exception as e:
            self.errors.append(f"Memory collection failed: {e}")
        
        try:
            snapshot.gpus = self.collect_gpu_info()
        except Exception as e:
            self.errors.append(f"GPU collection failed: {e}")
        
        try:
            snapshot.storage_devices = self.collect_storage_info()
        except Exception as e:
            self.errors.append(f"Storage collection failed: {e}")
        
        try:
            snapshot.motherboard = self.collect_motherboard_info()
        except Exception as e:
            self.errors.append(f"Motherboard collection failed: {e}")
        
        try:
            snapshot.cooling = self.collect_cooling_info()
        except Exception as e:
            self.errors.append(f"Cooling collection failed: {e}")
        
        try:
            snapshot.power = self.collect_power_info()
        except Exception as e:
            self.errors.append(f"Power collection failed: {e}")
        
        return snapshot
    
    def collect_cpu_info(self) -> Optional[CPUInfo]:
        """Collect CPU information"""
        if not self.wmi.is_available:
            return self._collect_cpu_fallback()
        
        processors = self.wmi.get_processor_info()
        if not processors:
            return None
        
        # Use first processor (usually the only one in consumer systems)
        cpu_data = processors[0]
        
        # Parse CPU name and manufacturer
        name = cpu_data.get('Name', 'Unknown CPU').strip()
        manufacturer = cpu_data.get('Manufacturer', 'Unknown')
        
        # Normalize manufacturer name
        if 'intel' in manufacturer.lower():
            manufacturer = 'Intel'
        elif 'amd' in manufacturer.lower():
            manufacturer = 'AMD'
        
        # Get architecture
        architecture = cpu_data.get('Architecture', 'Unknown')
        arch_map = {
            0: 'x86', 1: 'MIPS', 2: 'Alpha', 3: 'PowerPC',
            5: 'ARM', 6: 'ia64', 9: 'x64'
        }
        if isinstance(architecture, int):
            architecture = arch_map.get(architecture, 'Unknown')
        
        # Core/thread counts
        cores = cpu_data.get('NumberOfCores', 0)
        threads = cpu_data.get('NumberOfLogicalProcessors', 0)
        
        # Clock speeds (in MHz from WMI)
        base_clock = cpu_data.get('MaxClockSpeed', 0)
        current_clock = cpu_data.get('CurrentClockSpeed', base_clock)
        
        # Virtualization
        virt_enabled = cpu_data.get('VirtualizationFirmwareEnabled', False)
        vm_monitor_ext = cpu_data.get('VMMonitorModeExtensions', False)
        
        # Cache
        l3_cache = cpu_data.get('L3CacheSize', 0)
        if l3_cache:
            l3_cache = l3_cache / 1024  # Convert KB to MB
        
        return CPUInfo(
            name=name,
            manufacturer=manufacturer,
            architecture=architecture,
            cores=cores,
            threads=threads,
            base_clock_mhz=float(base_clock),
            max_clock_mhz=float(base_clock),  # WMI gives max as base
            current_clock_mhz=float(current_clock) if current_clock else None,
            virtualization_enabled=bool(virt_enabled),
            virtualization_support=bool(vm_monitor_ext),
            l3_cache_mb=l3_cache if l3_cache else None,
            socket=cpu_data.get('SocketDesignation'),
            microcode=cpu_data.get('ProcessorId'),
            stepping=cpu_data.get('Stepping'),
            load_percent=cpu_data.get('LoadPercentage')
        )
    
    def _collect_cpu_fallback(self) -> Optional[CPUInfo]:
        """Fallback CPU collection using platform module"""
        try:
            processor = platform.processor()
            machine = platform.machine()
            
            return CPUInfo(
                name=processor or 'Unknown',
                manufacturer='Unknown',
                architecture=machine or 'Unknown',
                cores=0,  # Cannot determine without WMI/psutil
                threads=0,
                base_clock_mhz=0.0,
                max_clock_mhz=0.0
            )
        except Exception:
            return None
    
    def collect_memory_info(self) -> Optional[MemoryInfo]:
        """Collect memory/RAM information"""
        if not self.wmi.is_available:
            return self._collect_memory_fallback()
        
        # Get physical memory modules
        modules = self.wmi.get_memory_info()
        
        if not modules:
            return None
        
        total_bytes = 0
        used_slots = 0
        slot_speeds = []
        slot_types = []
        memory_modules = []
        
        for module in modules:
            capacity = module.get('Capacity', 0)
            if capacity:
                total_bytes += int(capacity)
                used_slots += 1
            
            speed = module.get('Speed')
            if speed:
                slot_speeds.append(speed)
            
            mem_type = module.get('MemoryType')
            if mem_type:
                type_map = {
                    0: 'Unknown', 1: 'Other', 2: 'DRAM', 3: 'Synchronous DRAM',
                    4: 'Cache DRAM', 5: 'EDO', 6: 'EDRAM', 7: 'VRAM',
                    8: 'SRAM', 9: 'RAM', 10: 'ROM', 11: 'Flash',
                    12: 'EEPROM', 13: 'FEPROM', 14: 'EPROM',
                    15: 'CDRAM', 16: '3DRAM', 17: 'SDRAM',
                    18: 'SGRAM', 19: 'RDRAM', 20: 'DDR',
                    21: 'DDR2', 22: 'DDR2 FB-DIMM', 24: 'DDR3',
                    25: 'FBD2', 26: 'DDR4', 27: 'DDR5'
                }
                slot_types.append(type_map.get(mem_type, 'Unknown'))
            
            memory_modules.append({
                'capacity_gb': round(int(capacity) / (1024**3), 2) if capacity else None,
                'speed_mhz': speed,
                'type': slot_types[-1] if slot_types else None,
                'manufacturer': module.get('Manufacturer'),
                'part_number': module.get('PartNumber'),
                'serial_number': module.get('SerialNumber'),
                'slot': module.get('DeviceLocator')
            })
        
        # Get total system memory from OS
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulong = ctypes.c_ulong
            class MEMORYSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", c_ulong),
                    ("dwMemoryLoad", c_ulong),
                    ("dwTotalPhys", c_ulong),
                    ("dwAvailPhys", c_ulong),
                    ("dwTotalPageFile", c_ulong),
                    ("dwAvailPageFile", c_ulong),
                    ("dwTotalVirtual", c_ulong),
                    ("dwAvailVirtual", c_ulong)
                ]
            
            memory_status = MEMORYSTATUS()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUS)
            kernel32.GlobalMemoryStatus(ctypes.byref(memory_status))
            
            total_gb = memory_status.dwTotalPhys / (1024**3)
            available_gb = memory_status.dwAvailPhys / (1024**3)
            used_gb = total_gb - available_gb
        except:
            total_gb = total_bytes / (1024**3)
            used_gb = 0
            available_gb = total_gb
        
        # Determine common speed and type
        common_speed = max(set(slot_speeds), key=slot_speeds.count) if slot_speeds else None
        common_type = max(set(slot_types), key=slot_types.count) if slot_types else None
        
        return MemoryInfo(
            total_gb=round(total_gb, 2),
            used_gb=round(used_gb, 2),
            available_gb=round(available_gb, 2),
            speed_mhz=common_speed,
            type=common_type,
            slots_used=used_slots,
            slots_total=used_slots,  # Cannot determine total slots without SMBIOS
            xmp_enabled=False,  # Requires motherboard-specific detection
            modules=memory_modules
        )
    
    def _collect_memory_fallback(self) -> Optional[MemoryInfo]:
        """Fallback memory collection"""
        return None
    
    def collect_gpu_info(self) -> List[GPUInfo]:
        """Collect GPU/graphics card information"""
        if not self.wmi.is_available:
            return []
        
        gpus = []
        controllers = self.wmi.get_video_controller_info()
        
        for controller in controllers:
            # Skip Microsoft Basic Display Adapter (virtual driver)
            name = controller.get('Name', 'Unknown')
            if 'basic' in name.lower() and 'display' in name.lower():
                continue
            
            # Determine manufacturer
            manufacturer = controller.get('AdapterCompatibility', 'Unknown')
            if 'nvidia' in manufacturer.lower():
                manufacturer = 'NVIDIA'
            elif 'amd' in manufacturer.lower() or 'ati' in manufacturer.lower():
                manufacturer = 'AMD'
            elif 'intel' in manufacturer.lower():
                manufacturer = 'Intel'
            
            # Video memory
            vram = controller.get('AdapterRAM', 0)
            if vram:
                vram = vram // (1024 * 1024)  # Bytes to MB
            
            # Driver info
            driver_version = controller.get('DriverVersion', 'Unknown')
            driver_date = controller.get('DriverDate')
            if driver_date and hasattr(driver_date, 'strftime'):
                driver_date = driver_date.strftime('%Y-%m-%d')
            
            # Video mode
            video_mode = controller.get('VideoModeDescription', '')
            resolution = None
            refresh_rate = None
            if video_mode:
                parts = video_mode.split()
                if len(parts) >= 2:
                    resolution = parts[0]
                    if 'Hz' in video_mode:
                        refresh_match = video_mode.split()[-1].replace('Hz', '')
                        try:
                            refresh_rate = int(refresh_match)
                        except:
                            pass
            
            gpu = GPUInfo(
                name=name,
                manufacturer=manufacturer,
                vram_mb=vram if vram else 0,
                driver_version=driver_version,
                driver_date=driver_date,
                whql_signed=controller.get('DriverVersion', '').count('.') >= 3,
                video_mode_description=video_mode,
                current_resolution=resolution,
                refresh_rate=refresh_rate,
                connected_displays=controller.get('CurrentNumberOfColors', 0)
            )
            
            gpus.append(gpu)
        
        return gpus
    
    def collect_storage_info(self) -> List[StorageInfo]:
        """Collect storage device information"""
        if not self.wmi.is_available:
            return []
        
        drives = []
        
        # Get physical disk drives
        disk_drives = self.wmi.get_disk_drive_info()
        logical_disks = {d.get('DeviceID'): d for d in self.wmi.get_logical_disk_info()}
        
        for disk in disk_drives:
            model = disk.get('Model', 'Unknown')
            interface_type = disk.get('InterfaceType', 'Unknown')
            media_type = disk.get('MediaType', 'Unknown')
            
            # Determine if SSD or HDD
            if 'ssd' in media_type.lower() or 'solid' in media_type.lower():
                drive_type = 'SSD'
            elif 'fixed' in media_type.lower() or 'hard' in media_type.lower():
                drive_type = 'HDD'
            else:
                drive_type = 'Unknown'
            
            # Size
            size_bytes = disk.get('Size', 0)
            size_gb = size_bytes / (1024**3) if size_bytes else 0
            
            # Get partitions for this drive
            partitions = []
            try:
                partition_query = f"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{disk.get('DeviceID')}'}} WHERE AssocClass = Win32_DiskDriveToDiskPartition"
                partition_result = self.wmi.query("Win32_DiskPartition", where_clause=f"DiskIndex={disk.get('Index', 0)}")
                
                if partition_result.success:
                    for part in partition_result.data:
                        partitions.append({
                            'device_id': part.get('DeviceID'),
                            'size_gb': round(part.get('Size', 0) / (1024**3), 2),
                            'is_boot': part.get('BootPartition', False),
                            'type': part.get('Type')
                        })
            except:
                pass
            
            # Check if system drive
            is_system = any(p.get('is_boot') for p in partitions)
            
            storage = StorageInfo(
                model=model,
                interface=interface_type,
                type=drive_type,
                total_gb=round(size_gb, 2),
                used_gb=0,  # Calculated from partitions
                free_gb=0,
                partitions=partitions,
                is_system_drive=is_system,
                smart_data={
                    'status': disk.get('Status'),
                    'serial_number': disk.get('SerialNumber')
                }
            )
            
            drives.append(storage)
        
        return drives
    
    def collect_motherboard_info(self) -> Optional[MotherboardInfo]:
        """Collect motherboard information"""
        if not self.wmi.is_available:
            return None
        
        baseboard = self.wmi.get_baseboard_info()
        bios = self.wmi.get_bios_info()
        
        if not baseboard and not bios:
            return None
        
        manufacturer = baseboard.get('Manufacturer', 'Unknown')
        model = baseboard.get('Product', 'Unknown')
        version = baseboard.get('Version', '')
        serial = baseboard.get('SerialNumber')
        
        # BIOS info
        bios_version = bios.get('Version', '')
        bios_date = bios.get('ReleaseDate')
        if bios_date and hasattr(bios_date, 'strftime'):
            bios_date = bios_date.strftime('%Y-%m-%d')
        
        # Detect UEFI vs Legacy
        bios_mode = 'Legacy'
        if 'uefi' in bios_version.lower() or 'efi' in str(bios.get('SoftwareElementID', '')).lower():
            bios_mode = 'UEFI'
        
        return MotherboardInfo(
            manufacturer=manufacturer,
            model=model,
            version=version,
            serial_number=serial,
            bios_version=bios_version,
            bios_date=bios_date,
            bios_mode=bios_mode,
            secure_boot_enabled=False,  # Requires registry check
            tpm_enabled=False  # Requires TPM WMI class
        )
    
    def collect_cooling_info(self) -> Optional[CoolingInfo]:
        """Collect cooling system information"""
        if not self.wmi.is_available:
            return None
        
        fans = self.wmi.get_fan_info()
        temps = self.wmi.get_temperature_info()
        
        case_fans = []
        for fan in fans:
            case_fans.append({
                'name': fan.get('Name', 'Unknown'),
                'speed_rpm': fan.get('DesiredSpeed'),
                'status': fan.get('Status')
            })
        
        # Check for water cooling indicators
        water_cooling = any('pump' in str(f.get('Name', '')).lower() for f in fans)
        
        return CoolingInfo(
            cpu_fan_rpm=None,  # Requires specific WMI class not always available
            case_fans=case_fans,
            water_cooling_detected=water_cooling,
            pump_rpm=None,
            coolant_temp=None
        )
    
    def collect_power_info(self) -> Optional[PowerInfo]:
        """Collect power supply information"""
        # Power supply info is rarely available via WMI
        # Estimate based on hardware configuration
        
        estimated_wattage = None
        
        # Simple estimation based on GPU
        try:
            gpus = self.collect_gpu_info()
            for gpu in gpus:
                name = gpu.name.lower()
                if 'rtx' in name or 'rx' in name or 'gtx' in name:
                    # High-end GPU, assume 650W+ PSU
                    estimated_wattage = 650
                    break
                elif 'gt' in name or 'integrated' in name:
                    # Low-end or integrated, 300W PSU
                    estimated_wattage = 300
        except:
            pass
        
        return PowerInfo(
            estimated_wattage=estimated_wattage,
            psu_model=None,
            efficiency_rating=None
        )
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during collection"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Get list of warnings encountered during collection"""
        return self.warnings


__all__ = ['HardwareCollector']
