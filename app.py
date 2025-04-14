from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
import os
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes

# Create upload folder if it doesn't exist
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'json_comparison_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

def compare_json(reference, target, path=""):
    """Recursively compare two JSON objects."""
    missing, common, differences = {}, {}, {}

    for key in reference:
        current_path = f"{path}.{key}" if path else key
        if key not in target:
            missing[current_path] = reference[key]
        else:
            ref_val, tgt_val = reference[key], target[key]
            if isinstance(ref_val, dict) and isinstance(tgt_val, dict):
                sub_missing, sub_common, sub_diff = compare_json(ref_val, tgt_val, current_path)
                missing.update(sub_missing)
                common.update(sub_common)
                differences.update(sub_diff)
            elif ref_val == tgt_val:
                common[current_path] = ref_val
            else:
                differences[current_path] = {"reference": ref_val, "target": tgt_val}
    return missing, common, differences

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compare', methods=['POST'])
def compare():
    if 'reference' not in request.files:
        return jsonify({"error": "No reference file provided"}), 400
    
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
                "differences": {}
            })
            continue
        
        # Compare data
        missing, common, differences = compare_json(reference_data, target_data)
        
        results.append({
            "file": target_file.filename,
            "missing": missing,
            "common": common,
            "differences": differences
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