# Technology Stack

## Core Technologies

- **Language**: Python 3.8+ (pure Python implementation)
- **Testing Framework**: pytest with hypothesis for property-based testing
- **Dashboard**: Streamlit for web interface

## Python Dependencies

The project uses standard Python packages:

- **pytest**: Testing framework
- **hypothesis**: Property-based testing
- **streamlit**: Web dashboard framework
- **pandas**: Data manipulation
- **numpy**: Numerical operations
- **plotly**: Interactive visualizations
- **pydeck**: Map visualizations
- **reportlab**: PDF generation
- **requests**: HTTP client

## Common Commands

### Installing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or use setup script
python setup.py
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run property-based tests with more iterations
python -m pytest tests/ -v --hypothesis-profile=thorough

# Run specific test file
python -m pytest tests/test_solver.py -v
```

### Running the Dashboard

```bash
# From project root
cd dashboard
streamlit run app.py

# Or use quick launcher
python run_dashboard.bat  # Windows
./run_dashboard.sh        # Linux/macOS
```

### Verification

```bash
# Verify installation
python test_installation.py
```

## Platform Notes

### All Platforms

- Pure Python implementation works on any platform with Python 3.8+
- No compilation required
- No platform-specific dependencies
- No C++ runtime requirements

### Windows

- No Visual C++ Redistributable needed
- No MinGW or compiler required
- Works with standard Python installation

### Linux/macOS

- Works with standard Python 3.8+ installation
- No additional system packages required

