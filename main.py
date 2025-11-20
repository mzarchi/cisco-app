from config import Config
from core import Core, App_DB

import time

cf = Config()
db = App_DB()
cr = Core()

cr.show_banner()
time.sleep(2)
db.set_dict_admin_data()
db.set_dict_ipsubnet_data()
switch = 0
while True:
    switch = input(cr.show_menu())
    match switch:
        case "0":
            # App Settings (Edit all app settings)
            cr.app_settings_handler()

        case "1":
            ip_range = input("Insert your ip: ")
            cr.case_ip_scanner(ip_range)

        case "2":
            # Switch Scan (Get list of your switches) c1
            cr.case_switch_scan()

        case "3":
            # Switches Link (Get uplink of your switches) c2
            cr.case_switch_link()

        case "4":
            # Swtiches IPs (Get list of your IP Address in your switch) c3
            cr.case_switch_ips()

        case "5":
            # Switch Config Manager c4
            cr.case_config_manager()

        case "c":
            # Get CSV from database
            cr.coreCreateExportCsvFile()

        case "e":
            cr.ter_cls()
            break

# pyinstaller --onefile --icon=icon/cisco-app.ico --name=Cisco-App main.py
