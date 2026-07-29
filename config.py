import os
import sys
import getpass


class Config:
    counter = 0
    hostname = None
    user = ""
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
    mk = [None] * 16
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
                                                              ░░░░░     ░░░░░"""

    def __init__(self):
        self.create_db_dir()
        pass

    def create_db_dir(self):
        user = getpass.getuser()
        #user = "Zarchi-PC"
        self.user = user
        db_dirs = f"C:/Users/{user}/AppData/Local/ca_data/"
        os.makedirs(db_dirs, exist_ok=True)
        self.db_dir = f"{db_dirs}app_data.db"

        self.mk[0] = self.data_dir = f"C:/Users/{user}/Desktop/CA-Data/"
        self.mk[1] = self.backup_dir = f"{self.data_dir}Backup/"
        self.mk[2] = self.config_dir = f"{self.data_dir}Configs/"
        self.mk[3] = self.logs_dir = f"{self.data_dir}ConfigsLogs/"
        self.mk[4] = self.ips_dir = f"{self.data_dir}SwitchesIPs/"
        self.mk[5] = self.vlans_dir = f"{self.data_dir}SwitchVlans/"
        self.mk[6] = self.scanner_dir = f"{self.data_dir}IPScanner/"
        self.mk[7] = self.systemlog_dir = f"{self.data_dir}SystemLog/"
        self.mk[8] = self.switchcdp_dir = f"{self.data_dir}SwitchCDP/"
        self.mk[9] = self.switchlist_dir = f"{self.data_dir}SwitchList/"
        self.mk[10] = self.superputty_dir = f"{self.data_dir}SupperPutty/"
        self.mk[11] = self.recordDNS_dir = f"{self.data_dir}RecordDNS/"
        self.mk[12] = self.switchlinks_dir = f"{self.data_dir}SwitchLinks/"
        self.mk[13] = self.version_dir = f"{self.data_dir}SwitchesVersions/"
        self.mk[14] = self.interface_dir = f"{self.data_dir}SwitchesInterfaces/"
        self.mk[15] = self.switchconfig_dir = f"{self.data_dir}SwitchesConfigs/"

        for i in self.mk:
            os.makedirs(i, exist_ok=True)
