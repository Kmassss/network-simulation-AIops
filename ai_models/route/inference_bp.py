from flask import Blueprint, request, session, jsonify
from ai_models.task_runner import run_predict
from ai_models.task_manager import create_task
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import uuid

threadPool = ThreadPoolExecutor(max_workers=6)
train_lock = Lock()

inference_bp = Blueprint("inference_bp",__name__)

@inference_bp.route("/train", methods=["POST","GET"])
def train():
    session_id = str(uuid.uuid4())
    create_task(
        session_id=session_id,
        task_type="predict"
    )

    return {"ok":"ok"}

@inference_bp.route("/predict", methods=["POST"])
def predict():
    session_id = str(uuid.uuid4())
    create_task(
        session_id=session_id,
        task_type="predict"
    )

    return {"ok":"ok"}