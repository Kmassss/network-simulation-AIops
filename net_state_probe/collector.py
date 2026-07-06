# 建立连接，管理执行命令
from netmiko import ConnectHandler
import logging
from pathlib import Path
from datetime import datetime
import os,yaml,re

command_dict = {
    "brief":"show ip interface brief",
    "interface":"show interfaces",
    "log":"show logging",
    "route":"show ip route"
}

def parse_acl_matches(net_connect) -> dict:

    results = {"ACL":[]}
    current_acl = "unknown"
    acl_output = net_connect.send_command("show access-lists")

    for line in acl_output.splitlines():
        line = line.strip()
        if not line:
            continue

        acl_name_match = re.search(r"(?:Extended|Standard) IP access list\s+(\S+)", line)
        if acl_name_match:
            current_acl = acl_name_match.group(1)
            continue

        if "permit" not in line:
            continue

        rule_match = re.search(
            r"permit\s+(?P<protocol>icmp|tcp|udp|ip)\b.*?host\s+(?P<target>\d+\.\d+\.\d+\.\d+)(?:\s+eq\s+(?P<port>\S+))?",
            line
        )

        if not rule_match:
            continue

        match_count = 0
        count_match = re.search(r"\((?P<matches>\d+)\s+matches\)", line)
        if count_match:
            match_count = int(count_match.group("matches"))

        protocol = rule_match.group("protocol")
        target = rule_match.group("target")
        port = rule_match.group("port") or "any"

        
        if not results["ACL"]:
            results["ACL"].append({"acl_name":current_acl,
                                  "item":[{
                                      "protocol": protocol,
                                      "target": target,
                                      "port": port,
                                      "matches": match_count,
                                      }]})
        elif current_acl == results["ACL"][-1]["acl_name"]:
            results["ACL"][-1]["item"].append({
                "protocol": protocol,
                "target": target,
                "port": port,
                "matches": match_count,
            })
        else:
            results["ACL"].append({"acl_name":current_acl,
                                  "item":[{
                                      "protocol": protocol,
                                      "target": target,
                                      "port": port,
                                      "matches": match_count,
                                      }]})

    return results

def connect_device(device:dict):
    logging.info("connection building: %s", device['host'])
    net_connect = ConnectHandler(**device)
    logging.info("connection success")
    return net_connect

def collect_interface_info(net_connect,action:str):
    result = {}
    command = command_dict[action]
    raw_output = net_connect.send_command(command,use_textfsm=True)
    logging.info("raw output: %s", raw_output)
    return {"output": raw_output}

def config_load(path):
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / path 
    with open(config_path, "r", encoding="utf-8") as f: #根据当前路径获取配置绝对路径并读取
        config = yaml.safe_load(f)['devices']
    return config
