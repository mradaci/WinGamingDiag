"""
WinGamingDiag - Game Launcher Detector
Detects installed game launchers and their configurations
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import os
import re


class LauncherType(Enum):
    """Types of game launchers"""
    STEAM = "steam"
    EPIC = "epic_games"
    EA = "ea_app"
    UBISOFT = "ubisoft_connect"
    BATTLE_NET = "battle_net"
    XBOX = "xbox_app"
    GOG = "gog_galaxy"
    AMAZON = "amazon_games"
    ITCH = "itch_io"
    LEAUNCHER = "minecraft_launcher"
    RIOT = "riot_client"
    ROCKSTAR = "rockstar_games"
    UNKNOWN = "unknown"


class LauncherStatus(Enum):
    """Status of detected launcher"""
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class LauncherInfo:
    """Information about a game launcher"""
    name: str
    type: LauncherType
    status: LauncherStatus
    install_path: Optional[Path] = None
    executable_path: Optional[Path] = None
    version: Optional[str] = None
    library_paths: List[Path] = field(default_factory=list)
    games_count: int = 0
    is_running: bool = False
    auto_start: bool = False
    cloud_saves_enabled: bool = False
    overlay_enabled: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)


@dataclass
class GameLauncherResult:
    """Result of game launcher detection"""
    total_launchers: int = 0
    installed_launchers: List[LauncherInfo] = field(default_factory=list)
    not_installed: List[LauncherType] = field(default_factory=list)
    running_launchers: List[str] = field(default_factory=list)
    total_games: int = 0
    storage_used_gb: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class GameLauncherDetector:
    """
    Detects installed game launchers and analyzes their configurations.
    Identifies potential issues with launchers and game libraries.
    """
    
    # Launcher registry and path configurations
    LAUNCHER_CONFIGS = {
        LauncherType.STEAM: {
            'name': 'Steam',
            'registry_keys': [
                r'SOFTWARE\Valve\Steam',
                r'SOFTWARE\WOW6432Node\Valve\Steam'
            ],
            'default_paths': [
                r'C:\Program Files (x86)\Steam',
                r'C:\Program Files\Steam'
            ],
            'executable': 'steam.exe',
            'library_folders': ['steamapps'],
            'config_files': ['config/config.vdf', 'config/loginusers.vdf'],
            'overlay_name': 'Steam Overlay',
            'process_name': 'steam.exe'
        },
        LauncherType.EPIC: {
            'name': 'Epic Games Launcher',
            'registry_keys': [
                r'SOFTWARE\Epic Games\EpicGamesLauncher',
                r'SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher'
            ],
            'default_paths': [
                r'C:\Program Files (x86)\Epic Games\Launcher',
                r'C:\Program Files\Epic Games\Launcher'
            ],
            'executable': r'PortalBinariesWin64EpicGamesLauncher.exe',
            'library_folders': ['Data'],
            'config_files': [r'SavedConfigWindowsGameUserSettings.ini'],
            'overlay_name': 'Epic Overlay',
            'process_name': 'EpicGamesLauncher.exe'
        },
        LauncherType.EA: {
            'name': 'EA App',
            'registry_keys': [
                r'SOFTWARE\Electronic Arts\EA Desktop',
                r'SOFTWARE\WOW6432Node\Electronic Arts\EA Desktop'
            ],
            'default_paths': [
                r'C:\Program Files\Electronic Arts\EA Desktop',
                r'C:\Program Files (x86)\Electronic Arts\EA Desktop'
            ],
            'executable': r'EA DesktopEA Desktop.exe',
            'library_folders': [],
            'config_files': [],
            'overlay_name': 'EA Overlay',
            'process_name': 'EADesktop.exe'
        },
        LauncherType.UBISOFT: {
            'name': 'Ubisoft Connect',
            'registry_keys': [
                r'SOFTWARE\Ubisoft\Launcher',
                r'SOFTWARE\WOW6432Node\Ubisoft\Launcher'
            ],
            'default_paths': [
                r'C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher',
                r'C:\Program Files\Ubisoft\Ubisoft Game Launcher'
            ],
            'executable': 'UbisoftConnect.exe',
            'library_folders': ['games'],
            'config_files': ['settings.yml'],
            'overlay_name': 'Ubisoft Overlay',
            'process_name': 'UbisoftConnect.exe'
        },
        LauncherType.BATTLE_NET: {
            'name': 'Battle.net',
            'registry_keys': [
                r'SOFTWARE\Blizzard Entertainment\Battle.net',
                r'SOFTWARE\WOW6432Node\Blizzard Entertainment\Battle.net'
            ],
            'default_paths': [
                r'C:\Program Files (x86)\Battle.net',
                r'C:\Program Files\Battle.net'
            ],
            'executable': 'Battle.net.exe',
            'library_folders': [],
            'config_files': ['Battle.net.config'],
            'overlay_name': 'Battle.net Overlay',
            'process_name': 'Battle.net.exe'
        },
        LauncherType.XBOX: {
            'name': 'Xbox App',
            'registry_keys': [
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\GameConfigStore'
            ],
            'default_paths': [],
            'executable': '',
            'library_folders': [],
            'config_files': [],
            'overlay_name': 'Xbox Game Bar',
            'process_name': 'XboxApp.exe'
        },
        LauncherType.GOG: {
            'name': 'GOG Galaxy',
            'registry_keys': [
                r'SOFTWARE\GOG.com\Galaxy'
            ],
            'default_paths': [
                r'C:\Program Files (x86)\GOG Galaxy',
                r'C:\Program Files\GOG Galaxy'
            ],
            'executable': 'GalaxyClient.exe',
            'library_folders': ['Games'],
            'config_files': [],
            'overlay_name': 'GOG Overlay',
            'process_name': 'GalaxyClient.exe'
        },
        LauncherType.RIOT: {
            'name': 'Riot Client',
            'registry_keys': [
                r'SOFTWARE\Riot Games'
            ],
            'default_paths': [
                r'C:\Riot Games',
                r'C:\Program Files\Riot Games',
                r'C:\Program Files (x86)\Riot Games'
            ],
            'executable': r'Riot ClientRiotClientServices.exe',
            'library_folders': [],
            'config_files': [],
            'overlay_name': 'Riot Vanguard',
            'process_name': 'RiotClientServices.exe'
        }
    }
    
    def __init__(self, wmi_helper=None):
        """
        Initialize game launcher detector
        
        Args:
            wmi_helper: WMI helper instance
        """
        self.wmi_helper = wmi_helper
        self.errors: List[str] = []
        
    def detect_all_launchers(self) -> GameLauncherResult:
        """
        Detect all game launchers installed on the system
        
        Returns:
            GameLauncherResult with detection results
        """
        result = GameLauncherResult()
        
        # Get currently running processes
        running_processes = self._get_running_processes()
        
        # Check each launcher type
        for launcher_type in LauncherType:
            if launcher_type == LauncherType.UNKNOWN:
                continue
            
            try:
                launcher_info = self._detect_launcher(launcher_type, running_processes)
                result.total_launchers += 1
                
                if launcher_info.status == LauncherStatus.INSTALLED:
                    result.installed_launchers.append(launcher_info)
                    result.total_games += launcher_info.games_count
                    
                    if launcher_info.is_running:
                        result.running_launchers.append(launcher_info.name)
                        
                elif launcher_info.status == LauncherStatus.NOT_INSTALLED:
                    result.not_installed.append(launcher_type)
                    
            except Exception as e:
                self.errors.append(f"Error detecting {launcher_type.value}: {e}")
        
        # Calculate storage used
        result.storage_used_gb = self._calculate_storage(result.installed_launchers)
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        return result
    
    def _detect_launcher(self, launcher_type: LauncherType, running_processes: List[str]) -> LauncherInfo:
        """Detect a specific launcher"""
        config = self.LAUNCHER_CONFIGS.get(launcher_type)
        
        if not config:
            return LauncherInfo(
                name=launcher_type.value,
                type=launcher_type,
                status=LauncherStatus.NOT_INSTALLED
            )
        
        info = LauncherInfo(
            name=config['name'],
            type=launcher_type,
            status=LauncherStatus.NOT_INSTALLED
        )
        
        # Try to find via registry
        install_path = self._get_registry_install_path(config['registry_keys'])
        
        # Fallback to default paths
        if not install_path:
            install_path = self._check_default_paths(config['default_paths'])
        
        if install_path:
            info.status = LauncherStatus.INSTALLED
            info.install_path = Path(install_path)
            
            # Check for executable
            exe_path = info.install_path / config['executable']
            if exe_path.exists():
                info.executable_path = exe_path
            
            # Get version
            info.version = self._get_launcher_version(info.install_path, config)
            
            # Check if running
            info.is_running = config['process_name'].lower() in [p.lower() for p in running_processes]
            if info.is_running:
                info.status = LauncherStatus.RUNNING
            
            # Detect library paths
            info.library_paths = self._detect_library_paths(info.install_path, config['library_folders'])
            
            # Count games
            info.games_count = self._count_games(info.library_paths, launcher_type)
            
            # Check configuration
            self._check_launcher_config(info, config)
            
            # Check for issues
            info.issues = self._check_launcher_issues(info)
        
        return info
    
    def _get_registry_install_path(self, registry_keys: List[str]) -> Optional[str]:
        """Get install path from registry"""
        try:
            import winreg
            
            for key_path in registry_keys:
                try:
                    # Try 64-bit registry first
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    try:
                        install_path, _ = winreg.QueryValueEx(key, 'InstallPath')
                        if install_path and Path(install_path).exists():
                            winreg.CloseKey(key)
                            return install_path
                    except:
                        pass
                    winreg.CloseKey(key)
                    
                    # Try 32-bit registry
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                    try:
                        install_path, _ = winreg.QueryValueEx(key, 'InstallPath')
                        if install_path and Path(install_path).exists():
                            winreg.CloseKey(key)
                            return install_path
                    except:
                        pass
                    winreg.CloseKey(key)
                    
                except:
                    continue
                    
        except ImportError:
            pass
        except Exception as e:
            self.errors.append(f"Registry read error: {e}")
        
        return None
    
    def _check_default_paths(self, default_paths: List[str]) -> Optional[str]:
        """Check default installation paths"""
        for path in default_paths:
            if Path(path).exists():
                return path
        return None
    
    def _get_launcher_version(self, install_path: Path, config: Dict) -> Optional[str]:
        """Get launcher version"""
        try:
            # Try to get version from executable
            exe_path = install_path / config['executable']
            if exe_path.exists():
                return self._get_file_version(str(exe_path))
            
            # Fallback: check for version files
            version_files = ['version.txt', 'version', 'VERSION']
            for vf in version_files:
                vf_path = install_path / vf
                if vf_path.exists():
                    return vf_path.read_text().strip()
                    
        except Exception:
            pass
        
        return None
    
    def _get_file_version(self, filepath: str) -> Optional[str]:
        """Get version from file"""
        try:
            import ctypes
            from ctypes import wintypes
            
            wapi = ctypes.windll.version
            dwLen = wapi.GetFileVersionInfoSizeW(filepath, None)
            
            if dwLen == 0:
                return None
            
            buf = ctypes.create_string_buffer(dwLen)
            wapi.GetFileVersionInfoW(filepath, 0, dwLen, buf)
            
            uLen = wintypes.UINT()
            lpBuf = ctypes.c_void_p()
            
            if wapi.VerQueryValueW(buf, r'\\VarFileInfo\\Translation', ctypes.byref(lpBuf), ctypes.byref(uLen)):
                lang = ctypes.cast(lpBuf, ctypes.POINTER(wintypes.DWORD)).contents.value
                str_info = f'\\StringFileInfo\\{lang:08x}\\FileVersion'
                
                if wapi.VerQueryValueW(buf, str_info, ctypes.byref(lpBuf), ctypes.byref(uLen)):
                    return ctypes.wstring_at(lpBuf.value)
                    
        except:
            pass
        
        return None
    
    def _get_running_processes(self) -> List[str]:
        """Get list of running process names"""
        processes = []
        
        try:
            if self.wmi_helper and self.wmi_helper.is_available:
                result = self.wmi_helper.query("Win32_Process", fields=["Name"])
                if hasattr(result, 'success') and result.success:
                    processes = [proc.get('Name', '') for proc in result.data if proc.get('Name')]
        except:
            pass
        
        return processes
    
    def _detect_library_paths(self, install_path: Path, library_folders: List[str]) -> List[Path]:
        """Detect game library paths"""
        paths = []
        
        for folder in library_folders:
            lib_path = install_path / folder
            if lib_path.exists():
                paths.append(lib_path)
        
        # Check for additional library paths (Steam-specific)
        if install_path.exists():
            steamapps_path = install_path / 'steamapps'
            if steamapps_path.exists():
                libraryfolders_path = steamapps_path / 'libraryfolders.vdf'
                if libraryfolders_path.exists():
                    additional_paths = self._parse_steam_library_folders(libraryfolders_path)
                    paths.extend(additional_paths)
        
        return paths
    
    def _parse_steam_library_folders(self, vdf_path: Path) -> List[Path]:
        """Parse Steam libraryfolders.vdf"""
        paths = []
        
        try:
            content = vdf_path.read_text(encoding='utf-8')
            # Find paths in VDF format
            matches = re.findall(r'"path"\s+"([^"]+)"', content)
            for match in matches:
                # Convert escaped backslashes
                path = match.replace('\\\\', '\\')
                if Path(path).exists():
                    paths.append(Path(path))
        except:
            pass
        
        return paths
    
    def _count_games(self, library_paths: List[Path], launcher_type: LauncherType) -> int:
        """Count games in library"""
        count = 0
        
        for lib_path in library_paths:
            try:
                if launcher_type == LauncherType.STEAM:
                    # Count Steam apps
                    for item in lib_path.iterdir():
                        if item.name.startswith('appmanifest_'):
                            count += 1
                        elif item.is_dir() and item.name == 'common':
                            count += sum(1 for _ in item.iterdir() if item.is_dir())
                            
                elif launcher_type == LauncherType.EPIC:
                    # Check Epic manifest files
                    manifest_path = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'Epic' / 'EpicGamesLauncher' / 'Data' / 'Manifests'
                    if manifest_path.exists():
                        count += sum(1 for _ in manifest_path.glob('*.item'))
                        
                else:
                    # Generic: count subdirectories
                    if lib_path.exists():
                        count += sum(1 for item in lib_path.iterdir() if item.is_dir())
                        
            except:
                pass
        
        return count
    
    def _check_launcher_config(self, info: LauncherInfo, config: Dict) -> None:
        """Check launcher configuration"""
        # Check for overlay setting
        info.overlay_enabled = self._check_overlay_enabled(info.type, info.install_path, config)
        
        # Check auto-start setting
        info.auto_start = self._check_auto_start(info.type)
        
        # Check cloud saves
        info.cloud_saves_enabled = self._check_cloud_saves(info.type, info.install_path)
    
    def _check_overlay_enabled(self, launcher_type: LauncherType, install_path: Path, config: Dict) -> bool:
        """Check if overlay is enabled"""
        try:
            if launcher_type == LauncherType.STEAM:
                # Check Steam settings
                config_path = install_path / 'config' / 'config.vdf'
                if config_path.exists():
                    content = config_path.read_text()
                    return r'"InGameOverlayEnable"\s*"1"' in content
                    
            elif launcher_type == LauncherType.EPIC:
                # Epic overlay is usually enabled by default
                return True
                
        except:
            pass
        
        return True  # Assume enabled if we can't check
    
    def _check_auto_start(self, launcher_type: LauncherType) -> bool:
        """Check if launcher starts with Windows"""
        try:
            import winreg
            
            run_key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_READ)
            
            launcher_names = {
                LauncherType.STEAM: 'Steam',
                LauncherType.EPIC: 'EpicGamesLauncher',
                LauncherType.EA: 'EADesktop',
                LauncherType.UBISOFT: 'UbisoftConnect',
                LauncherType.BATTLE_NET: 'Battle.net',
                LauncherType.GOG: 'GOG Galaxy'
            }
            
            search_name = launcher_names.get(launcher_type, launcher_type.value)
            
            try:
                index = 0
                while True:
                    name, value, _ = winreg.EnumValue(key, index)
                    if search_name.lower() in name.lower():
                        winreg.CloseKey(key)
                        return True
                    index += 1
            except WindowsError:
                pass
                
            winreg.CloseKey(key)
            
        except:
            pass
        
        return False
    
    def _check_cloud_saves(self, launcher_type: LauncherType, install_path: Path) -> bool:
        """Check if cloud saves are enabled"""
        # Most launchers have cloud saves enabled by default
        # Detailed check would require parsing launcher-specific config
        return True
    
    def _check_launcher_issues(self, info: LauncherInfo) -> List[str]:
        """Check for launcher-specific issues"""
        issues = []
        
        # Check if launcher is running but overlay might conflict
        if info.is_running and info.overlay_enabled:
            issues.append(f"{info.name} overlay is enabled - may conflict with other overlays")
        
        # Check auto-start (can slow down system)
        if info.auto_start:
            issues.append(f"{info.name} is set to auto-start - may impact boot time")
        
        # Check for missing executable
        if info.executable_path and not info.executable_path.exists():
            issues.append(f"{info.name} executable not found at expected path")
        
        return issues
    
    def _calculate_storage(self, launchers: List[LauncherInfo]) -> float:
        """Calculate total storage used by games"""
        total_gb = 0.0
        
        for launcher in launchers:
            for lib_path in launcher.library_paths:
                try:
                    if lib_path.exists():
                        # Calculate size of library folder
                        for item in lib_path.iterdir():
                            if item.is_dir():
                                total_gb += self._get_folder_size(item) / (1024**3)
                except:
                    pass
        
        return round(total_gb, 2)
    
    def _get_folder_size(self, folder: Path) -> int:
        """Get total size of folder in bytes"""
        total = 0
        
        try:
            for item in folder.rglob('*'):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except:
                        pass
        except:
            pass
        
        return total
    
    def _generate_recommendations(self, result: GameLauncherResult) -> List[str]:
        """Generate recommendations based on detection results"""
        recommendations = []
        
        # Check for multiple running launchers
        if len(result.running_launchers) > 2:
            recommendations.append(
                f"Multiple launchers running ({len(result.running_launchers)}). "
                "Close unused launchers to free up system resources."
            )
        
        # Check for overlay conflicts
        overlays_enabled = sum(1 for l in result.installed_launchers if l.overlay_enabled)
        if overlays_enabled > 1:
            recommendations.append(
                f"Multiple overlays enabled ({overlays_enabled}). "
                "Consider disabling unused overlays to prevent conflicts."
            )
        
        # Check storage
        if result.storage_used_gb > 500:
            recommendations.append(
                f"Large game library detected ({result.storage_used_gb:.1f} GB). "
                "Consider archiving unused games to free disk space."
            )
        
        # Check auto-start launchers
        auto_start_count = sum(1 for l in result.installed_launchers if l.auto_start)
        if auto_start_count > 2:
            recommendations.append(
                f"{auto_start_count} launchers set to auto-start. "
                "Disable auto-start for launchers you don't use frequently."
            )
        
        return recommendations
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during detection"""
        return self.errors


__all__ = [
    'GameLauncherDetector',
    'GameLauncherResult',
    'LauncherInfo',
    'LauncherType',
    'LauncherStatus'
]