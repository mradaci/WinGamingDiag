"""
WinGamingDiag - Windows Gaming Diagnostic Agent
Main entry point
"""

import sys
import argparse
from pathlib import Path
import logging
import traceback

# --- Setup Logging ---
# Set up logging to a file before anything else can fail.
log_file = Path("WinGamingDiag_debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=str(log_file),
    filemode='w'
)
# Redirect stdout and stderr to the logger
class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

sys.stdout = StreamToLogger(logging.getLogger('STDOUT'), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.ERROR)

logging.info("--- WinGamingDiag Starting ---")
logging.info(f"Python version: {sys.version}")
logging.info(f"Platform: {sys.platform}")

# --- Pathing ---
try:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
        sys.path.insert(0, str(base_path))
        logging.info(f"Running FROZEN, MEIPASS: {base_path}")
    else:
        base_path = Path(__file__).parent
        sys.path.insert(0, str(base_path))
        logging.info(f"Running as script, base path: {base_path}")
except Exception as e:
    logging.critical(f"Path setup failed: {e}", exc_info=True)
    sys.exit(1)

# --- Main Application ---
try:
    from src.core.agent import DiagnosticAgent
    from src.utils.cli import create_default_ui
    logging.info("Core modules imported successfully.")
except ImportError as e:
    logging.critical(f"Fatal Error: Could not import required modules. {e}", exc_info=True)
    logging.critical(f"  - Python Executable: {sys.executable}")
    logging.critical(f"  - System Path: {sys.path}")
    sys.exit(1)

def main():
    """Main entry point"""
    try:
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
            help='Run quick diagnostic (hardware only)',
            default=False
        )
        
        parser.add_argument(
            '--output', '-o',
            type=str,
            help='Output path for report (default: Desktop)',
            default=None
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output',
            default=False
        )
        
        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output',
            default=False
        )
        
        parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s 1.0.0'
        )
        
        args = parser.parse_args()
        logging.info(f"Arguments parsed: {args}")

        if sys.platform != 'win32':
            logging.warning("This tool is designed for Windows.")
        
        ui = create_default_ui()
        if args.no_color:
            ui.use_colors = False
        
        logging.info("Starting diagnostic agent...")
        agent = DiagnosticAgent(ui=ui, verbose=args.verbose)
        result = agent.run_full_diagnostic()
        logging.info("Diagnostic run completed.")
        
        report_path = agent.save_report(result, args.output)
        ui.show_report_saved(report_path)
        logging.info(f"Report saved to {report_path}")
        
        # ... (rest of the exit logic)

    except Exception as e:
        logging.critical(f"An unexpected error occurred in main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logging.info("--- WinGamingDiag Finished ---")
        import os
        if getattr(sys, 'frozen', False) and not os.environ.get('CI'):
            print("\nDiagnostics finished. A debug log has been created: WinGamingDiag_debug.log")
            input("Press Enter to exit.")

if __name__ == '__main__':
    main()
