"""
WinGamingDiag - HTML Report Generator
Generates rich, interactive HTML reports with visual charts and styling
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import json
import base64


@dataclass
class ReportTheme:
    """Theme configuration for HTML reports"""
    primary_color: str = "#2563eb"
    secondary_color: str = "#3b82f6"
    success_color: str = "#10b981"
    warning_color: str = "#f59e0b"
    error_color: str = "#ef4444"
    background_color: str = "#0f172a"
    card_background: str = "#1e293b"
    text_color: str = "#f8fafc"
    text_muted: str = "#94a3b8"


class HTMLReportGenerator:
    """
    Generates rich HTML diagnostic reports with charts, graphs, and interactive elements.
    Creates a professional dashboard-style report that can be viewed in any browser.
    """
    
    def __init__(self, theme: Optional[ReportTheme] = None):
        """
        Initialize HTML report generator
        
        Args:
            theme: Custom theme configuration (uses default if not provided)
        """
        self.theme = theme or ReportTheme()
        
    def generate_report(self, result, output_path: Optional[str] = None) -> str:
        """
        Generate HTML diagnostic report
        
        Args:
            result: DiagnosticResult object
            output_path: Path to save report (default: Desktop)
            
        Returns:
            Path to saved report
        """
        if output_path is None:
            desktop = Path.home() / "Desktop"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = desktop / f"WinGamingDiag_Report_{timestamp}.html"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML content
        html_content = self._build_html(result)
        
        # Write to file
        with open(str(output_file), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def _build_html(self, result) -> str:
        """Build complete HTML document"""
        html_parts = [
            self._build_head(),
            self._build_body(result),
            self._build_scripts(result)
        ]
        
        return '\n'.join(html_parts)
    
    def _build_head(self) -> str:
        """Build HTML head section with styles"""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WinGamingDiag - System Diagnostic Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary: {self.theme.primary_color};
            --secondary: {self.theme.secondary_color};
            --success: {self.theme.success_color};
            --warning: {self.theme.warning_color};
            --error: {self.theme.error_color};
            --bg: {self.theme.background_color};
            --card-bg: {self.theme.card_background};
            --text: {self.theme.text_color};
            --text-muted: {self.theme.text_muted};
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg) 0%, #1a1f2e 100%);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 2rem;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        header .meta {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255,255,255,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}
        
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text);
        }}
        
        .card-icon {{
            font-size: 1.5rem;
            opacity: 0.8;
        }}
        
        .health-score {{
            text-align: center;
            padding: 2rem;
        }}
        
        .score-circle {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1rem;
            font-size: 2.5rem;
            font-weight: bold;
            position: relative;
            background: conic-gradient(var(--success) 0deg, var(--success) calc(var(--score) * 3.6deg), var(--card-bg) calc(var(--score) * 3.6deg));
        }}
        
        .score-circle::before {{
            content: '';
            position: absolute;
            width: 120px;
            height: 120px;
            background: var(--card-bg);
            border-radius: 50%;
        }}
        
        .score-circle span {{
            position: relative;
            z-index: 1;
        }}
        
        .score-label {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .issue-summary {{
            display: flex;
            justify-content: space-around;
            margin-top: 1rem;
        }}
        
        .issue-count {{
            text-align: center;
        }}
        
        .issue-count .number {{
            font-size: 2rem;
            font-weight: bold;
        }}
        
        .issue-count .label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        
        .critical {{ color: var(--error); }}
        .high {{ color: #f97316; }}
        .medium {{ color: var(--warning); }}
        .low {{ color: var(--success); }}
        
        .issue-list {{
            list-style: none;
        }}
        
        .issue-item {{
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-left: 4px solid var(--primary);
            transition: background 0.2s;
        }}
        
        .issue-item:hover {{
            background: rgba(255,255,255,0.06);
        }}
        
        .issue-item.critical {{ border-left-color: var(--error); }}
        .issue-item.high {{ border-left-color: #f97316; }}
        .issue-item.medium {{ border-left-color: var(--warning); }}
        .issue-item.low {{ border-left-color: var(--success); }}
        
        .issue-title {{
            font-weight: 600;
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .issue-badge {{
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        
        .badge-critical {{ background: rgba(239, 68, 68, 0.2); color: var(--error); }}
        .badge-high {{ background: rgba(249, 115, 22, 0.2); color: #f97316; }}
        .badge-medium {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
        .badge-low {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
        
        .issue-description {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}
        
        .issue-recommendation {{
            background: rgba(37, 99, 235, 0.1);
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            color: var(--text);
        }}
        
        .specs-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }}
        
        .spec-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        .spec-label {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .spec-value {{
            font-weight: 600;
            color: var(--text);
        }}
        
        .chart-container {{
            position: relative;
            height: 200px;
            margin-top: 1rem;
        }}
        
        .status-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        .status-good {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }}
        
        .status-warning {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--warning);
        }}
        
        .status-error {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--error);
        }}
        
        .section {{
            margin-bottom: 2rem;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 2rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            header h1 {{
                font-size: 1.75rem;
            }}
            
            .dashboard {{
                grid-template-columns: 1fr;
            }}
            
            .specs-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>'''
    
    def _build_body(self, result) -> str:
        """Build HTML body content"""
        snapshot = result.snapshot
        timestamp = snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S') if snapshot.timestamp else 'Unknown'
        
        body_content = f'''
<body>
    <div class="container">
        <header>
            <h1>🎮 WinGamingDiag Report</h1>
            <div class="meta">
                <p>Generated: {timestamp}</p>
                <p>Scan ID: {result.scan_id}</p>
                <p>Duration: {result.scan_duration_seconds:.1f}s</p>
            </div>
        </header>
        
        <div class="dashboard">
            {self._build_health_card(result)}
            {self._build_issues_card(result)}
            {self._build_hardware_card(snapshot)}
            {self._build_performance_card(snapshot)}
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 Detailed Findings</h2>
            {self._build_issues_list(result.issues)}
        </div>
        
        <div class="section">
            <h2 class="section-title">🖥️ System Specifications</h2>
            {self._build_detailed_specs(snapshot)}
        </div>
        
        <footer class="footer">
            <p>WinGamingDiag - Windows Gaming Diagnostic Tool</p>
            <p>This report is for informational purposes only</p>
        </footer>
    </div>
</body>'''
        
        return body_content
    
    def _build_health_card(self, result) -> str:
        """Build health score card"""
        score = result.health_score
        score_color = self._get_score_color(score)
        
        return f'''
            <div class="card">
                <div class="card-header">
                    <span class="card-title">System Health</span>
                    <span class="card-icon">💚</span>
                </div>
                <div class="health-score">
                    <div class="score-circle" style="--score: {score}; color: {score_color};">
                        <span>{score}</span>
                    </div>
                    <div class="score-label">Health Score</div>
                </div>
            </div>'''
    
    def _build_issues_card(self, result) -> str:
        """Build issues summary card"""
        return f'''
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Issues Summary</span>
                    <span class="card-icon">⚠️</span>
                </div>
                <div class="issue-summary">
                    <div class="issue-count">
                        <div class="number critical">{result.critical_count}</div>
                        <div class="label">Critical</div>
                    </div>
                    <div class="issue-count">
                        <div class="number high">{result.high_count}</div>
                        <div class="label">High</div>
                    </div>
                    <div class="issue-count">
                        <div class="number medium">{result.medium_count}</div>
                        <div class="label">Medium</div>
                    </div>
                    <div class="issue-count">
                        <div class="number low">{result.low_count}</div>
                        <div class="label">Low</div>
                    </div>
                </div>
            </div>'''
    
    def _build_hardware_card(self, snapshot) -> str:
        """Build hardware overview card"""
        cpu_name = snapshot.hardware.cpu.name if snapshot.hardware.cpu else "Unknown"
        gpu_name = snapshot.hardware.gpus[0].name if snapshot.hardware.gpus else "Unknown"
        memory_gb = snapshot.hardware.memory.total_gb if snapshot.hardware.memory else 0
        
        # Truncate long names
        cpu_name = cpu_name[:30] + '...' if len(cpu_name) > 33 else cpu_name
        gpu_name = gpu_name[:30] + '...' if len(gpu_name) > 33 else gpu_name
        
        return f'''
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Hardware Overview</span>
                    <span class="card-icon">🔧</span>
                </div>
                <div class="specs-grid">
                    <div class="spec-item">
                        <span class="spec-label">CPU</span>
                        <span class="spec-value" title="{snapshot.hardware.cpu.name if snapshot.hardware.cpu else 'Unknown'}">{cpu_name}</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">GPU</span>
                        <span class="spec-value" title="{snapshot.hardware.gpus[0].name if snapshot.hardware.gpus else 'Unknown'}">{gpu_name}</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Memory</span>
                        <span class="spec-value">{memory_gb:.1f} GB</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Storage</span>
                        <span class="spec-value">{len(snapshot.hardware.storage_devices)} drives</span>
                    </div>
                </div>
            </div>'''
    
    def _build_performance_card(self, snapshot) -> str:
        """Build performance overview card"""
        memory = snapshot.hardware.memory
        memory_status = "warning" if memory and (memory.used_gb / memory.total_gb * 100) > 80 else "good"
        
        storage_warning = any(
            (s.used_gb / s.total_gb * 100) > 85 
            for s in snapshot.hardware.storage_devices 
            if s.total_gb > 0
        ) if snapshot.hardware.storage_devices else False
        storage_status = "warning" if storage_warning else "good"
        
        return f'''
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Performance Status</span>
                    <span class="card-icon">📊</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <div class="status-indicator status-{memory_status}">
                        <span>●</span>
                        <span>Memory Usage: {memory.used_gb:.1f} / {memory.total_gb:.1f} GB</span>
                    </div>
                    <div class="status-indicator status-{storage_status}">
                        <span>●</span>
                        <span>Storage Status</span>
                    </div>
                </div>
            </div>'''
    
    def _build_issues_list(self, issues) -> str:
        """Build detailed issues list"""
        if not issues:
            return '<div class="card"><p style="text-align: center; color: var(--success);">✓ No issues detected! System is healthy.</p></div>'
        
        items = []
        for issue in issues:
            severity_class = issue.severity.value.lower()
            badge_class = f"badge-{severity_class}"
            
            items.append(f'''
            <li class="issue-item {severity_class}">
                <div class="issue-title">
                    {issue.title}
                    <span class="issue-badge {badge_class}">{issue.severity.value.upper()}</span>
                </div>
                <div class="issue-description">{issue.description}</div>
                <div class="issue-recommendation">
                    <strong>💡 Recommendation:</strong> {issue.recommendation}
                </div>
            </li>''')
        
        return f'<ul class="issue-list">{ "".join(items) }</ul>'
    
    def _build_detailed_specs(self, snapshot) -> str:
        """Build detailed system specifications"""
        specs = []
        
        # CPU details
        if snapshot.hardware.cpu:
            cpu = snapshot.hardware.cpu
            specs.extend([
                ('CPU Model', cpu.name),
                ('Cores/Threads', f"{cpu.cores}/{cpu.threads}"),
                ('Base Clock', f"{cpu.base_clock_mhz:.0f} MHz"),
            ])
        
        # Memory details
        if snapshot.hardware.memory:
            mem = snapshot.hardware.memory
            specs.extend([
                ('Total Memory', f"{mem.total_gb:.1f} GB"),
                ('Memory Used', f"{mem.used_gb:.1f} GB"),
                ('Memory Type', mem.type if mem.type else 'Unknown'),
            ])
        
        # GPU details
        if snapshot.hardware.gpus:
            for i, gpu in enumerate(snapshot.hardware.gpus):
                prefix = f"GPU {i+1}" if len(snapshot.hardware.gpus) > 1 else "GPU"
                specs.extend([
                    (f'{prefix} Model', gpu.name),
                    (f'{prefix} VRAM', f"{gpu.vram_mb} MB"),
                    (f'{prefix} Driver', gpu.driver_version),
                ])
        
        # Windows info
        if snapshot.windows:
            specs.extend([
                ('Windows Version', snapshot.windows.version),
                ('Windows Build', snapshot.windows.build),
                ('Architecture', snapshot.windows.architecture),
            ])
        
        # Build HTML
        spec_items = ''.join([
            f'<div class="spec-item"><span class="spec-label">{label}</span><span class="spec-value">{value}</span></div>'
            for label, value in specs
        ])
        
        return f'<div class="card"><div class="specs-grid">{spec_items}</div></div>'
    
    def _get_score_color(self, score: int) -> str:
        """Get color based on health score"""
        if score >= 90:
            return self.theme.success_color
        elif score >= 70:
            return self.theme.warning_color
        elif score >= 50:
            return '#f97316'  # Orange
        else:
            return self.theme.error_color
    
    def _build_scripts(self, result) -> str:
        """Build JavaScript for interactivity"""
        return '''
<script>
    // Add smooth scrolling for any anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Add hover effects to issue items
    document.querySelectorAll('.issue-item').forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
        });
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
</script>
</html>'''


__all__ = ['HTMLReportGenerator', 'ReportTheme']