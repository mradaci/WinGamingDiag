"""
WinGamingDiag - Windows Gaming Diagnostic Agent
A comprehensive diagnostic tool for Windows gaming systems
"""

__version__ = "1.0.0"
__author__ = "WinGamingDiag Team"
__description__ = "Comprehensive Windows Gaming System Diagnostic Tool"

from .src.core.agent import DiagnosticAgent
from .src.models import DiagnosticResult, SystemSnapshot

__all__ = ['DiagnosticAgent', 'DiagnosticResult', 'SystemSnapshot']
