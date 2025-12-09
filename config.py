import os
import sys
import getpass


class Config:
    counter = 0
    hostname = None
    all_switches = []
    COMMON_PORTS = [21, 22, 23, 67, 68, 80, 443]
    db_dir = ""
    root_dir = sys.argv[0].replace("main.py", "")
    data_dir = ""
    config_dir = ""
    switchconfig_dir = ""
    interface_dir = ""
    version_dir = ""
    ips_dir = ""
    scanner_dir = ""
    superputty_dir = ""
    switchlinks_dir = ""
    switchlist_dir = ""
    switchcdp_dir = ""
    systemlog_dir = ""
    domain = ""
    ssh_switch_range = ""
    auth_dict = {}
    banner = """
   █████████   ███                                 █████████                      
  ███░░░░░███ ░░░                                 ███░░░░░███                     
 ███     ░░░  ████   █████   ██████   ██████     ░███    ░███  ████████  ████████ 
░███         ░░███  ███░░   ███░░███ ███░░███    ░███████████ ░░███░░███░░███░░███
░███          ░███ ░░█████ ░███ ░░░ ░███ ░███    ░███░░░░░███  ░███ ░███ ░███ ░███
░░███     ███ ░███  ░░░░███░███  ███░███ ░███    ░███    ░███  ░███ ░███ ░███ ░███
 ░░█████████  █████ ██████ ░░██████ ░░██████     █████   █████ ░███████  ░███████ 
  ░░░░░░░░░  ░░░░░ ░░░░░░   ░░░░░░   ░░░░░░     ░░░░░   ░░░░░  ░███░░░   ░███░░░  
                                                               ░███      ░███     
                                                               █████     █████    
                                                              ░░░░░     ░░░░░     """

    def __init__(self):
        self.create_db_dir()
        pass

    def create_db_dir(self):
        user = getpass.getuser()
        db_dirs = f"C:/Users/{user}/AppData/Local/ca_data/"
        os.makedirs(db_dirs, exist_ok=True)
        self.db_dir = f"{db_dirs}app_data.db"

        mk = [None] * 12
        mk[0] = self.data_dir = f"C:/Users/{user}/Desktop/CA-Data/"
        mk[1] = self.ips_dir = f"{self.data_dir}/SwitchesIPs/"
        mk[2] = self.config_dir = f"{self.data_dir}/Configs"
        mk[3] = self.version_dir = f"{self.data_dir}/SwitchesVersions/"
        mk[4] = self.scanner_dir = f"{self.data_dir}/IPScanner/"
        mk[5] = self.interface_dir = f"{self.data_dir}/SwitchesInterfaces/"
        mk[6] = self.switchcdp_dir = f"{self.data_dir}/SwitchCDP/"
        mk[7] = self.superputty_dir = f"{self.data_dir}/SupperPutty/"
        mk[8] = self.switchlist_dir = f"{self.data_dir}/SwitchList/"
        mk[9] = self.switchlinks_dir = f"{self.data_dir}/SwitchLinks/"
        mk[10] = self.switchconfig_dir = f"{self.data_dir}/SwitchesConfigs/"
        mk[11] = self.systemlog_dir = f"{self.data_dir}/SystemLog/"

        for i in mk:
            os.makedirs(i, exist_ok=True)
