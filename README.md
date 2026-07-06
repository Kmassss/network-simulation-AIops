# network-simulation-lab

## 项目说明

本项目用于通过 Netmiko 登录 EVE-NG 模拟交换机，采集接口信息，并将采集结果保存到 output 目录。

## 项目结构

app/main.py：主程序  
config/deviceConf.yaml：设备连接信息  采集命令在main里，后续命令包装为函数以供调用
output/：采集结果输出目录  
Dockerfile：镜像构建文件  
requirements.txt：Python依赖  

## 构建镜像

sudo nerdctl build -n k8s.io -t netops-collector:0.1 .

## 运行容器

sudo nerdctl run --rm \
  --net=host \
  -v /root/network-simulation-lab/output:/workspace/output \
  -it netops-collector:0.1 bash

## 常见问题

1. 如果容器无法访问 EVE-NG，优先检查网络，并尝试使用 --net=host。
2. 如果 output 没有文件，检查挂载路径是否正确。
3. 如果构建时拉取 python:3.11-slim 超时，检查 BuildKit 或 containerd 镜像源。
4. 如果提示找不到 app/main.py，检查 Dockerfile 的 WORKDIR 和 COPY 路径。

## 后续 Prometheus Exporter 改造方向
1. 当前程序是一次性采集任务；
2. 后续将基于 prometheus_client 暴露 /metrics 接口；
3. 设备连接状态转换为 device_up；
4. 命令执行状态转换为 command_success；
5. 接口状态统计转换为 interface_up_total、interface_down_total；
6. 后续可部署为 K8s Deployment。