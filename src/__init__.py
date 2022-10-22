import sys
from stbmock import stb_login
from config import read_stb_config
from sys import platform
from os import path, makedirs, environ
from storage import Storage

def main() -> None:
    try:
        if platform == 'win32':
            config_dir = environ['USERPROFILE']
        elif platform == 'linux':
            config_dir = environ['HOME']

        config_path = path.join(config_dir, 'iptv.ini')

        conmmon_config, stb_config = read_stb_config(config_path)
        
        if not path.exists (conmmon_config.data_dir):
            makedirs(conmmon_config.data_dir)

        storage = Storage(path.join(conmmon_config.data_dir, 'epg.db'))
        stb_login(storage,conmmon_config, stb_config)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
