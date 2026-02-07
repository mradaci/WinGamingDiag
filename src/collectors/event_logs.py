"""
WinGamingDiag - Event Log Collector
Collects and analyzes Windows Event Logs for gaming-related issues
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


class EventLevel(Enum):
    """Windows Event Log levels"""
    CRITICAL = 1
    ERROR = 2
    WARNING = 3
    INFORMATION = 4
    VERBOSE = 5


@dataclass
class EventLogEntry:
    """Represents a Windows Event Log entry"""
    timestamp: datetime
    level: EventLevel
    source: str
    event_id: int
    message: str
    category: Optional[str] = None
    user: Optional[str] = None
    computer: Optional[str] = None
    related_to_gaming: bool = False


@dataclass
class EventLogSummary:
    """Summary of event log analysis"""
    total_events: int = 0
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    gaming_related_events: List[EventLogEntry] = field(default_factory=list)
    recent_crashes: List[EventLogEntry] = field(default_factory=list)
    driver_errors: List[EventLogEntry] = field(default_factory=list)
    system_errors: List[EventLogEntry] = field(default_factory=list)
    analysis_period_days: int = 7
    
    @property
    def app_crashes(self) -> int:
        """Count application crashes (Event ID 1001)"""
        return sum(1 for event in self.recent_crashes if event.event_id == 1001)
    
    @property
    def critical_errors(self) -> int:
        """Total critical errors"""
        return self.critical_count


class EventLogCollector:
    """
    Collects and analyzes Windows Event Logs for gaming-related issues.
    Focuses on application crashes, driver errors, and system stability issues.
    """
    
    # Gaming-related event sources
    GAMING_SOURCES = [
        'Application Error',
        'Application Hang',
        'Windows Error Reporting',
        'Display',
        'Kernel-Power',
        'Kernel-Processor-Power',
        'System',
        'Application',
        'Winlogon',
        'Service Control Manager'
    ]
    
    # Event IDs commonly associated with gaming issues
    CRITICAL_EVENT_IDS = {
        1001: 'Application Crash',
        1002: 'Application Hang',
        41: 'Unexpected Shutdown',
        6008: 'Unexpected Shutdown',
        1074: 'System Shutdown',
        1076: 'Shutdown Reason',
        55: 'NTFS File System Error',
        10016: 'DCOM Permission Error',
        7022: 'Service Hang',
        7023: 'Service Termination Error',
        7024: 'Service Termination Error',
        7026: 'Driver Loading Error',
        7031: 'Service Crash',
        7032: 'Service Recovery Failure',
        7034: 'Service Unexpected Termination'
    }
    
    # Gaming-related keywords in event messages
    GAMING_KEYWORDS = [
        'game', 'steam', 'epic', 'origin', 'battle.net', 'battlenet',
        'uplay', 'ubisoft', 'ea', 'electronic arts', 'riot', 'valorant',
        'league of legends', 'fortnite', 'apex', 'overwatch', 'call of duty',
        'gpu', 'graphics', 'directx', 'dxgi', 'nvidia', 'amd', 'intel',
        'display driver', 'gpu driver', 'graphics driver', 'video driver',
        'd3d', 'opengl', 'vulkan', 'crash', 'hang', 'freeze', 'bsod',
        'blue screen', 'memory', 'access violation', 'exception'
    ]
    
    def __init__(self, wmi_helper=None, days_to_analyze: int = 7):
        """
        Initialize event log collector
        
        Args:
            wmi_helper: WMI helper instance
            days_to_analyze: Number of days of event logs to analyze
        """
        self.wmi_helper = wmi_helper
        self.days_to_analyze = days_to_analyze
        self.errors: List[str] = []
        
    def collect_summary(self, days_back: int = 7) -> EventLogSummary:
        """Collect and analyze event logs (alias for collect_all with days parameter)"""
        self.days_to_analyze = days_back
        return self.collect_all()
    
    def collect_all(self) -> EventLogSummary:
        """
        Collect and analyze event logs
        
        Returns:
            EventLogSummary with analysis results
        """
        summary = EventLogSummary(analysis_period_days=self.days_to_analyze)
        
        try:
            # Collect events from various sources
            system_events = self._collect_system_events()
            application_events = self._collect_application_events()
            
            all_events = system_events + application_events
            
            # Analyze events
            for event in all_events:
                summary.total_events += 1
                
                # Count by level
                if event.level == EventLevel.CRITICAL:
                    summary.critical_count += 1
                elif event.level == EventLevel.ERROR:
                    summary.error_count += 1
                elif event.level == EventLevel.WARNING:
                    summary.warning_count += 1
                
                # Check if gaming-related
                if self._is_gaming_related(event):
                    event.related_to_gaming = True
                    summary.gaming_related_events.append(event)
                
                # Categorize events
                if event.event_id in [1001, 1002]:
                    summary.recent_crashes.append(event)
                elif 'driver' in event.source.lower() or event.event_id in [7026]:
                    summary.driver_errors.append(event)
                elif event.level in [EventLevel.CRITICAL, EventLevel.ERROR]:
                    summary.system_errors.append(event)
            
        except Exception as e:
            self.errors.append(f"Event log collection failed: {e}")
        
        return summary
    
    def _collect_system_events(self) -> List[EventLogEntry]:
        """Collect events from System log"""
        events = []
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.days_to_analyze)
            
            # Query System event log via WMI
            if self.wmi_helper and self.wmi_helper.is_available:
                query = f"""
                    SELECT * FROM Win32_NTLogEvent 
                    WHERE Logfile = 'System' 
                    AND TimeGenerated >= '{cutoff_date.strftime('%Y%m%d%H%M%S')}'
                    AND EventType <= 2
                """
                
                result = self.wmi_helper.query_raw(query)
                
                if hasattr(result, 'success') and result.success:
                    for event_data in result.data:
                        event = self._parse_event(event_data)
                        if event:
                            events.append(event)
            
            # Fallback: Use Windows Event Log API via ctypes
            if not events:
                events = self._collect_events_fallback('System')
                
        except Exception as e:
            self.errors.append(f"System event collection error: {e}")
        
        return events
    
    def _collect_application_events(self) -> List[EventLogEntry]:
        """Collect events from Application log"""
        events = []
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.days_to_analyze)
            
            # Query Application event log via WMI
            if self.wmi_helper and self.wmi_helper.is_available:
                query = f"""
                    SELECT * FROM Win32_NTLogEvent 
                    WHERE Logfile = 'Application' 
                    AND TimeGenerated >= '{cutoff_date.strftime('%Y%m%d%H%M%S')}'
                    AND EventType <= 2
                """
                
                result = self.wmi_helper.query_raw(query)
                
                if hasattr(result, 'success') and result.success:
                    for event_data in result.data:
                        event = self._parse_event(event_data)
                        if event:
                            events.append(event)
            
            # Fallback
            if not events:
                events = self._collect_events_fallback('Application')
                
        except Exception as e:
            self.errors.append(f"Application event collection error: {e}")
        
        return events
    
    def _parse_event(self, event_data: Dict[str, Any]) -> Optional[EventLogEntry]:
        """Parse event data from WMI query result"""
        try:
            # Parse timestamp
            time_generated = event_data.get('TimeGenerated')
            if time_generated:
                if hasattr(time_generated, 'strftime'):
                    timestamp = datetime.strptime(
                        time_generated.strftime('%Y%m%d%H%M%S'),
                        '%Y%m%d%H%M%S'
                    )
                else:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Map EventType to EventLevel
            event_type = event_data.get('EventType', 4)
            level_map = {
                1: EventLevel.CRITICAL,
                2: EventLevel.ERROR,
                3: EventLevel.WARNING,
                4: EventLevel.INFORMATION,
                5: EventLevel.VERBOSE
            }
            level = level_map.get(event_type, EventLevel.INFORMATION)
            
            # Get event ID
            event_id = event_data.get('EventCode', 0)
            if isinstance(event_id, str):
                event_id = int(event_id) if event_id.isdigit() else 0
            
            # Get message
            message = event_data.get('Message', '')
            if isinstance(message, list):
                message = ' '.join(str(m) for m in message)
            
            return EventLogEntry(
                timestamp=timestamp,
                level=level,
                source=event_data.get('SourceName', 'Unknown'),
                event_id=event_id,
                message=message[:500] if message else 'No message',  # Truncate long messages
                category=event_data.get('CategoryString'),
                user=event_data.get('User'),
                computer=event_data.get('ComputerName')
            )
            
        except Exception as e:
            self.errors.append(f"Event parsing error: {e}")
            return None
    
    def _collect_events_fallback(self, log_name: str) -> List[EventLogEntry]:
        """Fallback method to collect events without WMI"""
        events = []
        
        try:
            # Try using win32evtlog if available
            import win32evtlog
            import win32evtlogutil
            
            hand = win32evtlog.OpenEventLog(None, log_name)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            cutoff_date = datetime.now() - timedelta(days=self.days_to_analyze)
            
            while True:
                events_list = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events_list:
                    break
                
                for event in events_list:
                    # Check if within time range
                    event_time = event.TimeGenerated
                    if event_time < cutoff_date:
                        break
                    
                    # Only collect errors and warnings
                    if event.EventType > 3:  # Skip info events
                        continue
                    
                    # Parse event
                    try:
                        message = win32evtlogutil.SafeFormatMessage(event, log_name)
                    except:
                        message = str(event.StringInserts) if event.StringInserts else "No message"
                    
                    level_map = {
                        1: EventLevel.ERROR,
                        2: EventLevel.WARNING,
                        3: EventLevel.INFORMATION
                    }
                    
                    events.append(EventLogEntry(
                        timestamp=event_time,
                        level=level_map.get(event.EventType, EventLevel.INFORMATION),
                        source=event.SourceName,
                        event_id=event.EventID & 0xFFFF,  # Remove severity bits
                        message=message[:500] if message else 'No message'
                    ))
            
            win32evtlog.CloseEventLog(hand)
            
        except ImportError:
            # win32evtlog not available
            pass
        except Exception as e:
            self.errors.append(f"Fallback event collection error: {e}")
        
        return events
    
    def _is_gaming_related(self, event: EventLogEntry) -> bool:
        """Check if an event is related to gaming"""
        message_lower = event.message.lower()
        source_lower = event.source.lower()
        
        # Check gaming sources
        if any(gaming_source.lower() in source_lower for gaming_source in self.GAMING_SOURCES):
            # Check if it's a crash or error
            if event.level in [EventLevel.CRITICAL, EventLevel.ERROR]:
                # Check for gaming keywords
                if any(keyword in message_lower for keyword in self.GAMING_KEYWORDS):
                    return True
        
        # Check for specific crash event IDs
        if event.event_id in [1001, 1002]:  # Application crash/hang
            return True
        
        # Check for graphics/display related errors
        if any(keyword in source_lower for keyword in ['display', 'nvidia', 'amd', 'intel']):
            if event.level in [EventLevel.CRITICAL, EventLevel.ERROR]:
                return True
        
        return False
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered during collection"""
        return self.errors


__all__ = ['EventLogCollector', 'EventLogSummary', 'EventLogEntry', 'EventLevel']