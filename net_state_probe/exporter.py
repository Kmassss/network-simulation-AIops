#管理Gauge，提供Prometheus metrics收集endpoint
import time,datetime,os
import logging,yaml,json
from prometheus_client import start_http_server, Gauge
from metrics import calling_point,extract_device_features,extract_device_features,parse_device_observation,extract_network_summary,save_training_sample

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s Prometheus_exporter %(levelname)s %(message)s"
)

device_up = Gauge(
    name="network_device_up",
    documentation="whether the network device is reachable",
    labelnames=["device"]
)

interface_total = Gauge(
    name="network_interface_total",
    documentation="Total number of interfaces",
    labelnames=["device"]
)

interface_up_total = Gauge(
    name="network_interface_up_total",
    documentation="Total number of up interfaces",
    labelnames=["device"]
)

interface_down_total = Gauge(
    name="network_interface_down_total",
    documentation="Total number of down interfaces",
    labelnames=["device"]
)

acl_match_total = Gauge(
    name="network_acl_matches_total",
    documentation="ACL match count observed on network devices",
    labelnames=["device", "acl", "protocol", "target", "port"]
)


def collect_metrics():
    output_data = calling_point()
    for item in output_data:
        device_up.labels(device=item["device"]).set(1 if item["total"] > 0 else 0)
        interface_total.labels(device=item["device"]).set(item["total"])
        interface_up_total.labels(device=item["device"]).set(item["up"])
        interface_down_total.labels(device=item["device"]).set(item["down"])


def training_collect(scenario:str):
    output_data = calling_point()
    res = []
    for item in output_data:
        collect_output = extract_device_features(item)
        res.append(parse_device_observation(collect_output))
    sample = save_training_sample(scenario=scenario,network_features=extract_network_summary(res))
    print(json.dumps(sample, ensure_ascii=False, indent=2))

def main():
    # try:
    #     start_http_server(8000)
    #     logging.info("exporter activated, port 8000 has been listened")
    # except Exception as e:
    #     logging.exception("exporter failed to start: %s", e)
    #     return

    # while True:
    #     collect_metrics()
    #     time.sleep(30)
    training_collect("icmp_ping")

if __name__ == "__main__":
    main()