from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
import os
import tempfile
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError
from typing import Dict, Any, List, Union, Optional

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes

# Create upload folder if it doesn't exist
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'json_comparison_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class ComparisonConfig:
    def __init__(self, 
                 ignore_order: bool = False,
                 case_insensitive: bool = False,
                 numeric_tolerance: float = 0.0,
                 ignore_keys: List[str] = None,
                 custom_rules: Dict[str, Any] = None,
                 schema: Dict[str, Any] = None):
        self.ignore_order = ignore_order
        self.case_insensitive = case_insensitive
        self.numeric_tolerance = numeric_tolerance
        self.ignore_keys = ignore_keys or []
        self.custom_rules = custom_rules or {}
        self.schema = schema

def load_json(file_path):
    """Load JSON data from a file with error handling and encoding support."""
    # Try UTF-8 first (most common for JSON)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file), None
    except UnicodeDecodeError:
        # If UTF-8 fails, try with Latin-1 (which can handle any byte value)
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return json.load(file), None
        except Exception as e:
            return None, f"Failed to decode file with multiple encodings: {str(e)}"
    except FileNotFoundError:
        return None, f"File not found: {file_path}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in file {file_path}: {e}"
    except Exception as e:
        return None, f"Error reading file {file_path}: {str(e)}"

def compare_values(val1: Any, val2: Any, config: ComparisonConfig) -> bool:
    """Compare two values with respect to the comparison configuration."""
    if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
        return abs(val1 - val2) <= config.numeric_tolerance
    
    if config.case_insensitive and isinstance(val1, str) and isinstance(val2, str):
        return val1.lower() == val2.lower()
    
    return val1 == val2

def compare_arrays(arr1: List[Any], arr2: List[Any], config: ComparisonConfig) -> bool:
    """Compare arrays with optional order ignoring."""
    if len(arr1) != len(arr2):
        return False
    
    if not config.ignore_order:
        return all(compare_values(a, b, config) for a, b in zip(arr1, arr2))
    
    # For order-ignoring comparison, we need to check if all elements in arr1 exist in arr2
    arr2_copy = arr2.copy()
    for item1 in arr1:
        found = False
        for i, item2 in enumerate(arr2_copy):
            if compare_values(item1, item2, config):
                arr2_copy.pop(i)
                found = True
                break
        if not found:
            return False
    return True

def compare_json(reference: Dict[str, Any], target: Dict[str, Any], 
                config: ComparisonConfig, path: str = "") -> tuple:
    """Recursively compare two JSON objects with enhanced comparison options."""
    missing, common, differences, additional = {}, {}, {}, {}

    # Validate against schema if provided
    if config.schema and path == "":
        try:
            validate(instance=reference, schema=config.schema)
            validate(instance=target, schema=config.schema)
        except ValidationError as e:
            return {}, {}, {}, {"schema_error": str(e)}

    # Track keys present in target but not in reference
    for key in target:
        if key not in reference and key not in config.ignore_keys:
            current_path = f"{path}.{key}" if path else key
            additional[current_path] = target[key]

    for key in reference:
        if key in config.ignore_keys:
            continue

        current_path = f"{path}.{key}" if path else key
        
        # Apply custom rules if defined
        if current_path in config.custom_rules:
            rule = config.custom_rules[current_path]
            if rule == "ignore":
                continue
            elif callable(rule):
                if not rule(reference[key], target.get(key)):
                    differences[current_path] = {
                        "reference": reference[key],
                        "target": target.get(key)
                    }
                continue

        if key not in target:
            missing[current_path] = reference[key]
        else:
            ref_val, tgt_val = reference[key], target[key]
            
            if isinstance(ref_val, dict) and isinstance(tgt_val, dict):
                sub_missing, sub_common, sub_diff, sub_add = compare_json(ref_val, tgt_val, config, current_path)
                missing.update(sub_missing)
                common.update(sub_common)
                differences.update(sub_diff)
                additional.update(sub_add)
            elif isinstance(ref_val, list) and isinstance(tgt_val, list):
                if compare_arrays(ref_val, tgt_val, config):
                    common[current_path] = ref_val
                else:
                    differences[current_path] = {"reference": ref_val, "target": tgt_val}
            elif compare_values(ref_val, tgt_val, config):
                common[current_path] = ref_val
            else:
                differences[current_path] = {"reference": ref_val, "target": tgt_val}
    
    return missing, common, differences, additional

