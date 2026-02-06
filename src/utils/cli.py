"""
WinGamingDiag - CLI Interface
Rich terminal interface with progress bars and formatted output
"""

import sys
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass
import os


@dataclass
class ConsoleStyle:
    """Terminal color and style definitions"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Backgrounds
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class ProgressBar:
    """
    Simple progress bar for terminal output
    Compatible with Windows CMD and modern terminals
    """
    
    def __init__(self, total: int, width: int = 50, title: str = ""):
        """
        Initialize progress bar
        
        Args:
            total: Total number of steps
            width: Width of progress bar in characters
            title: Title to display above progress bar
        """
        self.total = total
        self.width = width
        self.title = title
        self.current = 0
        self.start_time = time.time()
        self.is_windows = sys.platform == 'win32'
        
    def update(self, step: int = 1, message: str = ""):
        """Update progress bar"""
        self.current = min(self.current + step, self.total)
        self._draw(message)
        
    def _draw(self, message: str = ""):
        """Draw the progress bar"""
        percent = (self.current / self.total) * 100
        filled = int(self.width * self.current / self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {int(eta)}s"
        else:
            eta_str = "ETA: --"
        
        # Build output
        lines = []
        if self.title and self.current == 0:
            lines.append(f"\n{self.title}")
        
        lines.append(f"[{bar}] {percent:.1f}% {eta_str}")
        if message:
            lines.append(f"  {message}")
        
        output = '\n'.join(lines)
        
        # Clear previous lines and redraw
        if self.current > 0:
            # Move cursor up and clear
            if self.title:
                sys.stdout.write('\033[F' * (2 if self.current == 1 else 1))
            else:
                sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        
        sys.stdout.write(output + '\n')
        sys.stdout.flush()
    
    def finish(self, message: str = "Complete"):
        """Finish progress bar"""
        self.current = self.total
        self._draw(message)
        print()  # New line after completion


class ConsoleUI:
    """
    Rich console interface for WinGamingDiag
    """
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize console UI
        
        Args:
            use_colors: Whether to use ANSI color codes
        """
        self.style = ConsoleStyle()
        self.use_colors = use_colors and sys.platform != 'win32' or self._supports_colors()
        self.current_section = None
        
    def _supports_colors(self) -> bool:
        """Check if terminal supports colors"""
        if sys.platform == 'win32':
            # Windows 10+ supports ANSI colors
            return os.environ.get('TERM') == 'xterm' or 'ANSICON' in os.environ
        return True
    
    def _color(self, text: str, color: str) -> str:
        """Apply color to text if supported"""
        if self.use_colors:
            return f"{color}{text}{self.style.RESET}"
        return text
    
    def header(self, title: str):
        """Display section header"""
        width = 70
        print()
        print(self._color("=" * width, self.style.CYAN))
        print(self._color(f"  {title}", self.style.BOLD + self.style.CYAN))
        print(self._color("=" * width, self.style.CYAN))
        print()
        
    def subheader(self, title: str):
        """Display subsection header"""
        print()
        print(self._color(f"📋 {title}", self.style.BOLD + self.style.WHITE))
        print(self._color("-" * 50, self.style.DIM))
        
    def info(self, message: str, indent: int = 0):
        """Display info message"""
        prefix = "  " * indent
        print(f"{prefix}ℹ️  {message}")
        
    def success(self, message: str, indent: int = 0):
        """Display success message"""
        prefix = "  " * indent
        icon = self._color("✓", self.style.GREEN) if self.use_colors else "✓"
        print(f"{prefix}{icon} {message}")
        
    def warning(self, message: str, indent: int = 0):
        """Display warning message"""
        prefix = "  " * indent
        icon = self._color("⚠️", self.style.YELLOW) if self.use_colors else "⚠️"
        print(f"{prefix}{icon} {message}")
        
    def error(self, message: str, indent: int = 0):
        """Display error message"""
        prefix = "  " * indent
        icon = self._color("✗", self.style.RED) if self.use_colors else "✗"
        print(f"{prefix}{icon} {message}")
        
    def critical(self, message: str, indent: int = 0):
        """Display critical error message"""
        prefix = "  " * indent
        if self.use_colors:
            print(f"{prefix}{self.style.BG_RED}{self.style.WHITE} 🔴 CRITICAL {self.style.RESET} {self._color(message, self.style.RED)}")
        else:
            print(f"{prefix}[CRITICAL] {message}")
    
    def metric(self, label: str, value: str, unit: str = "", indent: int = 0):
        """Display a metric"""
        prefix = "  " * indent
        label_colored = self._color(f"{label}:", self.style.DIM)
        value_colored = self._color(value, self.style.WHITE + self.style.BOLD)
        unit_str = f" {unit}" if unit else ""
        print(f"{prefix}{label_colored} {value_colored}{unit_str}")
        
    def progress_bar(self, total: int, title: str = "") -> ProgressBar:
        """Create and return a progress bar"""
        return ProgressBar(total, title=title)
    
    def show_collection_start(self):
        """Show collection start banner"""
        print()
        print(self._color("🔍 Starting System Diagnostic Collection...", self.style.BOLD))
        print()
        
    def show_collection_complete(self, duration: float, component_count: int):
        """Show collection complete message"""
        print()
        print(self._color(f"✅ Collection Complete!", self.style.GREEN + self.style.BOLD))
        self.metric("Duration", f"{duration:.1f}", "seconds")
        self.metric("Components Collected", str(component_count))
        print()
        
    def show_analysis_start(self, issue_count: int = 0):
        """Show analysis start"""
        if issue_count > 0:
            print(self._color(f"🔍 Analyzing {issue_count} potential issues...", self.style.BOLD))
        else:
            print(self._color("🔍 Analyzing collected data...", self.style.BOLD))
        print()
        
    def show_health_score(self, score: int):
        """Display health score with visual indicator"""
        print()
        
        # Color based on score
        if score >= 90:
            color = self.style.GREEN
            status = "EXCELLENT"
            emoji = "🟢"
        elif score >= 70:
            color = self.style.YELLOW
            status = "GOOD"
            emoji = "🟡"
        elif score >= 50:
            color = self.style.YELLOW
            status = "FAIR"
            emoji = "🟠"
        else:
            color = self.style.RED
            status = "POOR"
            emoji = "🔴"
        
        # Build score bar
        bar_width = 50
        filled = int(bar_width * score / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        print(self._color("┌" + "─" * 48 + "┐", color))
        print(self._color(f"│  SYSTEM HEALTH SCORE: {score:3d}/100                │", self.style.BOLD + color))
        print(self._color(f"│  Status: {emoji} {status:20}               │", color))
        print(self._color(f"│  [{bar}]  │", color))
        print(self._color("└" + "─" * 48 + "┘", color))
        print()
        
    def show_issue_summary(self, critical: int, high: int, medium: int, low: int):
        """Display issue summary"""
        print(self._color("📊 ISSUE SUMMARY:", self.style.BOLD))
        print()
        
        if critical > 0:
            self.error(f"Critical: {critical}", indent=1)
        if high > 0:
            self.warning(f"High: {high}", indent=1)
        if medium > 0:
            self.info(f"Medium: {medium}", indent=1)
        if low > 0:
            self.info(f"Low: {low}", indent=1)
            
        if critical + high + medium + low == 0:
            self.success("No issues detected! System is healthy.", indent=1)
            
        print()
        
    def show_issue_detail(self, title: str, severity: str, category: str, 
                         description: str, recommendation: str, confidence: float):
        """Display detailed issue information"""
        # Severity emoji and color
        severity_emojis = {
            'critical': ('🔴', self.style.RED),
            'high': ('🟠', self.style.YELLOW),
            'medium': ('🟡', self.style.YELLOW),
            'low': ('🟢', self.style.GREEN)
        }
        
        emoji, color = severity_emojis.get(severity.lower(), ('⚪', self.style.WHITE))
        
        print()
        print(self._color(f"{emoji} {title}", self.style.BOLD + color))
        print(self._color(f"   Category: {category.upper()}", self.style.DIM))
        print(self._color(f"   Confidence: {confidence*100:.0f}%", self.style.DIM))
        print()
        print(f"   {description}")
        print()
        print(self._color("   💡 Recommendation:", self.style.CYAN))
        for line in recommendation.split('\n'):
            print(f"      {line}")
        print()
        print(self._color("-" * 70, self.style.DIM))
        
    def show_report_saved(self, filepath: str):
        """Show report saved confirmation"""
        print()
        self.success(f"Report saved to: {filepath}")
        print()
        
    def show_update_available(self, current_version: str, new_version: str):
        """Show update available message"""
        print()
        print(self._color("📦 Update Available!", self.style.YELLOW + self.style.BOLD))
        print(f"   Current version: {current_version}")
        print(self._color(f"   New version: {new_version}", self.style.GREEN))
        print()
        print("   Run with --update to download and install")
        print()
        
    def prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """Prompt user for yes/no input"""
        suffix = " [Y/n]: " if default else " [y/N]: "
        response = input(f"{question}{suffix}").strip().lower()
        
        if not response:
            return default
        return response in ['y', 'yes']
    
    def prompt_choice(self, question: str, choices: List[str], default: int = 0) -> int:
        """Prompt user to choose from options"""
        print(f"\n{question}")
        for i, choice in enumerate(choices):
            marker = ">" if i == default else " "
            print(f"  {marker} {i+1}. {choice}")
        
        try:
            response = input(f"\nSelect option [{default+1}]: ").strip()
            if not response:
                return default
            return int(response) - 1
        except (ValueError, IndexError):
            return default
    
    def clear_screen(self):
        """Clear terminal screen"""
        if sys.platform == 'win32':
            os.system('cls')
        else:
            os.system('clear')
    
    def wait_for_key(self, message: str = "Press Enter to continue..."):
        """Wait for user to press a key"""
        input(f"\n{message}")


class Spinner:
    """Simple spinner for indeterminate progress"""
    
    def __init__(self, message: str = "Working"):
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current = 0
        self.running = False
        
    def start(self):
        """Start spinner display"""
        self.running = True
        import threading
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()
        
    def _spin(self):
        """Spinner animation loop"""
        while self.running:
            char = self.spinner_chars[self.current % len(self.spinner_chars)]
            sys.stdout.write(f"\r{char} {self.message}...")
            sys.stdout.flush()
            self.current += 1
            time.sleep(0.1)
            
    def stop(self, message: str = "Done"):
        """Stop spinner"""
        self.running = False
        self.thread.join()
        sys.stdout.write(f"\r✓ {self.message} - {message}\n")
        sys.stdout.flush()


def create_default_ui() -> ConsoleUI:
    """Create default console UI instance"""
    return ConsoleUI()


__all__ = [
    'ConsoleUI',
    'ProgressBar',
    'Spinner',
    'ConsoleStyle',
    'create_default_ui'
]
