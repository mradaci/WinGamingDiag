"""
WinGamingDiag - Network Diagnostics
Analyzes network configuration and performance for gaming
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import socket
import subprocess


class ConnectionType(Enum):
    """Network connection types"""
    ETHERNET = "ethernet"
    WIFI = "wifi"
    VPN = "vpn"
    BLUETOOTH = "bluetooth"
    UNKNOWN = "unknown"


class NetworkStatus(Enum):
    """Network connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    LIMITED = "limited"
    UNKNOWN = "unknown"


@dataclass
class NetworkAdapter:
    """Network adapter information"""
    name: str
    description: str
    type: ConnectionType
    status: NetworkStatus
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    speed_mbps: Optional[int] = None
    is_default: bool = False
    dhcp_enabled: bool = True
    mtu: int = 1500


@dataclass
class LatencyTest:
    """Latency test results"""
    target: str
    target_name: str
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    packet_loss: float = 0.0
    jitter_ms: float = 0.0
    status: str = "unknown"


@dataclass
class NetworkDiagnosticsResult:
    """Complete network diagnostics results"""
    is_connected: bool = False
    connection_type: ConnectionType = ConnectionType.UNKNOWN
    default_adapter: Optional[NetworkAdapter] = None
    adapters: List[NetworkAdapter] = field(default_factory=list)
    
    # Latency tests
    dns_latency_ms: Optional[float] = None
    gateway_latency_ms: Optional[float] = None
    gaming_servers: List[LatencyTest] = field(default_factory=list)
    
    # Issues
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Configuration
    ipv6_enabled: bool = False
    qos_enabled: bool = False
    gaming_mode_enabled: bool = False
    
    def __post_init__(self):
        if self.default_adapter:
            self.connection_type = self.default_adapter.type


