# WinGamingDiag - Windows Gaming Diagnostic Agent

A comprehensive, portable diagnostic tool for Windows gaming systems. Analyzes hardware, software, and configuration to detect issues affecting gaming performance and stability.

## Features

### Comprehensive Diagnostics
- **Hardware Analysis**: CPU, GPU, RAM, storage, motherboard, cooling, power
- **Software Detection**: Windows version, drivers, services, startup programs
- **Performance Monitoring**: Memory usage, disk space, thermal status
- **Gaming-Specific Checks**: Graphics APIs, game launchers, overlays, anti-cheat

### Phase 2 - Advanced Diagnostics
- **Event Log Analysis**: Detect application crashes, system errors, and gaming-related events
- **Driver Compatibility**: Check GPU, audio, and system drivers against latest versions
- **Game Launcher Detection**: Identify Steam, Epic Games, Xbox, and other launchers
- **Network Diagnostics**: Test latency, check connectivity, identify network issues
- **Storage Analysis**: Game library size detection and storage optimization recommendations

### Key Capabilities
- **Read-Only Operation**: Never modifies system state
- **Portable**: Single executable, no installation required
- **Privacy-First**: All processing local, secrets automatically redacted
- **Rich Output**: Progress bars, colored terminal output, detailed reports
- **Evidence-Based**: Every diagnosis includes supporting evidence

## Installation

### Option 1: Download Pre-built Executable
Download `WinGamingDiag.exe` from the releases page and run directly.

### Option 2: Run from Source
```bash
# Clone repository
git clone https://github.com/yourusername/WinGamingDiag.git
cd WinGamingDiag

# Install dependencies
pip install -r requirements.txt

# Run
python -m WinGamingDiag
```

## Usage

### Basic Usage
```bash
# Run full diagnostic
WinGamingDiag.exe

# Quick diagnostic (hardware only)
WinGamingDiag.exe --quick

# Save report to specific location
WinGamingDiag.exe --output C:\Reports\diagnostic.txt

# Verbose output
WinGamingDiag.exe --verbose

# Disable colors
WinGamingDiag.exe --no-color
```

### Output
Reports are automatically saved to the Desktop with timestamp:
- `WinGamingDiag_Report_YYYYMMDD_HHMMSS.txt`

## Architecture

```
WinGamingDiag/
├── src/
│   ├── core/
│   │   └── agent.py          # Main orchestrator
│   ├── collectors/
│   │   ├── hardware.py       # Hardware detection
│   │   ├── event_logs.py     # Event log analysis (Phase 2)
│   │   ├── drivers.py        # Driver compatibility (Phase 2)
│   │   ├── launchers.py      # Game launcher detection (Phase 2)
│   │   └── network.py        # Network diagnostics (Phase 2)
│   ├── models/
│   │   └── __init__.py       # Data models
│   └── utils/
│       ├── wmi_helper.py     # WMI interface
│       ├── redaction.py      # Privacy protection
│       └── cli.py            # Terminal UI
├── __main__.py               # Entry point
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Detected Issues

The tool detects issues across multiple categories:

### Hardware
- Thermal throttling
- Insufficient VRAM
- Storage bottlenecks (HDD vs SSD)
- Memory pressure

### Performance
- High memory usage
- Low disk space
- Background process interference

### Gaming
- Outdated GPU drivers
- Missing redistributables
- Overlay conflicts
- Anti-cheat issues

### Phase 2 - Advanced Detection
- **Event Log Analysis**: Application crashes, system hangs, BSOD patterns
- **Driver Issues**: Outdated drivers, unsigned drivers, missing GPU updates
- **Launcher Conflicts**: Multiple overlays enabled, auto-start bloat
- **Network Problems**: High latency, WiFi vs Ethernet, DNS issues
- **Storage**: Large game libraries, insufficient space for updates

### Configuration
- Suboptimal power settings
- Windows Game Mode status
- Hardware-accelerated GPU scheduling

## Development

### Prerequisites
- Python 3.10+
- Windows 10/11 (for full functionality)
- WMI service enabled

### Build Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --onefile --name WinGamingDiag __main__.py

# Output in dist/WinGamingDiag.exe
```

### Testing
```bash
# Run tests
pytest tests/
```

## Privacy & Security

- **Local Processing**: All data stays on your machine
- **Secret Redaction**: Passwords, API keys, serial numbers automatically hidden
- **No Telemetry**: No data sent to external servers
- **Open Source**: Full source code available for audit

## Supported Hardware

### CPUs
- Intel Core series (with VT-x support detection)
- AMD Ryzen series (with AMD-V support detection)
- All major architectures (x86, x64)

### GPUs
- NVIDIA GeForce (with DLSS, ray tracing detection)
- AMD Radeon (with FSR detection)
- Intel Arc (with XeSS detection)

### Memory
- DDR4, DDR5
- XMP/DOCP profile detection
- Multi-channel configuration

### Storage
- NVMe SSDs
- SATA SSDs/HDDs
- USB external drives

## Limitations

- Windows only (WMI dependency)
- Some features require administrator privileges
- Water cooling detection requires compatible hardware
- PSU information is estimated, not directly readable

## Roadmap

### Phase 1 (Complete)
- [x] Core hardware detection
- [x] Basic issue analysis
- [x] Text report generation
- [x] Privacy protection

### Phase 2 (Current)
- [x] Event log analysis - Detect crashes and gaming-related errors
- [x] Driver compatibility checking - Version comparison and update recommendations
- [x] Game launcher detection - Steam, Epic, Xbox, and others
- [x] Network diagnostics - Latency tests and connectivity analysis
- [x] Enhanced issue detection across all categories

### Phase 3 (Planned)
- [ ] HTML report generation
- [ ] Historical tracking
- [ ] Update checker integration
- [ ] Custom rule definitions
- [ ] Performance benchmarking
- [ ] Temperature monitoring

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- WMI library for Windows integration
- PyInstaller for executable generation
- Gaming community for issue patterns and feedback

## Support

For issues, questions, or feature requests:
- GitHub Issues: [github.com/yourusername/WinGamingDiag/issues](https://github.com/yourusername/WinGamingDiag/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/WinGamingDiag/discussions)

---

**Disclaimer**: This tool is for diagnostic purposes only. Always backup your system before making changes based on recommendations.
