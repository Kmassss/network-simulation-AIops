# 本地流量进入 EVE-NG 拓扑配置记录

## 流量入口链路

Windows PC → VMnet1 → EVE-NG Cloud1/pnet1 → R3 e0/3

## IP 规划

Windows VMnet1：192.168.47.1/24  
R3 e0/3：192.168.47.100/24  
R3 Loopback0：10.10.3.3/32  
R2 Loopback0：10.10.2.2/32  
SW Loopback0：10.10.1.1/32  

## Windows 静态路由

route -p add 10.10.0.0 mask 255.255.0.0 192.168.47.100

## 验证命令

ping 192.168.47.100  
ping 10.10.3.3  
ping 10.10.2.2  
ping 10.10.1.1  

## 设备检查命令

show ip interface brief  
show ip ospf neighbor  
show ip route ospf  
show interfaces e0/3  
show interfaces counters  