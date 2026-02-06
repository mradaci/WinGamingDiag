"""
Standalone collector script for running in a separate process.
This isolates potentially crashing WMI calls from the main application.
"""
import sys
import json
import logging
from pathlib import Path

def run_collector():
    # Set up basic logging for this script
    log_file = Path("collector_debug.log")
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename=str(log_file), filemode='w')
    
    # Add src to path
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
        sys.path.insert(0, str(base_path))
    else:
        # This path is relative to where the main script is, needs adjustment
        base_path = Path(__file__).parent.parent
        sys.path.insert(0, str(base_path))

    try:
        from src.collectors.hardware import HardwareCollector
        
        logging.info("Standalone Collector: Starting hardware collection.")
        collector = HardwareCollector()
        hardware_snapshot = collector.collect_all()
        
        # Serialize the snapshot to a dictionary
        # This is a simplified serialization; a real implementation would be more robust
        output_data = {
            'cpu': hardware_snapshot.cpu.__dict__ if hardware_snapshot.cpu else None,
            'memory': hardware_snapshot.memory.__dict__ if hardware_snapshot.memory else None,
            'gpus': [gpu.__dict__ for gpu in hardware_snapshot.gpus],
            'storage_devices': [storage.__dict__ for storage in hardware_snapshot.storage_devices],
            'motherboard': hardware_snapshot.motherboard.__dict__ if hardware_snapshot.motherboard else None,
            'cooling': hardware_snapshot.cooling.__dict__ if hardware_snapshot.cooling else None,
            'power': hardware_snapshot.power.__dict__ if hardware_snapshot.power else None,
            'errors': collector.get_errors(),
        }

        # The output file path is passed as a command-line argument
        output_file_path = sys.argv[1]
        with open(output_file_path, 'w') as f:
            json.dump(output_data, f)
            
        logging.info(f"Standalone Collector: Hardware data saved to {output_file_path}")
        sys.exit(0)

    except Exception as e:
        logging.critical("Standalone Collector: A fatal error occurred.", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_collector()
