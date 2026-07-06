import argparse
import concurrent.futures
import datetime
import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import List


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_jsonl(log_file: str, event: dict) -> None:
    event.setdefault("timestamp", now_iso())
    ensure_parent_dir(log_file)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_ping(target: str, count: int, timeout: int, log_file: str) -> None:
    system = platform.system().lower()

    cmd = ["ping", "-c", str(count), "-W", str(timeout), target]

    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(timeout * count + 5, 10),
        )

        duration = round(time.time() - start, 3)

        event = {
            "mode": "icmp_ping",
            "target": target,
            "command": " ".join(cmd),
            "returncode": result.returncode,
            "duration_seconds": duration,
            "success": result.returncode == 0,
            "stdout_preview": result.stdout[-500:],
            "stderr_preview": result.stderr[-500:],
        }
        write_jsonl(log_file, event)

        print(f"[PING] target={target} success={event['success']} duration={duration}s")

    except Exception as e:
        event = {
            "mode": "icmp_ping",
            "target": target,
            "error": str(e),
            "success": False,
        }
        write_jsonl(log_file, event)
        print(f"[PING] target={target} error={e}")


def http_request(port: int, path: str, timeout: int, log_file: str, index: int = 0, target: str = "192.168.48.128", ) -> bool:
    url = f"http://{target}:{port}{path}"
    start = time.time()

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "aiops-traffic-gen/0.1",
                "X-AIOps-Scenario": "http",
                "X-Request-Index": str(index),
            },
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(300)

        duration = round(time.time() - start, 3)

        event = {
            "mode": "http",
            "target": target,
            "port": port,
            "url": url,
            "index": index,
            "status_code": resp.status,
            "duration_seconds": duration,
            "success": 200 <= resp.status < 400,
            "body_preview": body.decode("utf-8", errors="replace"),
        }
        write_jsonl(log_file, event)

        print(f"[HTTP] {url} status={resp.status} duration={duration}s")
        return True

    except urllib.error.HTTPError as e:
        duration = round(time.time() - start, 3)

        event = {
            "mode": "http",
            "target": target,
            "port": port,
            "url": url,
            "index": index,
            "status_code": e.code,
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
        }
        write_jsonl(log_file, event)

        print(f"[HTTP] {url} http_error={e.code}")
        return False

    except Exception as e:
        duration = round(time.time() - start, 3)

        event = {
            "mode": "http",
            "target": target,
            "port": port,
            "url": url,
            "index": index,
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
        }
        write_jsonl(log_file, event)

        print(f"[HTTP] {url} error={e}")
        return False


def run_http_normal(port: int, count: int, interval: float, timeout: int, log_file: str) -> None:
    for i in range(1, count + 1):
        http_request(port, path=f"/normal?i={i}", timeout=timeout, log_file=log_file, index=i)
        time.sleep(interval)


