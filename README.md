# Network Simulation AIOps Lab

本项目是一个面向网络运维场景的 AIOps 实验项目，基于 EVE-NG 网络仿真环境、Python 自动化采集、Flask API、PyTorch 本地模型、Kafka 异步任务机制以及后续 Prometheus / Kubernetes / LLM Agent 能力，构建一个从“网络状态采集 → 数据样本构建 → 异常识别 → 任务异步处理 → 智能分析解释”的完整实验链路。

项目当前处于 AIOps 主线开发阶段，已完成基础网络自动化采集、样本构建、本地模型训练与 Flask 接口封装的初步实现，正在推进训练/推理任务异步化、Kafka 消息投递和 Agent 推理解耦。

---

## 1. 项目目标

本项目的目标不是单纯写一个网络脚本，而是逐步搭建一个贴近真实运维场景的 AIOps 原型系统。

主要目标包括：

1. 使用 Python 自动化采集网络设备状态；
2. 将网络接口、ACL、路由、设备状态等信息转换为结构化样本；
3. 使用 PyTorch 训练基础异常识别模型；
4. 使用 Flask 对外提供训练和推理接口；
5. 使用进程池 / 任务锁 / Kafka 解耦耗时任务；
6. 后续接入 Prometheus 与 Kubernetes 监控数据；
7. 后续引入 LLM / Agent 对异常结果进行解释和处置建议生成。

---

## 2. 技术栈

当前项目涉及以下技术：

| 类型 | 技术 |
|---|---|
| 网络仿真 | EVE-NG、Cisco IOL |
| 网络自动化 | Python、Netmiko |
| Web API | Flask、Blueprint |
| 机器学习 | PyTorch、MLP |
| 数据处理 | JSONL、Pandas |
| 异步任务 | ProcessPoolExecutor、任务锁 |
| 消息队列 | Kafka、confluent-kafka |
| 容器化 | Docker |
| 监控方向 | Prometheus |
| 云原生方向 | Kubernetes |
| 智能分析方向 | LLM、Agent |

---

## 3. 当前已实现功能

### 3.1 网络设备数据采集

已实现通过 Python 登录网络设备，采集基础网络状态信息，包括但不限于：

- 设备接口状态；
- 接口 IP 信息；
- 设备运行状态；
- 网络连通性相关信息；
- 后续可扩展 ACL、OSPF、路由表等信息采集。

当前采集逻辑主要面向 EVE-NG 中的 Cisco 模拟设备，用于构建可控的网络异常实验环境。

---

### 3.2 样本数据构建

项目已开始将网络采集结果转换为结构化样本，用于模型训练和推理。

### 3.3 PyTorch 本地模型训练

当前已基于 PyTorch 搭建基础分类模型，用于识别网络异常类型。

当前模型主线包括：

特征处理；
label 映射；
MLP 模型训练；
loss 计算；
optimizer 参数更新；
模型保存与加载。

当前模型主要用于实验验证，后续会继续优化：

训练集 / 测试集划分；
过拟合检测；
指标评估；
模型版本管理；
推理结果解释。
### 3.4 Flask API 接口封装

当前已开始使用 Flask 对模型训练和推理能力进行接口封装。

当前接口规划包括：

接口	方法	说明
/train	POST	提交模型训练任务
/predict	POST	提交模型推理任务
/status/<session_id>	GET	查询任务状态，后续完善
/health	GET	服务健康检查，后续完善

当前 /train 接口正在进行异步化改造，目标是将耗时训练任务从 Flask 请求主流程中解耦。

### 3.5 异步任务与锁机制

由于模型训练属于耗时任务，项目正在将训练逻辑从普通同步接口中拆分出来。

当前设计方向：

Flask 接口只负责接收请求；
使用任务锁控制同一时间只允许一个训练任务运行；
使用进程池提交训练任务；
训练完成后通过 Kafka 或任务状态存储返回结果；
API 主流程快速返回 session_id 或 busy 状态。

当前计划中的任务状态包括：

状态	含义
submitted	任务已提交
running	任务运行中
success	任务成功
failed	任务失败
busy	当前已有训练任务执行中
### 3.6 Kafka 异步结果投递

项目正在引入 Kafka，用于将训练结果、推理结果或任务状态从模型执行流程中解耦出来。

Kafka 在本项目中的作用：

解耦 Flask 请求与模型执行；
训练任务完成后向指定 topic 投递结果；
推理结果可以通过 consumer 异步消费；
后续可用于接入 Agent 分析模块。

计划中的 topic 示例：

aiops.train.result
aiops.predict.result
aiops.agent.analysis

--
## 4. 项目整体架构

当前设计架构如下：
```text
EVE-NG / Cisco Devices
        |
        | Netmiko
        v
Network Collector
        |
        | structured events
        v
Sample Builder
        |
        | JSONL / Features
        v
PyTorch Model
        |
        | train / predict
        v
Flask API
        |
        | async task
        v
Process Pool / Lock
        |
        | result event
        v
Kafka
        |
        v
Consumer / Agent / Result Handler
```

后续扩展架构：
```text
Prometheus / Kubernetes Metrics
        |
        v
AIOps Feature Pipeline
        |
        v
ML Model + LLM Agent
        |
        v
Root Cause Analysis / Suggestion
```
--
## 5. 项目目录结构

当前建议目录结构如下：

```text
network-simulation-AIOps/
├── app/
│   ├── __init__.py
│   ├── blueprints/
│   │   └── inference_bp.py
│   ├── services/
│   │   ├── train_service.py
│   │   ├── predict_service.py
│   │   ├── kafka_service.py
│   │   └── lock_service.py
│   └── utils/
│
├── collector/
│   ├── device_collector.py
│   └── parser.py
│
├── config/
│   ├── deviceConf.example.yaml
│   └── settings.example.yaml
│
├── data/
│   └── samples/
│       └── labeled_events.jsonl
│
├── models/
│   └── README.md
│
├── scripts/
│   ├── run_collector.py
│   ├── train_model.py
│   └── predict.py
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .gitignore
```