class NetworkDiagnostics:
    """
    Diagnoses network configuration and performance for gaming.
    Tests latency to gaming servers and identifies network issues.
    """
    
    # Gaming server endpoints for latency testing
    GAMING_SERVERS = [
        {'host': '8.8.8.8', 'name': 'Google DNS', 'region': 'Global'},
        {'host': '1.1.1.1', 'name': 'Cloudflare DNS', 'region': 'Global'},
        {'host': 'steamcommunity.com', 'name': 'Steam Community', 'region': 'Global'},
        {'host': 'epicgames.com', 'name': 'Epic Games', 'region': 'Global'},
    ]
    
    # Known gaming ports
    GAMING_PORTS = [
        27015,  # Steam/Source games
        3074,   # Xbox Live
        9308,   # PlayStation Network
        443,    # HTTPS (general gaming)
        80,     # HTTP
    ]
    
    def __init__(self, wmi_helper=None):
        """
        Initialize network diagnostics
        
        Args:
            wmi_helper: WMI helper instance
        """
        self.wmi_helper = wmi_helper
        self.errors: List[str] = []
    
    def run_diagnostics(self) -> NetworkDiagnosticsResult:
        """
        Run complete network diagnostics
        
        Returns:
            NetworkDiagnosticsResult with diagnostic results
        """
        result = NetworkDiagnosticsResult()
        
        try:
            # Get network adapters
            adapters = self._get_network_adapters()
            result.adapters = adapters
            
            # Find default adapter
            for adapter in adapters:
                if adapter.is_default and adapter.status == NetworkStatus.CONNECTED:
                    result.default_adapter = adapter
                    result.is_connected = True
                    result.connection_type = adapter.type
                    break
            
            # Test DNS resolution
            result.dns_latency_ms = self._test_dns_latency()
            
            # Test gateway latency
            if result.default_adapter and result.default_adapter.gateway:
                result.gateway_latency_ms = self._test_gateway_latency(
                    result.default_adapter.gateway
                )
            
            # Test gaming servers
            result.gaming_servers = self._test_gaming_servers()
            
            # Check network configuration
            self._check_network_config(result)
            
            # Identify issues
            result.issues = self._identify_issues(result)
            
            # Generate recommendations
            result.recommendations = self._generate_recommendations(result)
            
        except Exception as e:
            self.errors.append(f"Network diagnostics failed: {e}")
        
        return result
    
    def _get_network_adapters(self) -> List[NetworkAdapter]:
        """Get network adapter information"""
        adapters = []
        
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                # Query network adapters
                result = self.wmi_helper.query(
                    "Win32_NetworkAdapter",
                    fields=["Name", "Description", "MACAddress", "Speed", "AdapterType", "NetConnectionStatus"]
                )
                
                if hasattr(result, 'success') and result.success:
                    for adapter_data in result.data:
                        adapter = self._parse_adapter(adapter_data)
                        if adapter:
                            adapters.append(adapter)
                
                # Get network adapter configurations
                config_result = self.wmi_helper.query(
                    "Win32_NetworkAdapterConfiguration",
                    fields=["MACAddress", "IPAddress", "IPSubnet", "DefaultIPGateway", 
                           "DNSServerSearchOrder", "DHCPEnabled", "MTU"]
                )
                
                if hasattr(config_result, 'success') and config_result.success:
                    self._merge_adapter_configs(adapters, config_result.data)
            
            # Fallback: Use socket to get basic info
            if not adapters:
                adapters = self._get_adapters_fallback()
                
        except Exception as e:
            self.errors.append(f"Adapter collection error: {e}")
        
        return adapters
    
    def _parse_adapter(self, adapter_data: Dict[str, Any]) -> Optional[NetworkAdapter]:
        """Parse adapter data from WMI"""
        try:
            name = adapter_data.get('Name', 'Unknown')
            description = adapter_data.get('Description', name)
            
            # Determine connection type
            adapter_type = adapter_data.get('AdapterType', '')
            if 'ethernet' in adapter_type.lower():
                conn_type = ConnectionType.ETHERNET
            elif 'wireless' in adapter_type.lower() or 'wi-fi' in adapter_type.lower():
                conn_type = ConnectionType.WIFI
            elif 'vpn' in description.lower():
                conn_type = ConnectionType.VPN
            else:
                conn_type = ConnectionType.UNKNOWN
            
            # Determine status
            status_code = adapter_data.get('NetConnectionStatus', 0)
            if status_code == 2:
                status = NetworkStatus.CONNECTED
            elif status_code == 3:
                status = NetworkStatus.DISCONNECTED
            else:
                status = NetworkStatus.UNKNOWN
            
            # Get speed
            speed = adapter_data.get('Speed')
            if speed:
                speed_mbps = int(speed) / 1000000  # Convert to Mbps
            else:
                speed_mbps = None
            
            return NetworkAdapter(
                name=name,
                description=description,
                type=conn_type,
                status=status,
                mac_address=adapter_data.get('MACAddress'),
                speed_mbps=int(speed_mbps) if speed_mbps else None
            )
            
        except Exception:
            return None
    
    def _merge_adapter_configs(self, adapters: List[NetworkAdapter], configs: List[Dict]) -> None:
        """Merge adapter configurations with adapters"""
        for adapter in adapters:
            for config in configs:
                if config.get('MACAddress') == adapter.mac_address:
                    # Merge config data
                    ip_addresses = config.get('IPAddress', [])
                    if ip_addresses and isinstance(ip_addresses, list):
                        adapter.ip_address = ip_addresses[0]
                    elif ip_addresses:
                        adapter.ip_address = str(ip_addresses)
                    
                    subnets = config.get('IPSubnet', [])
                    if subnets and isinstance(subnets, list):
                        adapter.subnet_mask = subnets[0]
                    elif subnets:
                        adapter.subnet_mask = str(subnets)
                    
                    gateways = config.get('DefaultIPGateway', [])
                    if gateways and isinstance(gateways, list):
                        adapter.gateway = gateways[0]
                    elif gateways:
                        adapter.gateway = str(gateways)
                    
                    dns_servers = config.get('DNSServerSearchOrder', [])
                    if dns_servers:
                        adapter.dns_servers = dns_servers if isinstance(dns_servers, list) else [str(dns_servers)]
                    
                    adapter.dhcp_enabled = config.get('DHCPEnabled', True)
                    adapter.mtu = config.get('MTU', 1500)
                    
                    # Check if this is the default adapter (has gateway)
                    if adapter.gateway:
                        adapter.is_default = True
                    
                    break
    
    def _get_adapters_fallback(self) -> List[NetworkAdapter]:
        """Get adapters using fallback method"""
        adapters = []
        
        try:
            # Get hostname and IP info
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            
            # Create a basic adapter entry
            adapters.append(NetworkAdapter(
                name="Default Adapter",
                description="Active Network Connection",
                type=ConnectionType.UNKNOWN,
                status=NetworkStatus.CONNECTED,
                ip_address=ip_address,
                is_default=True
            ))
            
        except Exception:
            pass
        
        return adapters
    
    def _test_dns_latency(self) -> Optional[float]:
        """Test DNS resolution latency"""
        try:
            import time
            
            start = time.time()
            socket.getaddrinfo('google.com', None)
            end = time.time()
            
            return round((end - start) * 1000, 2)  # Convert to ms
            
        except Exception:
            return None
    
    def _test_gateway_latency(self, gateway: str) -> Optional[float]:
        """Test latency to gateway"""
        try:
            return self._ping_host(gateway)
        except Exception:
            return None
    
    def _test_gaming_servers(self) -> List[LatencyTest]:
        """Test latency to gaming servers"""
        results = []
        
        for server in self.GAMING_SERVERS:
            try:
                latency = self._ping_host(server['host'])
                
                test = LatencyTest(
                    target=server['host'],
                    target_name=server['name'],
                    avg_ms=latency if latency else 0.0,
                    status="ok" if latency and latency < 100 else "high_latency" if latency else "failed"
                )
                
                results.append(test)
                
            except Exception:
                results.append(LatencyTest(
                    target=server['host'],
                    target_name=server['name'],
                    status="failed"
                ))
        
        return results
    
    def _ping_host(self, host: str, count: int = 4) -> Optional[float]:
        """Ping a host and return average latency"""
        try:
            # Use system ping command
            import subprocess
            import re
            
            result = subprocess.run(
                ['ping', '-n', str(count), host],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output for average time
                match = re.search(r'Average\s*=\s*(\d+)ms', result.stdout)
                if match:
                    return float(match.group(1))
                
                # Alternative format
                match = re.search(r'minimum\s*=\s*\d+ms.*?average\s*=\s*(\d+)ms', result.stdout, re.IGNORECASE)
                if match:
                    return float(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    def _check_network_config(self, result: NetworkDiagnosticsResult) -> None:
        """Check network configuration settings"""
        try:
            # Check IPv6
            result.ipv6_enabled = self._check_ipv6_enabled()
            
            # Check QoS
            result.qos_enabled = self._check_qos_enabled()
            
            # Check gaming mode
            result.gaming_mode_enabled = self._check_gaming_mode()
            
        except Exception as e:
            self.errors.append(f"Config check error: {e}")
    
    def _check_ipv6_enabled(self) -> bool:
        """Check if IPv6 is enabled"""
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                result = self.wmi_helper.query(
                    "Win32_NetworkAdapterConfiguration",
                    fields=["IPAddress"]
                )
                
                if hasattr(result, 'success') and result.success:
                    for config in result.data:
                        ip_addresses = config.get('IPAddress', [])
                        if ip_addresses:
                            if not isinstance(ip_addresses, list):
                                ip_addresses = [ip_addresses]
                            for ip in ip_addresses:
                                if ':' in str(ip):  # IPv6 address
                                    return True
            
            return False
            
        except Exception:
            return False
    
    def _check_qos_enabled(self) -> bool:
        """Check if QoS is enabled"""
        # Simplified check - would need registry access for full check
        return False
    
    def _check_gaming_mode(self) -> bool:
        """Check if Windows gaming mode network optimizations are enabled"""
        try:
            import winreg
            
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
            
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            
            try:
                network_throttling, _ = winreg.QueryValueEx(key, "NetworkThrottlingIndex")
                # If set to FFFFFFFF, network throttling is disabled (better for gaming)
                return network_throttling == 0xFFFFFFFF
            except:
                pass
            finally:
                winreg.CloseKey(key)
                
        except:
            pass
        
        return False
    
    def _identify_issues(self, result: NetworkDiagnosticsResult) -> List[str]:
        """Identify network issues"""
        issues = []
        
        # Check connectivity
        if not result.is_connected:
            issues.append("No active network connection detected")
            return issues
        
        # Check connection type
        if result.connection_type == ConnectionType.WIFI:
            issues.append("Using WiFi connection - may have higher latency than Ethernet")
        
        # Check DNS latency
        if result.dns_latency_ms and result.dns_latency_ms > 100:
            issues.append(f"High DNS latency ({result.dns_latency_ms:.0f}ms) - consider changing DNS servers")
        
        # Check gateway latency
        if result.gateway_latency_ms and result.gateway_latency_ms > 10:
            issues.append(f"High gateway latency ({result.gateway_latency_ms:.0f}ms) - local network congestion")
        
        # Check gaming server latency
        for server in result.gaming_servers:
            if server.avg_ms > 150:
                issues.append(f"High latency to {server.target_name} ({server.avg_ms:.0f}ms)")
        
        # Check MTU
        if result.default_adapter and result.default_adapter.mtu != 1500:
            issues.append(f"Non-standard MTU detected ({result.default_adapter.mtu}) - may affect performance")
        
        # Check configuration
        if result.ipv6_enabled:
            issues.append("IPv6 is enabled - may cause connection issues with some games")
        
        return issues
    
    def _generate_recommendations(self, result: NetworkDiagnosticsResult) -> List[str]:
        """Generate network recommendations"""
        recommendations = []
        
        # Connection type recommendation
        if result.connection_type == ConnectionType.WIFI:
            recommendations.append(
                "Consider using Ethernet connection for gaming to reduce latency and packet loss"
            )
        
        # DNS recommendation
        if result.dns_latency_ms and result.dns_latency_ms > 50:
            recommendations.append(
                "Consider switching to Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1) for faster resolution"
            )
        
        # Gaming mode recommendation
        if not result.gaming_mode_enabled:
            recommendations.append(
                "Enable Windows Gaming Mode for network optimizations"
            )
        
        # QoS recommendation
        if not result.qos_enabled and result.connection_type == ConnectionType.WIFI:
            recommendations.append(
                "Enable QoS on your router to prioritize gaming traffic"
            )
        
        # MTU recommendation
        if result.default_adapter and result.default_adapter.mtu < 1500:
            recommendations.append(
                f"MTU is set to {result.default_adapter.mtu}. Consider setting to 1500 for optimal performance"
            )
        
        # IPv6 recommendation
        if result.ipv6_enabled:
            recommendations.append(
                "If experiencing connection issues, try disabling IPv6 in network adapter settings"
            )
        
        return recommendations
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during diagnostics"""
        return self.errors


__all__ = [
    'NetworkDiagnostics',
    'NetworkDiagnosticsResult',
    'NetworkAdapter',
    'LatencyTest',
    'ConnectionType',
    'NetworkStatus'
]