#定义数据集结构与工作流，并收集数据
from netmiko import ConnectHandler
import logging
from pathlib import Path
from datetime import datetime
import os,yaml,json,datetime
from collector import connect_device,config_load, collect_interface_info,parse_acl_matches
from utils import to_int, is_up, flatten_acl_observations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

def count_interface_status(parsed_output) -> dict:
    total = 0
    up = 0
    down = 0
    if not parsed_output:
        return {
            "total": 0,
            "up": 0,
            "down": 0
        }

    for item in parsed_output['output']:
        total += 1

        status = item.get("status")
        proto = item.get("proto")

        if status == "up" and proto == "up":
            up += 1
        else:
            down += 1

    return {
        'device': parsed_output["device"],
        "total": total,
        "up": up,
        "down": down
    }

def parse_show_interfaces_textfsm(parsed_output) -> dict:

    results = {}

    if not parsed_output:
        return results

    device_name = parsed_output.get("device", "unknown")
    output = parsed_output.get("output", [])

    if not isinstance(output, list):
        return results

    for item in output:
        if not isinstance(item, dict):
            continue

        interface_name = (
            item.get("interface")
            or item.get("intf")
            or item.get("port")
            or "unknown"
        )


        status = (
            item.get("link_status")
            or item.get("status")
            or "unknown"
        )

        protocol = (
            item.get("protocol_status")
            or item.get("proto")
            or item.get("protocol")
            or "unknown"
        )

        results.update({interface_name:{
            "status": status,
            "protocol": protocol,

            "input_packets": to_int(
                item.get("input_packets")
                or item.get("packets_input")
            ),
            "input_bytes": to_int(
                item.get("input_bytes")
                or item.get("bytes_input")
            ),
            "output_packets": to_int(
                item.get("output_packets")
                or item.get("packets_output")
            ),
            "output_bytes": to_int(
                item.get("output_bytes")
                or item.get("bytes_output")
            ),

            "input_errors": to_int(item.get("input_errors")),
            "output_errors": to_int(item.get("output_errors")),
            "crc_errors": to_int(
                item.get("crc")
                or item.get("crc_errors")
            ),
            "collisions": to_int(item.get("collisions")),

            "input_rate_bps": to_int(
                item.get("input_rate")
                or item.get("input_rate_bps")
            ),
            "output_rate_bps": to_int(
                item.get("output_rate")
                or item.get("output_rate_bps")
            ),
        }})

    return results

config = config_load(path = "config/deviceConf.yaml")
def work_flow(device:dict):       
    connection = None
    try:
        logging.info("connection target: %s", device['name'])   
        target = device.pop('name') #剔除多余参数
        connection = connect_device(device)
        output = collect_interface_info(connection,"interface") #执行命令函数并获得结果后补充必要信息
        acl_match = parse_acl_matches(connection)

        return {target:{**parse_show_interfaces_textfsm(output), **acl_match}}


    except Exception as e:
        logging.exception("collect failure: %s", e)

    finally:
        if connection:
            connection.disconnect()
            logging.info("disconnected")

def calling_point():
    config = config_load(path = "config/deviceConf.yaml")
    res = []
    with ThreadPoolExecutor(max_workers=len(config)) as executor:
        threads=[executor.submit(work_flow, device)
                for device in config
                ]
        for thread in as_completed(threads):
            res.append(thread.result())
    return res

