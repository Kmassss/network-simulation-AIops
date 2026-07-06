import torch
from torch import Tensor
from ai_utils import (
    FEATURE_NAMES, 
    LABEL_MAP, 
    load_model, 
    load_labeled_samples, 
    features_adjustment
)

ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}
model_save_path = "data/models/traffic_checkpoint.pt"
eval_data_path = "data/samples/test.jsonl"


input_dim = len(FEATURE_NAMES)
num_classes = len(LABEL_MAP)
#模型已经训练过,切换到推理
#加载模型，使用原有的平均数和标准差进行特征调整
model, mean, std, _= load_model(input_dim=input_dim,num_classes=num_classes,path=model_save_path)
model.eval()

def event_feature_trans(event: dict) -> Tensor:
    feature_value = []
    
    for name in FEATURE_NAMES:
        value = event.get(name,0)
        if name == "interface_status":
            value = 1 if value == "UP" or value == "up" else 0
        feature_value.append(float(value))

    if len(feature_value) != 16:#不等于16位则无法输入
        raise ValueError("length of feature is not 16")
    return torch.tensor(feature_value, dtype=torch.long)


def predict(id,event):
    # X, _ = load_labeled_samples(eval_data_path)#输入需要推理的数据集路径
    X = event_feature_trans(event)
    X, _, _ = features_adjustment(X, mean=mean, std=std)
    with torch.no_grad():#不记录梯度（参数），节省内存
        logits = model(X)
        pred_ids = torch.argmax(logits, dim=1)
        probs = torch.softmax(logits,dim=1)
        confidence, pred_id = torch.max(probs, dim=1)

    pred_id_value = pred_id.item()
    confidence_value = confidence.item()

    result = {
        "device": event.get("device"),
        "event_id": id,
        "interface": event.get("interface"),
        "pred_id": pred_id_value,
        "pred_event": ID_TO_LABEL[int(pred_id_value)],
        "confidence": round(confidence_value, 4),
    }
    return result

