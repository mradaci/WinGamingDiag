"""
WinGamingDiag - Historical Tracking
Tracks diagnostic history and trends over time
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib


@dataclass
class HistoricalDataPoint:
    """A single historical data point from a scan"""
    timestamp: datetime
    scan_id: str
    health_score: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_issues: int
    
    # System info
    cpu_name: Optional[str] = None
    memory_gb: float = 0.0
    gpu_name: Optional[str] = None
    
    # Performance metrics
    memory_usage_percent: float = 0.0
    storage_usage_percent: float = 0.0
    
    @classmethod
    def from_result(cls, result) -> 'HistoricalDataPoint':
        """Create data point from DiagnosticResult"""
        snapshot = result.snapshot
        
        return cls(
            timestamp=snapshot.timestamp,
            scan_id=result.scan_id,
            health_score=result.health_score,
            critical_count=result.critical_count,
            high_count=result.high_count,
            medium_count=result.medium_count,
            low_count=result.low_count,
            total_issues=len(result.issues),
            cpu_name=snapshot.hardware.cpu.name if snapshot.hardware.cpu else None,
            memory_gb=snapshot.hardware.memory.total_gb if snapshot.hardware.memory else 0.0,
            gpu_name=snapshot.hardware.gpus[0].name if snapshot.hardware.gpus else None,
            memory_usage_percent=(snapshot.hardware.memory.used_gb / snapshot.hardware.memory.total_gb * 100) if snapshot.hardware.memory and snapshot.hardware.memory.total_gb > 0 else 0.0,
            storage_usage_percent=cls._calc_storage_usage(snapshot)
        )
    
    @staticmethod
    def _calc_storage_usage(snapshot) -> float:
        """Calculate average storage usage"""
        if not snapshot.hardware.storage_devices:
            return 0.0
        
        total_usage = 0
        count = 0
        for storage in snapshot.hardware.storage_devices:
            if storage.total_gb > 0:
                total_usage += (storage.used_gb / storage.total_gb * 100)
                count += 1
        
        return total_usage / count if count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'scan_id': self.scan_id,
            'health_score': self.health_score,
            'critical_count': self.critical_count,
            'high_count': self.high_count,
            'medium_count': self.medium_count,
            'low_count': self.low_count,
            'total_issues': self.total_issues,
            'cpu_name': self.cpu_name,
            'memory_gb': self.memory_gb,
            'gpu_name': self.gpu_name,
            'memory_usage_percent': self.memory_usage_percent,
            'storage_usage_percent': self.storage_usage_percent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoricalDataPoint':
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            scan_id=data['scan_id'],
            health_score=data['health_score'],
            critical_count=data.get('critical_count', 0),
            high_count=data.get('high_count', 0),
            medium_count=data.get('medium_count', 0),
            low_count=data.get('low_count', 0),
            total_issues=data.get('total_issues', 0),
            cpu_name=data.get('cpu_name'),
            memory_gb=data.get('memory_gb', 0.0),
            gpu_name=data.get('gpu_name'),
            memory_usage_percent=data.get('memory_usage_percent', 0.0),
            storage_usage_percent=data.get('storage_usage_percent', 0.0)
        )


@dataclass
class TrendAnalysis:
    """Analysis of trends over time"""
    period_days: int
    data_points: int
    
    # Health score trends
    avg_health_score: float
    health_score_change: float  # Positive = improving
    
    # Issue trends
    avg_critical: float
    avg_high: float
    avg_medium: float
    avg_low: float
    
    # Performance trends
    avg_memory_usage: float
    avg_storage_usage: float
    
    # Changes
    issues_improving: bool
    performance_stable: bool
    recommendations: List[str] = field(default_factory=list)


class HistoricalTracker:
    """
    Tracks diagnostic history and provides trend analysis.
    Stores data locally in JSON format with privacy protection.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize historical tracker
        
        Args:
            data_dir: Directory to store historical data (default: AppData/WinGamingDiag)
        """
        if data_dir is None:
            # Use AppData/Local for Windows
            self.data_dir = Path.home() / "AppData" / "Local" / "WinGamingDiag"
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "scan_history.json"
        self.max_history_days = 365  # Keep 1 year of history
        
    def record_scan(self, result) -> bool:
        """
        Record a new scan result to history
        
        Args:
            result: DiagnosticResult to record
            
        Returns:
            True if successfully recorded
        """
        try:
            # Load existing history
            history = self._load_history()
            
            # Create data point
            data_point = HistoricalDataPoint.from_result(result)
            
            # Check if this scan ID already exists
            existing_ids = {dp.scan_id for dp in history}
            if data_point.scan_id in existing_ids:
                return True  # Already recorded
            
            # Add to history
            history.append(data_point)
            
            # Clean old entries
            history = self._clean_old_entries(history)
            
            # Save history
            self._save_history(history)
            
            return True
            
        except Exception as e:
            print(f"Error recording scan history: {e}")
            return False
    
    def get_history(self, days: int = 30) -> List[HistoricalDataPoint]:
        """
        Get historical data for specified period
        
        Args:
            days: Number of days to retrieve (default: 30)
            
        Returns:
            List of historical data points
        """
        history = self._load_history()
        
        # Filter by date
        cutoff = datetime.now() - timedelta(days=days)
        filtered = [dp for dp in history if dp.timestamp >= cutoff]
        
        # Sort by timestamp
        filtered.sort(key=lambda x: x.timestamp)
        
        return filtered
    
    def analyze_trends(self, days: int = 30) -> Optional[TrendAnalysis]:
        """
        Analyze trends over specified period
        
        Args:
            days: Number of days to analyze (default: 30)
            
        Returns:
            TrendAnalysis or None if insufficient data
        """
        history = self.get_history(days)
        
        if len(history) < 2:
            return None  # Need at least 2 data points for trend analysis
        
        # Calculate averages
        avg_health = sum(dp.health_score for dp in history) / len(history)
        avg_critical = sum(dp.critical_count for dp in history) / len(history)
        avg_high = sum(dp.high_count for dp in history) / len(history)
        avg_medium = sum(dp.medium_count for dp in history) / len(history)
        avg_low = sum(dp.low_count for dp in history) / len(history)
        avg_memory = sum(dp.memory_usage_percent for dp in history) / len(history)
        avg_storage = sum(dp.storage_usage_percent for dp in history) / len(history)
        
        # Calculate changes (first half vs second half)
        mid = len(history) // 2
        first_half = history[:mid]
        second_half = history[mid:]
        
        if first_half and second_half:
            first_health = sum(dp.health_score for dp in first_half) / len(first_half)
            second_health = sum(dp.health_score for dp in second_half) / len(second_half)
            health_change = second_health - first_health
            
            first_issues = sum(dp.total_issues for dp in first_half) / len(first_half)
            second_issues = sum(dp.total_issues for dp in second_half) / len(second_half)
            issues_improving = second_issues < first_issues
        else:
            health_change = 0
            issues_improving = False
        
        # Generate recommendations
        recommendations = self._generate_trend_recommendations(
            avg_health, health_change, avg_critical, avg_high, avg_memory, avg_storage
        )
        
        return TrendAnalysis(
            period_days=days,
            data_points=len(history),
            avg_health_score=avg_health,
            health_score_change=health_change,
            avg_critical=avg_critical,
            avg_high=avg_high,
            avg_medium=avg_medium,
            avg_low=avg_low,
            avg_memory_usage=avg_memory,
            avg_storage_usage=avg_storage,
            issues_improving=issues_improving,
            performance_stable=(health_change > -5 and health_change < 5),
            recommendations=recommendations
        )
    
    def get_system_changes(self, days: int = 30) -> Dict[str, Any]:
        """
        Detect system changes over time
        
        Args:
            days: Number of days to check (default: 30)
            
        Returns:
            Dictionary of detected changes
        """
        history = self.get_history(days)
        
        if len(history) < 2:
            return {'changes': [], 'message': 'Insufficient data for change detection'}
        
        oldest = history[0]
        newest = history[-1]
        
        changes = []
        
        # Check CPU change
        if oldest.cpu_name != newest.cpu_name:
            changes.append({
                'type': 'cpu',
                'old': oldest.cpu_name,
                'new': newest.cpu_name,
                'date': newest.timestamp.isoformat()
            })
        
        # Check GPU change
        if oldest.gpu_name != newest.gpu_name:
            changes.append({
                'type': 'gpu',
                'old': oldest.gpu_name,
                'new': newest.gpu_name,
                'date': newest.timestamp.isoformat()
            })
        
        # Check memory change
        if abs(oldest.memory_gb - newest.memory_gb) > 0.5:  # 0.5 GB threshold
            changes.append({
                'type': 'memory',
                'old': f"{oldest.memory_gb:.1f} GB",
                'new': f"{newest.memory_gb:.1f} GB",
                'date': newest.timestamp.isoformat()
            })
        
        return {
            'changes': changes,
            'scan_count': len(history),
            'period_days': days,
            'message': f"Detected {len(changes)} system changes" if changes else "No major hardware changes detected"
        }
    
    def export_history(self, output_path: str) -> bool:
        """
        Export history to JSON file
        
        Args:
            output_path: Path to export file
            
        Returns:
            True if successful
        """
        try:
            history = self._load_history()
            data = {
                'export_date': datetime.now().isoformat(),
                'total_scans': len(history),
                'data_points': [dp.to_dict() for dp in history]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error exporting history: {e}")
            return False
    
    def clear_history(self) -> bool:
        """Clear all historical data"""
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
    
    def _load_history(self) -> List[HistoricalDataPoint]:
        """Load history from file"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # Old format - just a list
                return [HistoricalDataPoint.from_dict(dp) for dp in data]
            elif isinstance(data, dict) and 'data_points' in data:
                # New format with metadata
                return [HistoricalDataPoint.from_dict(dp) for dp in data['data_points']]
            else:
                return []
                
        except Exception:
            return []
    
    def _save_history(self, history: List[HistoricalDataPoint]) -> None:
        """Save history to file"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_scans': len(history),
            'data_points': [dp.to_dict() for dp in history]
        }
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _clean_old_entries(self, history: List[HistoricalDataPoint]) -> List[HistoricalDataPoint]:
        """Remove entries older than max_history_days"""
        cutoff = datetime.now() - timedelta(days=self.max_history_days)
        return [dp for dp in history if dp.timestamp >= cutoff]
    
    def _generate_trend_recommendations(self, avg_health: float, health_change: float,
                                       avg_critical: float, avg_high: float,
                                       avg_memory: float, avg_storage: float) -> List[str]:
        """Generate recommendations based on trends"""
        recommendations = []
        
        # Health score trend
        if health_change < -10:
            recommendations.append(
                f"⚠️ System health declining by {abs(health_change):.1f} points. "
                "Review recent changes and address new issues."
            )
        elif health_change > 10:
            recommendations.append(
                f"✓ System health improving by {health_change:.1f} points. "
                "Keep up the good maintenance!"
            )
        
        # Issue trends
        if avg_critical > 0:
            recommendations.append(
                f"🔴 Averaging {avg_critical:.1f} critical issues per scan. "
                "Address critical issues immediately."
            )
        
        if avg_high > 2:
            recommendations.append(
                f"⚠️ Averaging {avg_high:.1f} high-severity issues. "
                "Consider systematic improvements."
            )
        
        # Performance trends
        if avg_memory > 85:
            recommendations.append(
                f"💾 Memory usage averaging {avg_memory:.1f}%. "
                "Consider upgrading RAM or closing background apps."
            )
        
        if avg_storage > 90:
            recommendations.append(
                f"💿 Storage usage averaging {avg_storage:.1f}%. "
                "Free up space to prevent performance issues."
            )
        
        if not recommendations:
            recommendations.append("✓ System trends look stable. No immediate action required.")
        
        return recommendations


__all__ = ['HistoricalTracker', 'HistoricalDataPoint', 'TrendAnalysis']