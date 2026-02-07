"""
WinGamingDiag - Background Process Analyzer
Detects bloatware and performance-interfering background processes
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from ..utils.wmi_helper import get_wmi_helper

@dataclass
class ProcessIssue:
    name: str
    pid: int
    description: str
    impact: str = "Medium"

class ProcessAnalyzer:
    """
    Analyzes running processes against a list of known gaming performance interferers.
    Aggressive detection mode - flags anything suspicious.
    """
    
    # Known bloatware/interferers with their impact descriptions
    # Format: Process Name (lowercase) -> (Description, Impact Level)
    BLACKLIST = {
        # Antivirus - High impact
        "mcshield.exe": ("McAfee On-Access Scanner - Real-time scanning causes disk I/O stutter in games", "High"),
        "mcapexe.exe": ("McAfee Anti-Malware Engine - High CPU usage during scans", "High"),
        "mfeann.exe": ("McAfee Module Core Service - Background security scanning", "Medium"),
        "nortonsecurity.exe": ("Norton Security Suite - Heavy background resource usage and real-time scanning", "High"),
        "ns.exe": ("Norton Security - Background protection service", "High"),
        "ccsvchst.exe": ("Symantec Service Framework - Resource intensive security software", "High"),
        "avastsvc.exe": ("Avast Antivirus Service - Real-time protection overhead", "Medium"),
        "avastui.exe": ("Avast User Interface - Additional background processes", "Low"),
        "avp.exe": ("Kaspersky Anti-Virus - Real-time scanning can cause game stutters", "High"),
        "ekrn.exe": ("ESET Kernel Service - On-access scanner overhead", "Medium"),
        
        # RGB and Gaming Software - Medium/High impact
        "corsair.service.exe": ("Corsair iCUE Service - Known for high CPU overhead and polling issues", "High"),
        "icue.exe": ("Corsair iCUE - RGB lighting and peripheral management", "Medium"),
        "lghub.exe": ("Logitech G HUB - Peripheral software with background polling", "Medium"),
        "lghub_agent.exe": ("Logitech G HUB Agent - Background service", "Medium"),
        "steelseriesengine.exe": ("SteelSeries Engine - RGB and peripheral management", "Medium"),
        "rgbfusion.exe": ("Gigabyte RGB Fusion - Lighting control software", "Medium"),
        "aura.exe": ("ASUS Aura - RGB lighting software", "Medium"),
        "lightingservice.exe": ("ASUS Lighting Service - RGB control service", "Medium"),
        "armoury crate.exe": ("ASUS Armoury Crate - Heavy suite with unnecessary background services", "High"),
        "acoms.exe": ("ASUS Armoury Crate Component - Background service", "Medium"),
        "patriotviperrgb.exe": ("Patriot Viper RGB - Memory lighting software", "Low"),
        
        # System Utilities - Medium impact
        "searchindexer.exe": ("Windows Search Indexer - Disk I/O interference during indexing", "Medium"),
        "searchprotocolhost.exe": ("Windows Search Protocol Host - Indexing overhead", "Medium"),
        "onedrive.exe": ("Microsoft OneDrive - Background syncing causes lag spikes", "Medium"),
        "dropbox.exe": ("Dropbox - Background file syncing", "Medium"),
        "googledrivesync.exe": ("Google Drive - Background file synchronization", "Medium"),
        " Creative Cloud.exe": ("Adobe Creative Cloud - Background update checking and syncing", "Medium"),
        "acrotray.exe": ("Adobe Acrobat Tray - Unnecessary background process", "Low"),
        
        # Communication - Low/Medium impact
        "teams.exe": ("Microsoft Teams - Heavy background RAM and CPU usage even when idle", "High"),
        "slack.exe": ("Slack - Background messaging and notification polling", "Medium"),
        "discord.exe": ("Discord - Voice and overlay overhead (consider closing if not using voice)", "Medium"),
        "skype.exe": ("Skype - Background messaging and call monitoring", "Medium"),
        "zoom.exe": ("Zoom - Background process when not in meeting", "Low"),
        
        # Media and Streaming - Medium impact
        "obs64.exe": ("OBS Studio - Recording/streaming software (close if not streaming)", "High"),
        "obs32.exe": ("OBS Studio (32-bit) - Recording/streaming software", "High"),
        "streamlabs obs.exe": ("Streamlabs OBS - Streaming software overhead", "High"),
        "rtss.exe": ("MSI Afterburner RivaTuner - Overlay and frame limiting (can be kept if needed)", "Low"),
        "msiafterburner.exe": ("MSI Afterburner - Hardware monitoring overhead (usually fine to keep)", "Low"),
        
        # Browsers - High impact if many tabs
        "chrome.exe": ("Google Chrome - Very high RAM usage with multiple tabs. Consider closing or using gaming browser mode.", "High"),
        "firefox.exe": ("Mozilla Firefox - High RAM usage with many tabs", "Medium"),
        "msedge.exe": ("Microsoft Edge - High RAM usage with many tabs", "Medium"),
        "opera.exe": ("Opera Browser - RAM usage and background processes", "Medium"),
        "brave.exe": ("Brave Browser - High RAM usage with many tabs", "Medium"),
        
        # Launchers - Medium impact (game-specific)
        "steam.exe": ("Steam Client - Can be closed after launching game if not needed for multiplayer", "Low"),
        "epicgameslauncher.exe": ("Epic Games Launcher - Close after launching game", "Low"),
        "origin.exe": ("EA App/Origin - Close after launching game", "Low"),
        "eadesktop.exe": ("EA Desktop - Background EA services", "Medium"),
        "battle.net.exe": ("Battle.net - Close after launching Blizzard games", "Low"),
        "ubisoftconnect.exe": ("Ubisoft Connect - Background DRM and cloud sync", "Medium"),
        "galaxyclient.exe": ("GOG Galaxy - Close if not using Galaxy features", "Low"),
        
        # Windows Gaming Services - Usually fine but can be optimized
        "gamingservices.exe": ("Windows Gaming Services - Occasionally causes high CPU usage", "Medium"),
        "gamingservicesnet.exe": ("Windows Gaming Services Network - Background service", "Low"),
        "xboxapp.exe": ("Xbox App - Background gaming services", "Medium"),
        "gamebar.exe": ("Xbox Game Bar - Recording and overlay services (disable if not used)", "Low"),
        
        # Miscellaneous
        "utorrent.exe": ("uTorrent - BitTorrent client (heavy disk I/O)", "High"),
        "qbittorrent.exe": ("qBittorrent - BitTorrent client (heavy disk I/O)", "High"),
        "steamwebhelper.exe": ("Steam Web Helper - Multiple instances consume RAM", "Medium"),
        "wallpaperengine.exe": ("Wallpaper Engine - Live wallpapers consume GPU/CPU resources", "Medium"),
        "fences.exe": ("Stardock Fences - Desktop organization (minor overhead)", "Low"),
        "rainmeter.exe": ("Rainmeter - Desktop customization (CPU overhead for widgets)", "Low"),
        "camtasia.exe": ("Camtasia Studio - Screen recording software", "High"),
        "bandicam.exe": ("Bandicam - Screen recording software", "High"),
        "action.exe": ("Mirillis Action - Screen recording software", "High"),
        "fraps.exe": ("FRAPS - Screen recording and FPS overlay", "Medium"),
        "csrss.exe": (""),
    }

    def __init__(self, wmi_helper=None):
        self.wmi = wmi_helper or get_wmi_helper()
        self.issues: List[ProcessIssue] = []

    def check_processes(self) -> List[ProcessIssue]:
        self.issues = []
        if not self.wmi or not self.wmi.is_available:
            return []

        try:
            processes = self.wmi.get_process_info()
            
            for proc in processes:
                name = proc.get('Name', '').lower()
                if name in self.BLACKLIST:
                    description, impact = self.BLACKLIST[name]
                    if description:  # Skip empty descriptions (placeholder entries)
                        self.issues.append(ProcessIssue(
                            name=proc.get('Name'),
                            pid=proc.get('ProcessId', 0),
                            description=description,
                            impact=impact
                        ))
        except Exception as e:
            # Silently fail - process checking is non-critical
            pass
        
        return self.issues