def extract_device_features(device_item: dict) -> dict:
    """
    从单台设备的结构化输出中提取有用信息。

    输入：单台设备 dict
    输出：精简后的 AI 运维特征
    """
    result = {}
    for device_name, info_dict in device_item.items():
        result = {
            "device": device_name,
            "status": "unknown",
            "acl_observation": None,
            "traffic_interfaces": [],
            "interface_health": {
                "total_interfaces": 0,
                "up_interfaces": 0,
                "down_interfaces": 0,
                "error_interfaces": 0,
                "total_input_packets": 0,
                "total_output_packets": 0,
                "total_input_bytes": 0,
                "total_output_bytes": 0,
                "total_input_errors": 0,
                "total_output_errors": 0,
                "total_crc_errors": 0,
            }
        }

        # 1. 提取 ACL 信息
        acl_info = info_dict.get("ACL") or info_dict.get("acl")

        if isinstance(acl_info, list):
            result["acl_observation"] = acl_info


        # 2. 提取接口信息
        for key, value in info_dict.items():
            # 跳过非接口字段
            if key in ["device", "host", "status", "ACL", "acl", "parsed", "commands"]:
                continue

            # 只处理 Ethernet / Loopback 等接口字段
            if not (
                key.startswith("Ethernet")
                or key.startswith("GigabitEthernet")
                or key.startswith("FastEthernet")
                or key.startswith("Loopback")
            ):
                continue

            if not isinstance(value, dict):
                continue

            interface_name = key

            input_packets = to_int(value.get("input_packets"))
            output_packets = to_int(value.get("output_packets"))
            input_bytes = to_int(value.get("input_bytes"))
            output_bytes = to_int(value.get("output_bytes"))

            input_errors = to_int(value.get("input_errors"))
            output_errors = to_int(value.get("output_errors"))
            crc_errors = to_int(value.get("crc_errors"))

            input_rate_bps = to_int(value.get("input_rate_bps"))
            output_rate_bps = to_int(value.get("output_rate_bps"))

            status = str(value.get("status", "unknown")).lower()
            protocol = str(value.get("protocol", "unknown")).lower()

            result["interface_health"]["total_interfaces"] += 1
            result["interface_health"]["total_input_packets"] += input_packets
            result["interface_health"]["total_output_packets"] += output_packets
            result["interface_health"]["total_input_bytes"] += input_bytes
            result["interface_health"]["total_output_bytes"] += output_bytes
            result["interface_health"]["total_input_errors"] += input_errors
            result["interface_health"]["total_output_errors"] += output_errors
            result["interface_health"]["total_crc_errors"] += crc_errors

            if is_up(status) and is_up(protocol):
                result["interface_health"]["up_interfaces"] += 1
            else:
                result["interface_health"]["down_interfaces"] += 1

            if input_errors > 0 or output_errors > 0 or crc_errors > 0:
                result["interface_health"]["error_interfaces"] += 1

            # 只保留有流量或有异常的接口，避免输出太长
            if (
                input_packets > 0
                or output_packets > 0
                or input_rate_bps > 0
                or output_rate_bps > 0
                or input_errors > 0
                or output_errors > 0
                or crc_errors > 0
            ):
                result["traffic_interfaces"].append({
                    "interface": interface_name,
                    "status": status,
                    "protocol": protocol,
                    "input_packets": input_packets,
                    "output_packets": output_packets,
                    "input_bytes": input_bytes,
                    "output_bytes": output_bytes,
                    "input_rate_bps": input_rate_bps,
                    "output_rate_bps": output_rate_bps,
                    "input_errors": input_errors,
                    "output_errors": output_errors,
                    "crc_errors": crc_errors,
                })

        if result["interface_health"]["down_interfaces"] > 0:
            result["status"] = "warning"
        elif result["interface_health"]["error_interfaces"] > 0:
            result["status"] = "warning"
        else:
            result["status"] = "up"

    return result


def parse_device_observation(device_item):
    device_name = device_item.get("device", "unknown")

    acl_rules = flatten_acl_observations(device_item)

    interfaces = device_item.get("traffic_interfaces") or []

    interface_summary = {
        "total_interfaces": 0,
        "up_interfaces": 0,
        "down_interfaces": 0,
        "error_interfaces": 0,
        "active_interfaces": [],
        "total_input_packets": 0,
        "total_output_packets": 0,
        "total_input_errors": 0,
        "total_output_errors": 0,
        "total_crc_errors": 0,
    }

    for iface in interfaces:
        interface_summary["total_interfaces"] += 1

        interface_name = iface.get("interface", "unknown")
        status = iface.get("status")
        protocol = iface.get("protocol")

        input_packets = to_int(iface.get("input_packets"))
        output_packets = to_int(iface.get("output_packets"))
        input_rate_bps = to_int(iface.get("input_rate_bps"))
        output_rate_bps = to_int(iface.get("output_rate_bps"))

        input_errors = to_int(iface.get("input_errors"))
        output_errors = to_int(iface.get("output_errors"))
        crc_errors = to_int(iface.get("crc_errors"))

        interface_summary["total_input_packets"] += input_packets
        interface_summary["total_output_packets"] += output_packets
        interface_summary["total_input_errors"] += input_errors
        interface_summary["total_output_errors"] += output_errors
        interface_summary["total_crc_errors"] += crc_errors

        if is_up(status) and is_up(protocol):
            interface_summary["up_interfaces"] += 1
        else:
            interface_summary["down_interfaces"] += 1

        if input_errors > 0 or output_errors > 0 or crc_errors > 0:
            interface_summary["error_interfaces"] += 1

        # 只保留有明显流量或错误的接口
        if (
            input_packets > 0
            or output_packets > 0
            or input_rate_bps > 0
            or output_rate_bps > 0
            or input_errors > 0
            or output_errors > 0
            or crc_errors > 0
        ):
            interface_summary["active_interfaces"].append({
                "interface": interface_name,
                "status": status,
                "protocol": protocol,
                "input_packets": input_packets,
                "output_packets": output_packets,
                "input_rate_bps": input_rate_bps,
                "output_rate_bps": output_rate_bps,
                "input_errors": input_errors,
                "output_errors": output_errors,
                "crc_errors": crc_errors,
            })

    if interface_summary["down_interfaces"] > 0:
        health_status = "warning"
    elif interface_summary["error_interfaces"] > 0:
        health_status = "warning"
    else:
        health_status = "up"

    return {
        "device": device_name,
        "status": health_status,
        "acl_rules": acl_rules,
        "interface_summary": interface_summary,
    }

