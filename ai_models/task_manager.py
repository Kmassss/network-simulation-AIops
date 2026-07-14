from datetime import datetime
from threading import Lock

_task_store = {}
_lock = Lock()

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def create_task(session_id:str,task_type: str):
    with _lock:
        _task_store[session_id] = {
            "session_id":session_id,
            "task_type": task_type,
            "status": "submitted",
            "created_at": now_str(),
            "updated_at": now_str(),
            "error": None,
        }

def update_task(session_id:str,**kwargs):
    with _lock:
        if session_id not in _task_store:
            _task_store[session_id] = {
                "session_id": session_id,
                "created_at": now_str(),
            }

        _task_store[session_id].update(kwargs)
        _task_store[session_id]["updated_at"] = now_str()

def get_task(session_id:str):
    with _lock:
        return _task_store.get(session_id)


    