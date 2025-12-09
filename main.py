from config import Config
from core import Core, App_DB

import time

cf = Config()
db = App_DB()
cr = Core()

cr.log("main[]: Start app!", nl=True)
cr.log("core[]:Core{}:show_banner()")
cr.show_banner()
time.sleep(2)
cr.log("core[]:App_DB{}:set_dict_admin_data()")
db.set_dict_admin_data()
cr.log("core[]:App_DB{}:set_dict_ipsubnet_data()")
db.set_dict_ipsubnet_data()
switch = 0
while True:
    cr.log("main[]:while:switch:show_menu()")
    switch = input(cr.show_menu())
    cr.log("main[]:while:switch:input({switch})")
    match switch:
        case "0":
            # App Settings (Edit all app settings)
            cr.log("main[]:while:switch:case-0:app_settings_handler()")
            cr.app_settings_handler()

        case "1":
            ip_range = input("Insert your ip: ")
            cr.log("main[]:while:switch:case-1:case_ip_scanner()")
            cr.case_ip_scanner(ip_range)

        case "2":
            # Switch Scan (Get list of your switches) c1
            cr.log("main[]:while:switch:case-2:case_switch_scan()")
            cr.case_switch_scan()

        case "3":
            # Switches Link (Get uplink of your switches) c2
            cr.log("main[]:while:switch:case-3:case_switch_link()")
            cr.case_switch_link()

        case "4":
            # Swtiches IPs (Get list of your IP Address in your switch) c3
            cr.log("main[]:while:switch:case-4:case_switch_ips()")
            cr.case_switch_ips()

        case "5":
            # Switch Config Manager c4
            cr.log("main[]:while:switch:case-5:case_config_manager()")
            cr.case_config_manager()

        case "c":
            # Get CSV from database
            cr.log("main[]:while:switch:case-c:coreCreateExportCsvFile()")
            cr.coreCreateExportCsvFile()

        case "e":
            cr.log("main[]:while:switch:case-e:ter_cls()")
            cr.ter_cls()
            break

# pyinstaller --onefile --icon=icon/cisco-app.ico --name=Cisco-App main.py
