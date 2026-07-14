import os,json
from datetime import datetime
import logging

from confluent_kafka import Producer

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

logging.basicConfig( #日志定义
    filename=now_str(),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
    encoding="utf-8")

task_topic_dict = {
    "train":"TASK_TRAIN_TOPIC",
    "predict":"TASK_PREDICT_TOPIC",
}

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092"
)

producer = Producer(
    {"bootstrap.servers":KAFKA_BOOTSTRAP_SERVERS}
)

def callback(err,msg):
    if err is not None:
        logging.error("sending failed: %s",err)
    else:
        logging.info("success: topic= %s",msg.topic())
        logging.info("partition= %s, ",msg.partition())
        logging.info("offset= %s",msg.offset())

def send_task_event(session_id: str, task_type: str, status: str,payload: dict|None):
    if task_type not in task_topic_dict.keys():
        raise ValueError("task_type's input is illegal")
    
    message = {

        "session_id": session_id,
        "task_type": task_type,
        "status": status,
        "payload": payload or {},
        "timestamp": now_str(),
    }

    producer.produce(
        task_topic_dict[task_type],
        key=session_id,
        value=json.dumps(message, ensure_ascii=False).encode("utf-8"),
        callback=callback
    )

    producer.poll(0.5)#调用callback
    producer.flush()#确认写入topic
    
    return task_topic_dict[task_type]