def calculate_accuracy(missing: Dict, common: Dict, differences: Dict, additional: Dict) -> Dict[str, float]:
    """Calculate various accuracy metrics."""
    total_keys = len(missing) + len(common) + len(differences) + len(additional)
    if total_keys == 0:
        return {
            "overall_accuracy": 0.0,
            "key_presence_accuracy": 0.0,
            "value_accuracy": 0.0
        }
    
    # Calculate key presence accuracy (ignoring values)
    total_present_keys = len(common) + len(differences)
    key_presence_accuracy = (total_present_keys / (total_present_keys + len(missing))) * 100 if (total_present_keys + len(missing)) > 0 else 0
    
    # Calculate value accuracy (only for keys that are present)
    value_accuracy = (len(common) / (len(common) + len(differences))) * 100 if (len(common) + len(differences)) > 0 else 0
    
    # Calculate overall accuracy
    overall_accuracy = (len(common) / total_keys) * 100
    
    return {
        "overall_accuracy": round(overall_accuracy, 2),
        "key_presence_accuracy": round(key_presence_accuracy, 2),
        "value_accuracy": round(value_accuracy, 2)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compare', methods=['POST'])
def compare():
    if 'reference' not in request.files:
        return jsonify({"error": "No reference file provided"}), 400
    
    # Get comparison configuration from request
    config = ComparisonConfig(
        ignore_order=request.form.get('ignore_order', 'false').lower() == 'true',
        case_insensitive=request.form.get('case_insensitive', 'false').lower() == 'true',
        numeric_tolerance=float(request.form.get('numeric_tolerance', '0.0')),
        ignore_keys=request.form.get('ignore_keys', '').split(',') if request.form.get('ignore_keys') else [],
        custom_rules=json.loads(request.form.get('custom_rules', '{}')),
        schema=json.loads(request.form.get('schema', '{}')) if request.form.get('schema') else None
    )
    
    reference_file = request.files['reference']
    if reference_file.filename == '':
        return jsonify({"error": "No reference file selected"}), 400

    # Save reference file
    reference_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(reference_file.filename))
    reference_file.save(reference_path)
    
    # Load reference data
    reference_data, error = load_json(reference_path)
    if error:
        return jsonify({"error": error}), 400
    
    results = []
    
    # Process each target file
    target_files = request.files.getlist('targets')
    
    if not target_files or all(file.filename == '' for file in target_files):
        return jsonify({"error": "No target files provided"}), 400
    
    for target_file in target_files:
        if target_file.filename == '':
            continue
            
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(target_file.filename))
        target_file.save(target_path)
        
        # Load target data
        target_data, error = load_json(target_path)
        
        if error:
            results.append({
                "file": target_file.filename,
                "error": error,
                "missing": {},
                "common": {},
                "differences": {},
                "additional": {},
                "accuracy": {
                    "overall_accuracy": 0.0,
                    "key_presence_accuracy": 0.0,
                    "value_accuracy": 0.0
                }
            })
            continue
        
        # Compare data
        missing, common, differences, additional = compare_json(reference_data, target_data, config)
        
        # Calculate accuracy metrics
        accuracy = calculate_accuracy(missing, common, differences, additional)
        
        results.append({
            "file": target_file.filename,
            "missing": missing,
            "common": common,
            "differences": differences,
            "additional": additional,
            "accuracy": accuracy
        })
        
        # Clean up temp files
        try:
            os.remove(target_path)
        except:
            pass
    
    # Clean up reference file
    try:
        os.remove(reference_path)
    except:
        pass
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)