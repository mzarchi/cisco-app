from config import Config
from database import Database
from core import Core
from PeriodicWorker import PeriodicWorker
from datetime import datetime

import ctypes
import msvcrt
import os
import threading
import time


ctypes.windll.kernel32.SetConsoleTitleW("CiscoApp vG173-2608")


startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

app_state = {
    "last_worker_run": startup_time,
    "worker_status": "Waiting"
}

state_lock = threading.Lock()


def get_worker_state():
    with state_lock:
        return (
            app_state["last_worker_run"],
            app_state["worker_status"]
        )


def run_switch_ips_worker():
    with state_lock:
        app_state["worker_status"] = "Running"

    try:
        cr.switch_ips_worker()

    except Exception as error:
        with state_lock:
            app_state["worker_status"] = f"Error: {error}"

    else:
        with state_lock:
            app_state["last_worker_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app_state["worker_status"] = "Completed"


def clear_console():
    os.system("cls")


def get_menu_input():
    command = ""
    last_refresh_time = 0

    while True:
        current_time = time.monotonic()

        if current_time - last_refresh_time >= 10:
            clear_console()

            last_worker_run, worker_status = get_worker_state()

            print(
                cr.show_menu(
                    last_worker_run=last_worker_run,
                    worker_status=worker_status
                ),
                end=""
            )

            print(command, end="", flush=True)

            last_refresh_time = current_time

        if msvcrt.kbhit():
            key = msvcrt.getwch()

            if key == "\r":
                print()
                return command.strip()

            if key == "\b":
                if command:
                    command = command[:-1]

            elif key == "\x03":
                continue

            elif key.isprintable():
                command += key

            clear_console()

            last_worker_run, worker_status = get_worker_state()

            print(
                cr.show_menu(
                    last_worker_run=last_worker_run,
                    worker_status=worker_status
                ),
                end=""
            )

            print(command, end="", flush=True)

        time.sleep(0.05)


cf = Config()
db = Database()
cr = Core()

switch_ips_worker_interval = db.get_app_variables()[1]

cr.show_banner()

time.sleep(2)

db.set_dict_admin_data()
db.set_dict_ipsubnet_data()
cr.scan_network()


ip_refresh_worker = PeriodicWorker(
    task=run_switch_ips_worker,
    interval=int(switch_ips_worker_interval),
    run_immediately=True
)

ip_refresh_worker.start()


while True:
    switch = get_menu_input()

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
pyinstaller --onefile --icon=icon/cisco-app.ico --version-file="version_info.txt" --name=Cisco-App_vG173-2608 main.py
git rev-list --count HEAD
'''