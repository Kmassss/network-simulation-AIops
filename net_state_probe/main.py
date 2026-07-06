from netmiko import ConnectHandler
import logging
from pathlib import Path
from datetime import datetime
import os,yaml,re
from collector import connect_device,config_load, collect_interface_info
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig( #日志定义
    filename=datetime.now().strftime("log/collector_%Y%m%d_.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
    encoding="utf-8"
)


def main():

    def work_flow(device={}):       
        connection = None
        try:
            logging.info("connection target: %s", device['name'])   
            target = device.pop('name') #剔除多余参数
            connection = connect_device(device)
            output = collect_interface_info(connection, "interface") #执行命令函数并获得结果后补充必要信息
            output.update({"device": target, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            with open("output/interface_output_{}.txt".format(datetime.now().strftime("%Y-%m-%d")), "a", encoding="utf-8") as f:
                f.write(yaml.dump(output) + "\n") #将输出信息保存本地


        except Exception as e:
            logging.exception("collect failure: %s", e)

        finally:
            if connection:
                connection.disconnect()
                logging.info("disconnected")
        
    config = config_load(path = "config/deviceConf.yaml")
    with ThreadPoolExecutor(max_workers=len(config)) as executor:
        threads=[executor.submit(work_flow, device)
                for device in config
                ]
        for thread in as_completed(threads):
            res = thread.result()


if __name__ == "__main__":
    main()