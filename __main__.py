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
log_file = Path("WinGamingDiag_debug.log")
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    filename=str(log_file), 
    filemode='w'
)

class StreamToLogger:
    """Redirects stream output to logger while preserving original stream"""
    def __init__(self, stream, logger, level):
        self.stream = stream
        self.logger = logger
        self.level = level
    def write(self, buf):
        # Write to original stream (console)
        self.stream.write(buf)
        self.stream.flush()
        # Also log it
        for line in buf.rstrip().splitlines():
            if line.strip():  # Only log non-empty lines
                self.logger.log(self.level, line.rstrip())
    def flush(self):
        self.stream.flush()

# Keep original stderr for console output, but also log errors
original_stderr = sys.stderr
sys.stderr = StreamToLogger(original_stderr, logging.getLogger('STDERR'), logging.ERROR)

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
    print(f"CRITICAL ERROR: Path setup failed: {e}", file=original_stderr)
    sys.exit(1)

# --- Main Application ---
try:
    from src.core.agent import DiagnosticAgent
    from src.utils.cli import create_default_ui
    logging.info("Core modules imported successfully.")
except ImportError as e:
    logging.critical(f"Fatal Error: Could not import required modules. {e}", exc_info=True)
    print(f"CRITICAL ERROR: Could not import required modules: {e}", file=original_stderr)
    sys.exit(1)

def main():
    """Main entry point"""
    exit_code = 0
    try:
        parser = argparse.ArgumentParser(description="WinGamingDiag - Comprehensive Windows Gaming Diagnostic Tool")
        parser.add_argument('--quick', action='store_true', help='Run quick diagnostic', default=False)
        parser.add_argument('--output', '-o', type=str, help='Output path for report', default=None)
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output', default=False)
        parser.add_argument('--no-color', action='store_true', help='Disable colored output', default=False)
        parser.add_argument('--version', action='version', version='%(prog)s 6.0.2')
        
        args = parser.parse_args()
        logging.info(f"Arguments parsed: {args}")

        if sys.platform != 'win32':
            logging.warning("This tool is designed for Windows.")
            print("WARNING: This tool is designed for Windows. Some features may not work correctly.")
        
        ui = create_default_ui()
        if args.no_color:
            ui.use_colors = False
        
        print("\nStarting diagnostic...", flush=True)
        agent = DiagnosticAgent(ui=ui, verbose=args.verbose, quick_mode=args.quick)
        result = agent.run_full_diagnostic()
        
        print("\nSaving report...", flush=True)
        report_path = agent.save_report(result, args.output)
        if report_path:
            ui.show_report_saved(report_path)
            print(f"\nReport saved to: {report_path}", flush=True)
        else:
            print("\nWARNING: Report could not be saved.", flush=True)
        
        logging.info("Graceful finish.")
        print("\nDiagnostic completed successfully!", flush=True)
    
    except KeyboardInterrupt:
        logging.warning("Diagnostic interrupted by user.")
        print("\nDiagnostic interrupted by user.", flush=True)
        exit_code = 130
    except Exception as e:
        logging.critical("An unexpected error occurred in main:", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}", flush=True)
        print(f"Check debug log for details: {log_file.absolute()}", flush=True)
        traceback.print_exc()
        exit_code = 1
    finally:
        logging.info("--- WinGamingDiag Finished ---")
        # Only pause if running as frozen executable and not in CI
        if getattr(sys, 'frozen', False) and not os.environ.get('CI'):
            if exit_code != 0:
                print(f"\nExited with error code {exit_code}", flush=True)
            print("\nPress Enter to exit...", flush=True)
            try:
                input()
            except:
                pass
    
    return exit_code

if __name__ == '__main__':
    import os
    sys.exit(main())
