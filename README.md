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

当前样本数据以 JSONL 形式保存，示例路径：

```text
data/samples/labeled_events.jsonl