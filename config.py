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
    root_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
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
    mk = []
    renew_all_switches = 1
    renew_all_switches_interval = 5
    interval_changed_flag = False

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
        #user = getpass.getuser()
        user = "Zarchi-PC"
        self.user = user
        db_dirs = f"C:/Users/{user}/AppData/Local/ca_data/"
        os.makedirs(db_dirs, exist_ok=True)
        self.db_dir = f"{db_dirs}app_data.db"

        
        self.data_dir = f"C:/Users/{user}/Desktop/CA-Data/"
        self.switchconfig_dir = f"{self.data_dir}SwitchesConfigs/"
        self.interface_dir = f"{self.data_dir}SwitchesInterfaces/"
        self.version_dir = f"{self.data_dir}SwitchesVersions/"
        self.switchlinks_dir = f"{self.data_dir}SwitchLinks/"
        self.showDefResult = f"{self.data_dir}ShowDefResult/"
        self.superputty_dir = f"{self.data_dir}SupperPutty/"
        self.switchlist_dir = f"{self.data_dir}SwitchList/"
        self.debug_result = f"{self.data_dir}DebugResult/"
        self.systemlog_dir = f"{self.data_dir}SystemLog/"
        self.recordDNS_dir = f"{self.data_dir}RecordDNS/"
        self.switchcdp_dir = f"{self.data_dir}SwitchCDP/"
        self.vlans_dir = f"{self.data_dir}SwitchVlans/"
        self.AccessList = f"{self.data_dir}AccessList/"
        self.scanner_dir = f"{self.data_dir}IPScanner/"
        self.logs_dir = f"{self.data_dir}ConfigsLogs/"
        self.ips_dir = f"{self.data_dir}SwitchesIPs/"
        self.config_dir = f"{self.data_dir}Configs/"
        self.backup_dir = f"{self.data_dir}Backup/"
        
        self.mk = [
            self.ips_dir,
            self.logs_dir,
            self.data_dir,
            self.vlans_dir,
            self.config_dir,
            self.AccessList,
            self.backup_dir,
            self.scanner_dir,
            self.version_dir,
            self.debug_result,
            self.switchcdp_dir,
            self.systemlog_dir,
            self.interface_dir,
            self.showDefResult,
            self.recordDNS_dir,
            self.switchlist_dir,
            self.superputty_dir,
            self.switchlinks_dir,
            self.switchconfig_dir,
        ]

        for i in self.mk:
            os.makedirs(i, exist_ok=True)
