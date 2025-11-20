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
        self.db_dir = f"{db_dirs}app_data.db"
        self.data_dir = f"C:/Users/{user}/Desktop/CA-Data/"
        os.makedirs(db_dirs, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
