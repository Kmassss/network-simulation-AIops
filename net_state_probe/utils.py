def to_int(value, default=0):
    if value is None:
        return default

    if isinstance(value, int):
        return value

    value = str(value).strip().replace(",", "")

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default
    
def is_up(value) -> bool:
    if value is None:
        return False

    value = str(value).strip().lower()
    return value.startswith("up")

def normalize_port(port):
    """
    把 www / https 等端口名统一成数字字符串。
    """
    if port is None:
        return "any"

    port = str(port).strip().lower()

    port_map = {
        "www": "80",
        "http": "80",
        "https": "443",
    }

    return port_map.get(port, port)

def flatten_acl_observations(device_item):
    """
    把 acl_observation 展平成一条条规则。
    """
    device_name = device_item.get("device", "unknown")
    acl_groups = device_item.get("acl_observation") or []

    flat = []

    for group in acl_groups:
        acl_name = group.get("acl_name", "unknown")

        for rule in group.get("item", []):
            flat.append({
                "device": device_name,
                "acl_name": acl_name,
                "protocol": rule.get("protocol"),
                "target": rule.get("target"),
                "port": normalize_port(rule.get("port")),
                "matches": to_int(rule.get("matches")),
            })

    return flat