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

    if switch == "e":
        cr.ter_cls()
        break

    else:
        match switch:
            case "0":
                cr.app_settings_handler()

            case "1":
                cr.case1_handler()

            case "2":
                cr.case2_handler()

            case "3":
                cr.case3_handler()
                
            case "3":
                cr.coreCaseFourHandler()

print("Good bye ツ")
time.sleep(2)

# pyinstaller --onefile --icon=icon/cisco-app.ico --name=Cisco-App main.py

