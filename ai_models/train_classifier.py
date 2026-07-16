import torch
from torch import Tensor
import torch.nn as nn
import json
from collections import Counter
from pathlib import Path
from ai_utils import load_labeled_samples, load_model, features_adjustment, save_model, TrafficClassifier, FEATURE_NAMES, LABEL_MAP

SAMPLE_FILE = "data/samples/labeled_events.jsonl"
model_save_path = "data/models/traffic_checkpoint.pt"


def model_trainer(model, X,y,optimizer_state=None):
    '''定义模型训练过程'''
    lr = 0.001
    epoch = 100
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(),lr=lr)

    if optimizer_state is not None:     
        optimizer.load_state_dict(optimizer_state)#如果已有训练过的模型,加载优化器状态,继续训练

    for epoch in range(1,epoch + 1):
        #模型设置为训练
        model.train()
        #输出模型结果(前向计算)
        logits = model(X)
        #计算误差
        loss = loss_fn(logits, y)
        #清空优化器梯度,重新调整
        optimizer.zero_grad()
        #反向传播，修改对应参数
        loss.backward()
        #更新参数
        optimizer.step()

    return model, optimizer.state_dict()



def train_model(path: str|None):
    input_dim = len(FEATURE_NAMES)
    num_classes = len(LABEL_MAP)

    '''y为标签,即正确答案'''
    if path:
        X, y = load_labeled_samples(path)#若有其他训练数据则需要传入文件路径作为参
    else:
        X, y = load_labeled_samples()
    try:
        if not Path(model_save_path).exists():
            '''模型尚未训练,进行训练'''
            X, mean, std = features_adjustment(X)
            model = TrafficClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
        )
            model, optimizer_state = model_trainer(model=model, X=X, y=y)#训练，无需加载优化器状态
        else:
            '''继续训练模型'''
            model, mean, std, optimizer_state = load_model(input_dim=input_dim, num_classes=num_classes, path=model_save_path)
            X, mean, std = features_adjustment(X, mean=mean, std=std)#使用原有的平均数和标准差进行特征调整
            model, optimizer_state = model_trainer(model=model, X=X, y=y, optimizer_state=optimizer_state)#训练，加载优化器状态
        save_model(model,mean,std,optimizer_state,model_save_path) #保存模型
    except Exception as e:
        raise Exception
    return { "result":"success"}

    