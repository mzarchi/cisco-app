from config import Config
from database import Database
from core import Core
from PeriodicWorker import PeriodicWorker
from decorators import method_logger, lg

import ctypes
import time


ctypes.windll.kernel32.SetConsoleTitleW("CiscoApp vG132-2608")

cf = Config()
db = Database()
cr = Core()
switch_ips_worker_interval = db.get_app_variables()[1]
cr.show_banner()

time.sleep(2)
db.set_dict_admin_data()
db.set_dict_ipsubnet_data()
cr.scan_network()
ip_refresh_worker = PeriodicWorker(task=cr.switch_ips_worker, interval=int(switch_ips_worker_interval), run_immediately=True)
ip_refresh_worker.start()

switch = 0
while True:
    switch = input(cr.show_menu())
    match switch:
        case "0":
            cr.app_settings_handler()

        case "1":
            cr.case_ip_scanner()

        case "2":
            cr.case_switch_scan()

        case "3":
            cr.case_switch_link()

        case "4":
            cr.case_switch_ips()

        case "5":
            cr.case_switch_ips(dns_mode=True)

        case "6":
            cr.case_config_manager()

        case "7":
            cr.case_access_list_manager()

        case "8":
            cr.coreGetSwitchesBackup()

        case "s":
            cr.coreSearchSwitchesIPsDatabase()

        case "c":
            cr.coreCreateExportCsvFile()

        case "r":
            cr.coreRunSqlQuery()

        case "e":
            cr.ter_cls()
            break

'''
pyinstaller --onefile --icon=icon/cisco-app.ico --version-file="version_info.txt" --name=Cisco-App_vG132-2608 main.py
git rev-list --count HEAD
'''
