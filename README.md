# JSON Comparison Tool

A powerful web-based tool for comparing JSON files with advanced comparison options and a modern, user-friendly interface.

![JSON Comparison Tool](screenshot.png)

## Features

### Core Comparison Features
- Compare multiple JSON files against a reference file
- Detailed comparison results showing:
  - Missing keys
  - Common keys
  - Different values
  - Additional keys
- Accuracy metrics including:
  - Overall accuracy
  - Key presence accuracy
  - Value accuracy

### Advanced Comparison Options
- **Compare Keys Only**: Check only for the presence of keys, ignoring their values
- **Ignore Array Order**: Compare arrays regardless of element order
- **Case Insensitive**: Compare strings ignoring case differences
- **Numeric Tolerance**: Set maximum allowed difference between numbers
- **Ignore Keys**: Specify keys to ignore during comparison
- **Custom Rules**: Define custom comparison rules for specific paths
- **JSON Schema Validation**: Validate files against a JSON schema

### User Interface Features
- **Dark Mode**: Toggle between light and dark themes
- **Collapsible Settings**: Expandable/collapsible comparison settings section
- **Keyboard Shortcuts**: Quick access to common actions
- **Search Functionality**: Search through comparison results
- **Bookmarking**: Save comparison settings and file selections
- **Export Results**: Download comparison results as JSON

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nafismahmud181/json_comparison_tool.git
cd json_comparison_tool
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Upload your JSON files:
   - Select a reference JSON file
   - Select one or more target JSON files to compare against
   - Configure comparison settings as needed
   - Click "Compare Files" to start the comparison

## Keyboard Shortcuts

- `Ctrl + D`: Toggle dark mode
- `Ctrl + S`: Toggle settings panel
- `Ctrl + K`: Show/hide keyboard shortcuts
- `Ctrl + B`: Toggle bookmark

## Requirements

- Python 3.7+
- Flask
- Flask-CORS
- jsonschema

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Flask
- Uses jsonschema for JSON validation
- Inspired by the need for a flexible JSON comparison tool