def extract_network_summary(device_features):
    """
    输入：多台设备的 feature list
    输出：全网汇总特征
    """

    summary = {
        "device_count": 0,
        "up_devices": 0,
        "warning_devices": 0,
        "collect_failed_devices": 0,

        "total_acl_matches": 0,
        "acl_match_by_protocol_port": {},

        "total_input_packets": 0,
        "total_output_packets": 0,
        "total_input_errors": 0,
        "total_output_errors": 0,
        "total_crc_errors": 0,

        "primary_traffic": None,
    }

    for device in device_features:
        summary["device_count"] += 1

        status = device.get("status", "unknown")

        if status == "up":
            summary["up_devices"] += 1
        elif status == "collect_failed":
            summary["collect_failed_devices"] += 1
        else:
            summary["warning_devices"] += 1

        # 汇总 ACL 命中
        for rule in device.get("acl_rules", []):
            protocol = rule.get("protocol", "unknown")
            port = str(rule.get("port", "any"))
            matches = to_int(rule.get("matches"))

            key = f"{protocol}_{port}"

            summary["acl_match_by_protocol_port"][key] = (
                summary["acl_match_by_protocol_port"].get(key, 0) + matches
            )

            summary["total_acl_matches"] += matches

        # 汇总接口信息
        iface_summary = device.get("interface_summary", {})

        summary["total_input_packets"] += to_int(
            iface_summary.get("total_input_packets")
        )
        summary["total_output_packets"] += to_int(
            iface_summary.get("total_output_packets")
        )
        summary["total_input_errors"] += to_int(
            iface_summary.get("total_input_errors")
        )
        summary["total_output_errors"] += to_int(
            iface_summary.get("total_output_errors")
        )
        summary["total_crc_errors"] += to_int(
            iface_summary.get("total_crc_errors")
        )

    # 找出最主要的协议/端口
    if summary["acl_match_by_protocol_port"]:
        primary_key = max(
            summary["acl_match_by_protocol_port"],
            key=summary["acl_match_by_protocol_port"].get
        )

        summary["primary_traffic"] = {
            "protocol_port": primary_key,
            "matches": summary["acl_match_by_protocol_port"][primary_key],
        }

    return summary

def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def append_jsonl(path: str, record: dict):
    ensure_parent_dir(path)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def infer_traffic_type(summary: dict) -> str:
    """
    根据设备侧 ACL matches 推断流量类型。
    注意：这是 inferred_type，不是训练 label。
    """

    acl_map = summary.get("acl_match_by_protocol_port", {})

    tcp_8080 = acl_map.get("tcp_8080", 0)
    tcp_9000 = acl_map.get("tcp_9000", 0)
    udp_9999 = acl_map.get("udp_9999", 0)
    icmp_any = acl_map.get("icmp_any", 0)

    tcp_22 = acl_map.get("tcp_22", 0)
    tcp_80 = acl_map.get("tcp_80", 0)
    tcp_443 = acl_map.get("tcp_443", 0)

    active_probe_ports = sum(
        1 for value in [tcp_22, tcp_80, tcp_443, tcp_8080, tcp_9000]
        if value > 0
    )
    print(active_probe_ports)

    if active_probe_ports >= 3:
        return "tcp_probe"

    if tcp_8080 >= 1000:
        return "http_burst"

    if tcp_8080 > 0:
        return "http_normal"

    if tcp_9000 > 0:
        return "tcp_connect"

    if udp_9999 >= 50:
        return "udp_burst"

    if icmp_any > 0:
        return "icmp_ping"

    return "unknown"


def build_training_sample(
    scenario: str,
    network_features: dict,
    target: str = "192.168.48.128",
    counter_mode: str = "acl_clear_before_scenario",
) -> dict:
    
    """
    根据当前 network_features 生成 PyTorch / AI 训练用样本。

    scenario：你运行 traffic_gen.py 时的 --mode
    label：训练标签，直接等于 scenario
    inferred_type：由设备数据规则推断出来的类型
    """

    return {
        "sample_time": now_iso(),
        "scenario": scenario,
        "label": scenario,
        "inferred_type": infer_traffic_type(network_features),
        "target": target,
        "counter_mode": counter_mode,
        "main_observation": "network_device_acl_and_interface_counters",
        "endpoint_logs_used": False,
        "features": network_features,
    }



def save_training_sample(
    scenario: str,
    network_features: dict,
    output_file: str = "data/samples/labeled_events.jsonl",
    target: str = "192.168.48.128",
) -> dict:
    """
    构造并保存一条训练样本。
    """

    sample = build_training_sample(
        scenario=scenario,
        network_features=network_features,
        target=target,
    )

    append_jsonl(output_file, sample)

    return sample