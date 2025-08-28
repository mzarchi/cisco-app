from config import Config
from core import Core, App_DB

import time

cf = Config()
ad = App_DB()
cr = Core()

# cr.show_banner()
# time.sleep(2)
ad.set_dict_admin_data()
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
                continue

            case "2":
                cr.case2_handler()

            case "3":
                continue

print("Good bye ツ")
time.sleep(2)
