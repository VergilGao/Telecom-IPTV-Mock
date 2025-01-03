from stbmock import stb_login
from config import read_stb_config
from os import path
import os
from storage import Storage
from argparse import ArgumentParser


def main(config_dir: str, data_dir: str) -> None:
    try:
        config_path = path.join(config_dir, "iptv.ini")
        xml_path = path.join(config_dir, "epg.xml")

        udpxy_config, stb_config = read_stb_config(config_path)

        storage = Storage(path.join(config_dir, "epg.db"))  # 数据库都存 config 里

        result = stb_login(storage, data_dir, xml_path, udpxy_config, stb_config)
        os._exit(0 if result else 1)
    except Exception as e:
        print(e)
        os._exit(1)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="/config")
    parser.add_argument("--data", type=str, default="/data")
    args = parser.parse_args()
    main(args.config, args.data)