def run_http_burst(
    target: str,
    port: int,
    count: int,
    concurrency: int,
    timeout: int,
    log_file: str,
) -> None:
    print(f"[HTTP_BURST] target={target}:{port} count={count} concurrency={concurrency}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(1, count + 1):
            futures.append(
                executor.submit(
                    http_request,
                    port,
                    f"/burst?i={i}",
                    timeout,
                    log_file,
                    i,
                )
            )

        success_count = 0
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                success_count += 1

    summary = {
        "mode": "http_burst_summary",
        "target": target,
        "port": port,
        "count": count,
        "concurrency": concurrency,
        "success_count": success_count,
        "failed_count": count - success_count,
    }
    write_jsonl(log_file, summary)

    print(f"[HTTP_BURST] done success={success_count} failed={count - success_count}")


def tcp_connect(target: str, port: int, timeout: int, log_file: str, index: int = 0) -> bool:
    start = time.time()

    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            message = f"hello tcp from traffic_gen index={index} time={now_iso()}\n"
            sock.sendall(message.encode("utf-8"))
            sock.settimeout(timeout)
            data = sock.recv(1024)

        duration = round(time.time() - start, 3)

        event = {
            "mode": "tcp_connect",
            "target": target,
            "port": port,
            "index": index,
            "duration_seconds": duration,
            "success": True,
            "response_preview": data.decode("utf-8", errors="replace"),
        }
        write_jsonl(log_file, event)

        print(f"[TCP ] target={target}:{port} success=True duration={duration}s")
        return True

    except Exception as e:
        duration = round(time.time() - start, 3)

        event = {
            "mode": "tcp_connect",
            "target": target,
            "port": port,
            "index": index,
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
        }
        write_jsonl(log_file, event)

        print(f"[TCP ] target={target}:{port} success=False error={e}")
        return False


def run_tcp_connect(target: str, port: int, count: int, interval: float, timeout: int, log_file: str) -> None:
    for i in range(1, count + 1):
        tcp_connect(target, port, timeout, log_file, index=i)
        time.sleep(interval)


def parse_ports(ports_str: str) -> List[int]:
    ports = []

    for item in ports_str.split(","):
        item = item.strip()
        if not item:
            continue
        ports.append(int(item))

    return ports


def run_tcp_probe(target: str, ports: List[int], interval: float, timeout: int, log_file: str) -> None:
    print(f"[TCP_PROBE] target={target} ports={ports}")

    open_ports = []

    for index, port in enumerate(ports, start=1):
        ok = tcp_connect(target, port, timeout, log_file, index=index)
        if ok:
            open_ports.append(port)

        time.sleep(interval)

    summary = {
        "mode": "tcp_probe_summary",
        "target": target,
        "ports": ports,
        "open_ports": open_ports,
        "closed_or_failed_ports": [p for p in ports if p not in open_ports],
    }
    write_jsonl(log_file, summary)

    print(f"[TCP_PROBE] done open_ports={open_ports}")


def udp_send(target: str, port: int, timeout: int, log_file: str, index: int = 0) -> bool:
    start = time.time()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        message = f"hello udp from traffic_gen index={index} time={now_iso()}".encode("utf-8")
        sock.sendto(message, (target, port))

        try:
            data, addr = sock.recvfrom(1024)
            response_preview = data.decode("utf-8", errors="replace")
            got_response = True
        except socket.timeout:
            response_preview = ""
            got_response = False

        duration = round(time.time() - start, 3)

        event = {
            "mode": "udp_send",
            "target": target,
            "port": port,
            "index": index,
            "bytes_sent": len(message),
            "got_response": got_response,
            "duration_seconds": duration,
            "success": True,
            "response_preview": response_preview,
        }
        write_jsonl(log_file, event)

        print(f"[UDP ] target={target}:{port} sent=True response={got_response}")
        return True

    except Exception as e:
        duration = round(time.time() - start, 3)

        event = {
            "mode": "udp_send",
            "target": target,
            "port": port,
            "index": index,
            "duration_seconds": duration,
            "success": False,
            "error": str(e),
        }
        write_jsonl(log_file, event)

        print(f"[UDP ] target={target}:{port} error={e}")
        return False

    finally:
        sock.close()


def run_udp_burst(target: str, port: int, count: int, interval: float, timeout: int, log_file: str) -> None:
    success_count = 0

    for i in range(1, count + 1):
        ok = udp_send(target, port, timeout, log_file, index=i)
        if ok:
            success_count += 1

        if interval > 0:
            time.sleep(interval)

    summary = {
        "mode": "udp_burst_summary",
        "target": target,
        "port": port,
        "count": count,
        "success_count": success_count,
        "failed_count": count - success_count,
    }
    write_jsonl(log_file, summary)

    print(f"[UDP_BURST] done success={success_count} failed={count - success_count}")


def run_normal(target: str, http_port: int, tcp_port: int, udp_port: int, count: int, interval: float, timeout: int, log_file: str) -> None:
    print(f"[NORMAL] target={target} count={count}")

    for i in range(1, count + 1):
        print(f"[NORMAL] round {i}/{count}")

        run_ping(target, count=1, timeout=timeout, log_file=log_file)
        http_request(http_port, path=f"/normal?round={i}", timeout=timeout, log_file=log_file, index=i)
        tcp_connect(target, tcp_port, timeout=timeout, log_file=log_file, index=i)
        udp_send(target, udp_port, timeout=timeout, log_file=log_file, index=i)

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="AIOps Lab Traffic Generator")

    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "normal",
            "icmp_ping",
            "http_normal",
            "http_burst",
            "tcp_connect",
            "tcp_probe",
            "udp_burst",
        ],
        help="traffic mode",
    )
    parser.add_argument("--target", required=True, help="target IP, example: 192.168.48.10")

    parser.add_argument("--port", type=int, default=None, help="single target port")
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--tcp-port", type=int, default=9000)
    parser.add_argument("--udp-port", type=int, default=9999)
    parser.add_argument("--ports", default="22,80,443,8080,9000", help="ports for tcp_probe")

    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=3)

    parser.add_argument("--log-file", default="output/traffic_gen_events.jsonl")

    args = parser.parse_args()

    print("[INFO] traffic generator started")
    print(f"[INFO] mode={args.mode}")
    print(f"[INFO] target={args.target}")
    print(f"[INFO] log_file={args.log_file}")

    if args.mode == "normal":
        run_normal(
            target=args.target,
            http_port=args.http_port,
            tcp_port=args.tcp_port,
            udp_port=args.udp_port,
            count=args.count,
            interval=args.interval,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "icmp_ping":
        run_ping(
            target=args.target,
            count=args.count,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "http_normal":
        port = args.port or args.http_port
        run_http_normal(
            port=port,
            count=args.count,
            interval=args.interval,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "http_burst":
        port = args.port or args.http_port
        run_http_burst(
            target=args.target,
            port=port,
            count=args.count,
            concurrency=args.concurrency,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "tcp_connect":
        port = args.port or args.tcp_port
        run_tcp_connect(
            target=args.target,
            port=port,
            count=args.count,
            interval=args.interval,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "tcp_probe":
        ports = parse_ports(args.ports)
        run_tcp_probe(
            target=args.target,
            ports=ports,
            interval=args.interval,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    elif args.mode == "udp_burst":
        port = args.port or args.udp_port
        run_udp_burst(
            target=args.target,
            port=port,
            count=args.count,
            interval=args.interval,
            timeout=args.timeout,
            log_file=args.log_file,
        )

    print("[INFO] traffic generator finished")


if __name__ == "__main__":
    main()