"""
WinGamingDiag - Windows Gaming Diagnostic Agent
Main entry point
"""

import sys
import argparse
from pathlib import Path

# Handle frozen (PyInstaller) vs normal execution
if getattr(sys, 'frozen', False):
    # When frozen, the executable's directory is the root for bundled files.
    # We add this directory to the path.
    base_path = Path(sys.executable).parent
    sys.path.insert(0, str(base_path))
else:
    # When running as a script, the project root (parent of 'src') needs to be on the path.
    # This file (__main__.py) is in the project root.
    base_path = Path(__file__).parent
    sys.path.insert(0, str(base_path))

try:
    from src.core.agent import DiagnosticAgent
    from src.utils.cli import create_default_ui
except ImportError as e:
    print(f"Fatal Error: Could not import required modules. {e}")
    print(f"\nDebugging Info:")
    print(f"  - Python Executable: {sys.executable}")
    print(f"  - System Path: {sys.path}")
    print(f"  - Base Path Calculated: {base_path}")
    input("\nPress Enter to exit.")
    sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="WinGamingDiag - Comprehensive Windows Gaming Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  WinGamingDiag.exe              Run full diagnostic
  WinGamingDiag.exe --quick      Run quick diagnostic (hardware only)
  WinGamingDiag.exe --output C:\\Reports\\my_report.txt  Save to specific location
  WinGamingDiag.exe --verbose    Show detailed output
        """
    )
    
    parser.add_argument(
        '--quick', 
        action='store_true',
        help='Run quick diagnostic (hardware only)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output path for report (default: Desktop)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Check if running on Windows
    if sys.platform != 'win32':
        print("WARNING: This tool is designed for Windows.")
        print("Some features may not work on your operating system.")
        print()
    
    # Create UI
    ui = create_default_ui()
    if args.no_color:
        ui.use_colors = False
    
    try:
        # Run diagnostic
        agent = DiagnosticAgent(ui=ui, verbose=args.verbose)
        result = agent.run_full_diagnostic()
        
        # Save report
        report_path = agent.save_report(result, args.output)
        ui.show_report_saved(report_path)
        
        # Exit with appropriate code
        if result.critical_count > 0:
            sys.exit(2)  # Critical issues found
        elif result.high_count > 0:
            sys.exit(1)  # High severity issues found
        else:
            sys.exit(0)  # Success
            
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
