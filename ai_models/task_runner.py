import traceback

from ai_models.train_classifier import train_model
from ai_models.ai_utils import BusyError
from ai_models.eval_classifier import predict
from ai_models.kafka_client import send_task_event
from threading import Lock
from functools import wraps
from typing import Callable

_train_lock = Lock()



def task_handler(
        *,
        task_type:str,
        result_key:str = "result",
        lock: Lock|None,
        blocking: bool = False,
):

    '''
        args:
        task_type:任务类型,如train/predict
        result_key:成功结果放入 payload 时使用的字段名
        lock:需要使用的线程锁
        blocking:
        True  = 锁被占用时等待
        False = 锁被占用时立即拒绝
    '''

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(session_id: str, *args, **kwargs):
            acquired = False

            try:
                if lock is not None:
                    acquired = lock.acquire(blocking=blocking)
                    if not acquired:
                        raise BusyError("training task existing")
                res = func(session_id,*args,**kwargs)

            except BusyError:
                raise

            except Exception as e:
                send_task_event(
                    session_id=session_id,
                    task_type=task_type,
                    status="failed",
                    payload={
                        "error":str(e),
                        "detail":traceback.format_exc()
                        }
                )
                return None

            finally:
                if acquired and lock:
                    lock.release()
            
            send_task_event(
                session_id=session_id,
                task_type=task_type,
                status="success",
                payload= res
            )
            return res
        return wrapper
    return decorator


@task_handler(task_type="predict",result_key="prediction",lock=None)  
def run_predict(session_id: str, event: dict):
    return predict(id=session_id, event=event)

@task_handler(task_type="train",result_key="train_res",lock=_train_lock,blocking=False)   
def run_train(session_id: str,train_file_path : str):
    return train_model(path=train_file_path)