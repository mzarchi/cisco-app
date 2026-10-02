import logging

logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("netmiko").setLevel(logging.CRITICAL)

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


ctypes.windll.kernel32.SetConsoleTitleW("CiscoApp vG192-2609")


startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

app_state = {"last_worker_run": startup_time, "worker_status": "Waiting"}

state_lock = threading.Lock()
state_changed = threading.Event()


def get_worker_state():
    with state_lock:
        return (app_state["last_worker_run"], app_state["worker_status"])


def run_switch_ips_worker():
    with state_lock:
        app_state["worker_status"] = "Running"
    state_changed.set()

    try:
        cr.switch_ips_worker()

    except Exception as error:
        with state_lock:
            app_state["worker_status"] = f"Error: {error}"
        state_changed.set()

    else:
        with state_lock:
            app_state["last_worker_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app_state["worker_status"] = "Completed"
        state_changed.set()


def clear_console():
    os.system("cls")


def get_menu_input():
    command = ""

    def draw():
        clear_console()
        last_worker_run, worker_status = get_worker_state()
        print(cr.show_menu(last_worker_run=last_worker_run, worker_status=worker_status), end="")
        print(command, end="", flush=True)

    draw()

    while True:
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

            draw()

        if state_changed.is_set():
            state_changed.clear()
            draw()

        time.sleep(0.05)


cf = Config()
db = Database()
cr = Core()

interval_row = db.get_app_variables()
switch_ips_worker_interval = interval_row[1] if interval_row else "240"

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


def interval_watcher():
    while True:
        if Config.interval_changed_flag:
            Config.interval_changed_flag = False
            new_interval = db.get_app_variables()[1]
            ip_refresh_worker.set_interval(int(new_interval))
        time.sleep(0.5)


interval_watcher_thread = threading.Thread(
    target=interval_watcher,
    daemon=True,
    name="IntervalWatcherThread"
)
interval_watcher_thread.start()


while True:
    switch = get_menu_input()
    switch = switch.lower()

    match switch:
        case "0":
            cr.app_settings_handler()

        case "1":
            cr.case_ip_scanner()

        case "2":
            cr.case_switch_scan()

        case "3":
            cr.switch_statuses()

        case "4":
            cr.case_switch_link()

        case "5":
            cr.case_switch_ips()

        case "6":
            cr.case_switch_ips(dns_mode=True)

        case "7":
            cr.case_config_manager()

        case "8":
            cr.case_access_list_manager()

        case "9":
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
