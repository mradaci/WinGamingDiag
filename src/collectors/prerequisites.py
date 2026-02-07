"""
WinGamingDiag - Gaming Prerequisites Checker
Checks for essential gaming dependencies like Visual C++, DirectX, and Game Mode
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import os
import ctypes
from pathlib import Path

@dataclass
class PrerequisiteInfo:
    """Information about a gaming prerequisite"""
    name: str
    installed: bool
    version: Optional[str] = None
    details: str = ""
    critical: bool = True

@dataclass
class PrerequisitesResult:
    """Result of prerequisites check"""
    items: List[PrerequisiteInfo] = field(default_factory=list)
    missing_critical: int = 0
    game_mode_enabled: bool = False
    
class PrerequisitesChecker:
    """
    Checks for presence of critical gaming libraries and settings.
    """
    
    def check_all(self) -> PrerequisitesResult:
        result = PrerequisitesResult()
        
        # Check Visual C++
        vc_results = self._check_vc_redists()
        result.items.extend(vc_results)
        
        # Check DirectX
        dx_result = self._check_directx()
        result.items.append(dx_result)
        
        # Check Game Mode
        result.game_mode_enabled = self._check_game_mode()
        
        # Count missing criticals
        result.missing_critical = sum(1 for item in result.items if item.critical and not item.installed)
        
        return result

    def _check_vc_redists(self) -> List[PrerequisiteInfo]:
        results = []
        
        # VC++ 2015-2022 is the most critical one for modern games
        is_installed, version = self._check_registry_key(
            r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64", 
            "Version"
        )
        
        results.append(PrerequisiteInfo(
            name="Visual C++ 2015-2022 Redistributable (x64)",
            installed=is_installed,
            version=version,
            critical=True,
            details="Required for most modern games built with Unreal Engine, Unity, and other frameworks."
        ))
        
        # Also check x86 version (some older games still need it)
        is_installed_x86, version_x86 = self._check_registry_key(
            r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x86",
            "Version"
        )
        
        results.append(PrerequisiteInfo(
            name="Visual C++ 2015-2022 Redistributable (x86)",
            installed=is_installed_x86,
            version=version_x86,
            critical=False,  # x64 is more critical for modern gaming
            details="Required for some 32-bit games and applications."
        ))
        
        return results

    def _check_directx(self) -> PrerequisiteInfo:
        # Checking for d3d12.dll is a reliable way to check for DX12 support availability
        system_folder = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
        d3d12_path = os.path.join(system_folder, 'd3d12.dll')
        d3d11_path = os.path.join(system_folder, 'd3d11.dll')
        dxgi_path = os.path.join(system_folder, 'dxgi.dll')
        
        has_d3d12 = os.path.exists(d3d12_path)
        has_d3d11 = os.path.exists(d3d11_path)
        has_dxgi = os.path.exists(dxgi_path)
        
        if has_d3d12:
            version = "DirectX 12"
            installed = True
        elif has_d3d11 and has_dxgi:
            version = "DirectX 11"
            installed = True
        else:
            version = "Unknown / Missing"
            installed = False
        
        return PrerequisiteInfo(
            name="DirectX Runtime",
            installed=installed,
            version=version,
            critical=True,
            details="Graphics API required for all modern games. DX12 is preferred for new titles."
        )

    def _check_game_mode(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\GameBar", 
                0, 
                winreg.KEY_READ
            )
            # AllowAutoGameMode: 1 = On, 0 = Off
            val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
            winreg.CloseKey(key)
            return val == 1
        except Exception:
            # Default is usually On in Windows 10/11 if key is missing
            return True

    def _check_registry_key(self, path: str, value_name: str) -> Tuple[bool, Optional[str]]:
        try:
            import winreg
            # Try HKLM first
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return True, str(val)
        except OSError:  # WindowsError is a subclass of OSError, this works on all platforms
            return False, None
        except Exception:
            return False, None
