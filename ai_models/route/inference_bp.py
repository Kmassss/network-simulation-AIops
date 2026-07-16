from flask import Blueprint, request, session, jsonify
from ai_models.task_runner import run_predict,run_train
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import uuid

threadPool = ThreadPoolExecutor(max_workers=6)
train_lock = Lock()

inference_bp = Blueprint("inference_bp",__name__)

@inference_bp.route("/train", methods=["POST"])
def train():
    data = request.get_json(silent=True) or {}
    train_file_path = data.get("train_file")
    
    if not train_file_path:
        return jsonify(
            {
                "error":"lack training file"
            }
        ),400
    
    session_id = str(uuid.uuid4())
    try:
        threadPool.submit(
            run_train,
            session_id,
            train_file_path,
        )
    except Exception as e :
        return jsonify(
            {
            "session_id": session_id,
            "status": "submit_failed",
            "error": str(e),  
            }
        ), 500
    
    return jsonify(
        {
            "session_id": session_id,
            "status": "submited",
            "task_type": "train",
        }
    ), 202



@inference_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    event = data.get("event")
    
    if not event:
        return jsonify(
            {
                "error":"lack training file"
            }
        ),400
    
    session_id = str(uuid.uuid4())

    try:
        threadPool.submit(
            run_predict,
            session_id,
            event,
        )
    except Exception as e :
        return jsonify(
            {
            "session_id": session_id,
            "status": "submit_failed",
            "error": str(e),  
            }
        ), 500
    
    return jsonify(
        {
            "session_id": session_id,
            "status": "submited",
            "task_type": "train",
        }
    ), 202
