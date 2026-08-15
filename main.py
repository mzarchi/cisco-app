from config import Config
from database import Database
from core import Core

import ctypes
import time

ctypes.windll.kernel32.SetConsoleTitleW("CiscoApp vG132-2608")

cf = Config()
db = Database()
cr = Core()

cr.log("main[]:main():Start-app", nl=True)
cr.log("main[]:core[]:Core{}:show_banner()")
cr.show_banner()

time.sleep(2)
cr.log("main[]:core[]:App_DB{}:set_dict_admin_data()")
db.set_dict_admin_data()
cr.log("main[]:core[]:App_DB{}:set_dict_ipsubnet_data()")
db.set_dict_ipsubnet_data()
switch = 0
while True:
    cr.log("main[]:while:switch:show_menu()")
    switch = input(cr.show_menu())
    cr.log("main[]:while:switch:input(switch)")
    match switch:
        case "0":
            # App Settings (Edit all app settings)
            cr.log("main[]:while:switch:case-0:core{}:core[]:app_settings_handler()")
            cr.app_settings_handler()

        case "1":
            ip_range = input("Insert your ip: ")
            cr.log("main[]:while:switch:case-1:core{}:core[]:case_ip_scanner()")
            cr.case_ip_scanner(ip_range)

        case "2":
            # Switch Scan (Get list of your switches)
            cr.log("main[]:while:switch:case-2:core{}:core[]:case_switch_scan()")
            cr.case_switch_scan()

        case "3":
            # Switches Link (Get uplink of your switches)
            cr.log("main[]:while:switch:case-3:core{}:core[]:case_switch_link()")
            cr.case_switch_link()

        case "4":
            # Swtiches IPs (Get list of your IP Address in your switch)
            cr.log("main[]:while:switch:case-4:core{}:core[]:case_switch_ips()")
            cr.case_switch_ips(dns_mode=False)
            
        case "5":
            # Get DNS name by IP
            cr.log("main[]:while:switch:case-5:core{}:core[]:case_switch_ips(dns_mode)")
            cr.case_switch_ips(dns_mode=True)

        case "6":
            # Switch Config Manager
            cr.log("main[]:while:switch:case-6:core{}:core[]:case_config_manager()")
            cr.case_config_manager()
        
        case "7":
            # Access-List Manager
            cr.log("main[]:while:switch:case-7:core{}:core[]:coreGetSwitchesBackup()")
            cr.case_access_list_manager()
        
        case "8":
            # Case Backup
            cr.log("main[]:while:switch:case-7:core{}:core[]:coreGetSwitchesBackup()")
            cr.coreGetSwitchesBackup()

        case "s":
            # Search in Switches IPs database
            cr.log("main[]:while:switch:case-c:core{}:core[]:coreSearchSwitchesIPsDatabase()")
            cr.coreSearchSwitchesIPsDatabase()
            
        case "c":
            # Get CSV from database
            cr.log("main[]:while:switch:case-c:core{}:core[]:coreCreateExportCsvFile()")
            cr.coreCreateExportCsvFile()
            
        case "r":
            # Run SQL query on database
            cr.log("main[]:while:switch:case-c:core{}:core[]:coreRunSqlQuery()")
            cr.coreRunSqlQuery()

        case "e":
            cr.log("main[]:while:switch:case-e:ter_cls()")
            cr.ter_cls()
            break

'''
pyinstaller --onefile --icon=icon/cisco-app.ico --version-file="version_info.txt" --name=Cisco-App_vG132-2608 main.py
git rev-list --count HEAD
'''
