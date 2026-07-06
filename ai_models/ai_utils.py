import torch
from torch import Tensor
import torch.nn as nn
import json
from pathlib import Path


SAMPLE_FILE = "data/samples/labeled_events.jsonl"
model_save_path = "data/models/traffic_checkpoint.pt"

# 定义输入的特征值，之后会转换成[0,0,3343,0,0..]这样的数列作为输入
FEATURE_NAMES = [
    "icmp_any",
    "tcp_22",
    "tcp_80",
    "tcp_443",
    "tcp_8080",
    "tcp_9000",
    "udp_9999", 
    "total_acl_matches",
    "total_input_packets",
    "total_output_packets",
    "total_input_errors",
    "total_output_errors",
    "total_crc_errors",
    "up_devices",
    "warning_devices",
    "collect_failed_devices",
]

#定义label映射
LABEL_MAP = {
    "tcp_connect": 0,
    "http_normal": 1,
    "http_burst": 2,
    "icmp_ping": 3,
    "udp_burst": 4,
}

#定义模型
class TrafficClassifier(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()

        #第一层 input特征生成32 interim特征
        self.layer1 = nn.Linear(input_dim,32)
        self.relu1 = nn.ReLU()

        #第二层 32 interim特征生成16高级特征
        self.layer2 = nn.Linear(32, 16)
        self.relu2 = nn.ReLU()

        #第三层 高级特征生成5个分类分数
        self.output_layer = nn.Linear(16, num_classes)

    #前向函数，执行模型的工作流
    def forward(self, x):
        #x构成：[样本数，每条样本内的特征数]
        x = self.layer1(x)
        x = self.relu1(x)

        x = self.layer2(x)
        x = self.relu2(x)

        logits = self.output_layer(x)
        return logits

def flatten_features(sample: dict) -> list:
    """
    把一条 jsonl 样本转换成 16 个数字特征。
    输入：一条完整 sample
    输出：长度为 16 的 list
    """

    features = sample.get("features", {})
    acl_map = features.get("acl_match_by_protocol_port", {}) or {}

    row = [
        acl_map.get("icmp_any", 0),
        acl_map.get("tcp_22", 0),
        acl_map.get("tcp_80", 0),
        acl_map.get("tcp_443", 0),
        acl_map.get("tcp_8080", 0),
        acl_map.get("tcp_9000", 0),
        acl_map.get("udp_9999", 0),

        features.get("total_acl_matches", 0),
        features.get("total_input_packets", 0),
        features.get("total_output_packets", 0),
        features.get("total_input_errors", 0),
        features.get("total_output_errors", 0),
        features.get("total_crc_errors", 0),
        features.get("up_devices", 0),
        features.get("warning_devices", 0),
        features.get("collect_failed_devices", 0),
    ]

    return row


def load_labeled_samples(path: str = SAMPLE_FILE):
    """读取 jsonl,转换成训练用的x/y(label)"""

    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"not existing: {path}")

    xs = []
    labels = []

    with open(path_obj, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                sample = json.loads(line)
            except Exception as e:
                print(f"[WARN] line {line_no} is illegal JSON,{e}, skip")
                continue

            label = sample.get("label") or sample.get("scenario")

            row = flatten_features(sample)

            xs.append(row)
            labels.append(label)

    if not xs:
        raise ValueError("empty sample")

    if labels and labels[0] is not None:
        y_ids = [LABEL_MAP[label] for label in labels]
        y = torch.tensor(y_ids, dtype=torch.long)
    else:
        y = torch.tensor([], dtype=torch.long)

    X = torch.tensor(xs, dtype=torch.float32)
    

    return X, y

def save_model(model, mean, std, optimizer_state, path: str = model_save_path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "model_checkpoint": model.state_dict(),
        "optimizer_state": optimizer_state,
        "feature_names": FEATURE_NAMES,
        "label_map": LABEL_MAP,
        "mean": mean,
        "std": std
    }

    try:
        torch.save(checkpoint,path)
    except Exception as e:
        print(f"[ERROR] failed to save model: {e}")
        exit(1)


def load_model( input_dim: int, num_classes: int, path: str = model_save_path):
    checkpoint = torch.load(path, map_location=torch.device("cpu"))
    optimizer_state = checkpoint.get("optimizer_state")
    model = TrafficClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
        )
    model.load_state_dict(checkpoint["model_checkpoint"])
    mean = checkpoint["mean"]
    std = checkpoint["std"]
    return model, mean, std, optimizer_state


def features_adjustment(X:Tensor, mean:Tensor | None = None, std:Tensor | None = None): 
    '''输入特征标准化,将大数量级的参数调整为相同量级'''
    if mean is None:
        mean = X.mean(dim=0)
    if std is None:
        std = X.std(dim=0)

    #将全部为0的特征的标准差设为1，防止分母为0
    std[std == 0] = 1.0

    X_norm = (X - mean) / std

    return X_norm, mean, std