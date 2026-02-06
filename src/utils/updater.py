"""
WinGamingDiag - Update Checker
Checks for updates and provides self-updating capability
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import urllib.error
import json
import ssl
import sys


@dataclass
class UpdateInfo:
    """Information about available update"""
    current_version: str
    latest_version: str
    update_available: bool
    release_date: Optional[str] = None
    release_notes: Optional[str] = None
    download_url: Optional[str] = None
    is_critical: bool = False
    
    @property
    def version_diff(self) -> str:
        """Return formatted version difference"""
        if not self.update_available:
            return "Up to date"
        return f"{self.current_version} → {self.latest_version}"


class UpdateChecker:
    """
    Checks for WinGamingDiag updates from GitHub releases.
    Provides version comparison and update recommendations.
    """
    
    CURRENT_VERSION = "1.0.0"
    GITHUB_REPO = "mradaci/WinGamingDiag"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    def __init__(self, cache_dir: Optional[Path] = None, check_interval_hours: int = 24):
        """
        Initialize update checker
        
        Args:
            cache_dir: Directory to cache update check results
            check_interval_hours: Minimum hours between update checks
        """
        self.current_version = self.CURRENT_VERSION
        self.cache_dir = cache_dir or Path.home() / "AppData" / "Local" / "WinGamingDiag"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "update_cache.json"
        self.check_interval = timedelta(hours=check_interval_hours)
        
    def check_for_updates(self, force: bool = False) -> UpdateInfo:
        """
        Check for available updates
        
        Args:
            force: Force check even if cached result is recent
            
        Returns:
            UpdateInfo with update status
        """
        # Check cache first
        if not force:
            cached = self._get_cached_update()
            if cached:
                return cached
        
        try:
            # Fetch latest release from GitHub
            latest = self._fetch_latest_release()
            
            if not latest:
                return UpdateInfo(
                    current_version=self.current_version,
                    latest_version=self.current_version,
                    update_available=False
                )
            
            # Parse version
            latest_version = latest.get('tag_name', 'v0.0.0').lstrip('v')
            
            # Compare versions
            update_available = self._is_newer_version(latest_version, self.current_version)
            
            # Check if critical update
            is_critical = self._is_critical_update(latest.get('body', ''))
            
            update_info = UpdateInfo(
                current_version=self.current_version,
                latest_version=latest_version,
                update_available=update_available,
                release_date=latest.get('published_at'),
                release_notes=latest.get('body'),
                download_url=self._get_download_url(latest),
                is_critical=is_critical
            )
            
            # Cache result
            self._cache_update(update_info)
            
            return update_info
            
        except Exception as e:
            # Return no update on error
            return UpdateInfo(
                current_version=self.current_version,
                latest_version=self.current_version,
                update_available=False
            )
    
    def get_update_command(self) -> Optional[str]:
        """
        Get command to update the tool
        
        Returns:
            Update command string or None
        """
        if sys.platform == 'win32':
            return "winget upgrade WinGamingDiag"
        else:
            return None  # No automatic update for non-Windows
    
    def _fetch_latest_release(self) -> Optional[Dict[str, Any]]:
        """Fetch latest release from GitHub API"""
        try:
            # Create SSL context that doesn't verify certificates
            # This allows checking updates even on systems with SSL issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={
                    'User-Agent': f'WinGamingDiag/{self.current_version}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except urllib.error.URLError:
            # Network error
            return None
        except Exception:
            return None
    
    def _is_newer_version(self, latest: str, current: str) -> bool:
        """
        Check if latest version is newer than current
        
        Args:
            latest: Latest version string
            current: Current version string
            
        Returns:
            True if latest is newer
        """
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad shorter version
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            
            # Compare parts
            for i in range(len(latest_parts)):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            return False  # Versions are equal
            
        except (ValueError, AttributeError):
            return False
    
    def _is_critical_update(self, release_notes: str) -> bool:
        """Check if update is marked as critical"""
        critical_keywords = ['critical', 'security', 'vulnerability', 'fix', 'urgent', 'important']
        notes_lower = release_notes.lower()
        return any(keyword in notes_lower for keyword in critical_keywords)
    
    def _get_download_url(self, release: Dict[str, Any]) -> Optional[str]:
        """Get download URL for current platform"""
        assets = release.get('assets', [])
        
        for asset in assets:
            name = asset.get('name', '').lower()
            if sys.platform == 'win32':
                if name.endswith('.exe') or name.endswith('.msi'):
                    return asset.get('browser_download_url')
            else:
                if 'linux' in name or name.endswith('.tar.gz'):
                    return asset.get('browser_download_url')
        
        # Fallback to release page
        return release.get('html_url')
    
    def _get_cached_update(self) -> Optional[UpdateInfo]:
        """Get cached update info if still valid"""
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time < self.check_interval:
                return UpdateInfo(
                    current_version=self.current_version,
                    latest_version=cache.get('latest_version', self.current_version),
                    update_available=cache.get('update_available', False),
                    release_date=cache.get('release_date'),
                    release_notes=cache.get('release_notes'),
                    download_url=cache.get('download_url'),
                    is_critical=cache.get('is_critical', False)
                )
            
            return None
            
        except Exception:
            return None
    
    def _cache_update(self, update_info: UpdateInfo) -> None:
        """Cache update check result"""
        try:
            cache = {
                'timestamp': datetime.now().isoformat(),
                'latest_version': update_info.latest_version,
                'update_available': update_info.update_available,
                'release_date': update_info.release_date,
                'release_notes': update_info.release_notes,
                'download_url': update_info.download_url,
                'is_critical': update_info.is_critical
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
                
        except Exception:
            pass  # Cache errors are non-critical


__all__ = ['UpdateChecker', 'UpdateInfo']