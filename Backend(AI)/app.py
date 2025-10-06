import base64
from flask import Flask, request, jsonify
import numpy as np
from io import BytesIO
from PIL import Image
from flask_cors import CORS
import os
import torch
import pandas as pd
import json 
import time 
import atexit 

app = Flask(__name__)

CHAMBER_VOLUME_ML = 0.0001
CORS(app, resources={r"/predict": {"origins": "https://g6weds.consolutechcloud.com"}}) 

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "best.pt")
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
LATEST_DATA_PATH = os.path.join(DATA_DIR, "algae_data.json")
HISTORY_DATA_PATH = os.path.join(DATA_DIR, "analysis_history.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

LATEST_DATA = {}
HISTORY_DATA = []

model = None
try:
    model = torch.hub.load("ultralytics/yolov5", "custom", path=MODEL_PATH, source="github") 
    print("INFO: YOLOv5 model loaded successfully.")
except Exception as e:
    print(f"FATAL ERROR: Failed to load YOLO model: {e}")
    model = None

def load_json_data(filepath, default_value):
    """Loads JSON data from a file, returns default_value if file doesn't exist or is invalid."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return default_value
                return json.loads(content)
        return default_value
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
        return [] if filepath == HISTORY_DATA_PATH else default_value 
    except Exception as e:
        print(f"Error loading data from {filepath}: {e}")
        return default_value

def save_json_data(filepath, data):
    """Attempts to save data to a JSON file (ใช้สำหรับบันทึกสุดท้ายเท่านั้น)."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4) 
        print(f"INFO: Data successfully saved to {filepath} on shutdown.")
        return True
    except Exception as e:
        print(f"WARNING: Could not save data to {filepath}. Permission Denied? Error: {e}")
        return False

LATEST_DATA = load_json_data(LATEST_DATA_PATH, {})
HISTORY_DATA = load_json_data(HISTORY_DATA_PATH, [])

def save_on_exit():
    print("INFO: Attempting to save current in-memory data to files...")
    save_json_data(LATEST_DATA_PATH, LATEST_DATA)
    save_json_data(HISTORY_DATA_PATH, HISTORY_DATA)

atexit.register(save_on_exit)

@app.route('/data/algae_data.json', methods=['GET'])
def get_latest_data():
    return jsonify(LATEST_DATA)

@app.route('/data/analysis_history.json', methods=['GET'])
def get_history_data():
    return jsonify(HISTORY_DATA)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API is running"}), 200

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    global LATEST_DATA
    global HISTORY_DATA

    data = request.get_json()

    if not data or "image_base64" not in data:
        return jsonify({"error": "Missing image_base64 in request body"}), 400

    if model is None:
        return jsonify({"error": "Model not initialized on server."}), 500

    try:
        
        # 1. แปลง Base64 -> Image (PIL Object)
        base64_parts = data["image_base64"].split(",")
        image_data = base64_parts[-1]
        image_bytes = base64.b64decode(image_data)
        img = Image.open(BytesIO(image_bytes)).convert('RGB')
        
        # 2. รันการทำนายด้วย YOLOv5
        results = model(img, size=640) 
        detections = results.pandas().xyxy[0] 
        cell_count = len(detections) 

        if CHAMBER_VOLUME_ML > 0:
            density_cells_ml = round(cell_count / CHAMBER_VOLUME_ML)
        else:
            density_cells_ml = 0

        detected_boxes = []
        for index, row in detections.iterrows():
            coords = [row['xmin'], row['ymin'], row['xmax'], row['ymax']]
            detected_boxes.append({"bbox": [round(c, 2) for c in coords], "confidence": round(row['confidence'], 4)})

        # 3. สร้างภาพผลลัพธ์ที่มีกรอบ (Annotated Image)
        results.render()
        annotated_img = Image.fromarray(results.ims[0])

        buffered = BytesIO()
        annotated_img.save(buffered, format="PNG") 
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        annotated_base64 = "data:image/png;base64," + img_str
        
        prediction_result = {
            "image_base64": annotated_base64, 
            "detected": detected_boxes, 
            "total_cells": cell_count, 
            "density_cells_ml": density_cells_ml, 
            "accuracy_model": "89.2"
        }


        current_time_str = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        file_name = f"analysis_{int(time.time())}.png" 
        

        new_id = (HISTORY_DATA[-1]['id'] + 1) if HISTORY_DATA and isinstance(HISTORY_DATA, list) and 'id' in HISTORY_DATA[-1] else 1
        
        new_history_entry = {
            "id": new_id,
            "date": current_time_str,
            "file": file_name,
            "total_cells": cell_count,
            "density_cells_ml": density_cells_ml
        }
        HISTORY_DATA.append(new_history_entry) 

        LATEST_DATA = { 
            "total_cells": cell_count,
            "density_cells_ml": density_cells_ml,
            "accuracy_model": prediction_result["accuracy_model"],
            "last_updated": current_time_str,
            "last_image_base64": annotated_base64 
        }
        
        # 4. ส่งผลลัพธ์กลับ
        return jsonify(prediction_result)

    except Exception as e:
        print(f"An unexpected error occurred during prediction: {e}")
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4500, debug=True)
