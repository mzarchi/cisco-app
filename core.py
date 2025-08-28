from config import Config
from datetime import datetime
from encrypt import Encryption
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor

import os
import re
import sys
import time
import getpass
import sqlite3
import platform
import subprocess


"""
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  ██████   ██████           █████    █████                   █████                 |
| ░░██████ ██████           ░░███    ░░███                   ░░███                  |
|  ░███░█████░███   ██████  ███████   ░███████    ██████   ███████   █████          | 
|  ░███░░███ ░███  ███░░███░░░███░    ░███░░███  ███░░███ ███░░███  ███░░           | 
|  ░███ ░░░  ░███ ░███████   ░███     ░███ ░███ ░███ ░███░███ ░███ ░░█████          | 
|  ░███      ░███ ░███░░░    ░███ ███ ░███ ░███ ░███ ░███░███ ░███  ░░░░███         |
|  █████     █████░░██████   ░░█████  ████ █████░░██████ ░░████████ ██████          |
| ░░░░░     ░░░░░  ░░░░░░     ░░░░░  ░░░░ ░░░░░  ░░░░░░   ░░░░░░░░ ░░░░░░           |
|                                                                                   |
+-----------------------------------------------------------------------------------+

"""


class Core:
    def __init__(self):
        pass

    def scan_network(self):
        with ThreadPoolExecutor(max_workers=50) as executor:
            for i in range(1, 255):
                ip = f"{Config.ssh_switch_range}.{i}"
                executor.submit(self.ping_ip, ip)

    def ping_ip(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=1)
            Config.all_switches.append(ip)
        except subprocess.TimeoutExpired:
            pass

    def read_file(self, dir: str, file: str):
        content = None
        with open(f"{dir}/{file}", "r", encoding="utf-8") as file:
            content = file.read()

        return content

    def manage_content(self, content: str):
        content = content.split("-------------------------")
        del content[0]
        return content

    def switch_data(self, switch: list):
        result = {}

        # IPv4 Value
        # ipv4_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        # ipv4_find = re.findall(ipv4_pattern, switch)
        # result.update({"sw_ip" : ipv4_find[0]})

        # Switch Name
        deviveID_pattern = r".*Device ID:.*"
        deviveID_find = re.findall(deviveID_pattern, switch)[0]
        replacement = {"Device ID: ": "", Config.domain: ""}
        for i in replacement.keys():
            deviveID_find = deviveID_find.replace(i, replacement[i])
        result.update({"device": deviveID_find})

        # Switch Port Details
        port_pattern = r".*Interface:.*"
        port_find = re.findall(port_pattern, switch)[0]
        port_find = port_find.split(",")
        port_list = []
        for i in port_find:
            port = i.split(":")
            port[1] = port[1].replace(" ", "")
            port_list.append(port[1])
        result.update({"ports": port_list})

        return result

    def find_hostname(self, text):
        host_line = None
        for line in text.splitlines():
            if re.search(r"uptime\s+is", line, re.IGNORECASE):
                host_line = line.strip()

        host_line = host_line.split(" ")
        Config.hostname = host_line[0]

    def __set_number(self):
        Config.counter += 1
        result = Config.counter
        if result > 0 and result < 10:
            result = f"00{result}"
        elif result >= 10 and result < 100:
            result = f"0{result}"
        return result

    def get_current_text(self, prompt, text=True):
        while True:
            if text:
                value = input(prompt).strip()
            else:
                value = getpass.getpass(prompt).strip()

            if value:
                return value
            print("Insert a character!")

    def show_banner(self):
        print(Config.banner)
        message = "Developer: github/mzarchi, version: 0.1 (202808)\n"
        message += "Repository: https://github.com/mzarchi/cisco-app\n"
        message += "Me at Twitter, Telegram and Instagram: @mhzarchi\n"
        message += "I always live in the depths of the Internet ❤️"
        for c in message:
            print(c, end='', flush=True)
            time.sleep(0.1)

    def show_menu(self):
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t0- App Settings (Edit all app settings)\n"
        message += "\t1- Switch Scan (Get list of your switches)\n"
        message += "\t2- Switches Link (Get uplink of your switches)\n"
        message += "\t3- IP Scan (Get list of your IP Address in your switch)\n"
        message += "\te- Exit\nPlease insert option number: "
        return message

    def case2_handler(self):
        cf = Config()
        db = App_DB()
        self.scan_network()
        result = ""
        switches = cf.all_switches

        # Put there for use two lines
        dt = self.get_datetime()

        for i, ip in enumerate(switches):
            connect = None
            auth_index = 0
            while True:
                try:
                    cisco_switch = {
                        'device_type': 'cisco_ios',
                        'host': ip,
                        'username': cf.auth_dict[auth_index]['username'],
                        'password': cf.auth_dict[auth_index]['password'],
                        'secret': cf.auth_dict[auth_index]['secret'],
                    }

                    connect = ConnectHandler(**cisco_switch)
                    connect.enable()
                    break

                except Exception as e:
                    if auth_index < len(cf.auth_dict):
                        auth_index += 1
                        continue
                    else:
                        break

            if connect != None:
                try:
                    version_data = connect.send_command("show version")
                    self.find_hostname(version_data)
                    content = connect.send_command("show cdp neighbors detail")
                    sw_text = self.manage_content(content)

                    # def write_result
                    wr_result = ""
                    for i in range(0, len(sw_text)):
                        sw_data = self.switch_data(sw_text[i])
                        part_one = f"{self.__set_number()} - {Config.hostname+":":<30} {sw_data["ports"][0]:<25}"
                        part_two = f"{sw_data["device"]+":":<30} {sw_data["ports"][1]:<25}"
                        link = f"{Config.hostname}-{sw_data["ports"][0]}|{sw_data["device"]}-{sw_data["ports"][1]}"
                        msl_dt = f"{dt['date']}-{dt['time']}"
                        update = db.manage_switch_link(link, msl_dt)

                        part_three = "Insert (New!)"
                        if update:
                            part_three = "Update"

                        print(f"{part_one} ----> {part_two} {part_three}")
                        wr_result += f"{part_one} ----> {part_two} {part_three}\n"

                    result += wr_result

                except Exception as e:
                    print(f"- Error in {ip}: {e}")
                    continue

        with open(f"{cf.data_dir}Switch-Links_{dt['date']}-{dt['time']}.txt", "a") as file:
            file.write(result)

        Config.counter = 0
        input("Task finished! press Enter to continue ..")
        os.system('cls')

    def get_datetime(self):
        result = {}
        now = datetime.now()
        result.update({"date": now.strftime("%Y%m%d")})
        result.update({"time": now.strftime("%H%M%S")})
        return result

    def ter_cls(self):
        os.system('cls')

    def app_settings_handler(self):
        ab = App_DB()
        en = Encryption()
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t1- Edit App Settings\n"
        message += "\t2- Add/Edit/Remove SSH user login\n"
        message += "\te- Exit from Settings\nPlease insert option number: "

        while True:  # ID: ash_w1
            case_number = input(message)

            if case_number == "e":
                break

            match case_number:  # ID: ash_m1
                case "1":
                    pass

                case "2":
                    self.ter_cls()
                    c2_message = "Please select one of the options below:\n"
                    c2_message += "\t1- Add Admin\n"
                    c2_message += "\t2- Edit Admin\n"
                    c2_message += "\t3- Show Admin\n"
                    c2_message += "\t4- Remove Admin\n"
                    c2_message += "\te- Exit\nPlease insert option number: "
                    while True:  # ID: ash_w2
                        c2_case_number = input(c2_message)
                        if c2_case_number == "e":
                            break

                        match c2_case_number:  # ID: ash_m2
                            case "1":
                                self.ter_cls()
                                user_data = {}
                                username = self.get_current_text(
                                    "Please inser your username: ")
                                password = self.get_current_text(
                                    "Please inser your password: ", False)
                                secret = self.get_current_text(
                                    "Please inser your secret: ", False)
                                tag = self.get_current_text(
                                    "Please inser admin tag: ")
                                user_data.update({
                                    "username": username,
                                    "password": password,
                                    "secret": secret,
                                    "tag": tag
                                })
                                ab.set_admin_data(user_data)

                                input(
                                    "User Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "3":
                                self.ter_cls()
                                rows = ab.get_admin_data()
                                for row in rows:
                                    print(
                                        f"id:{row[0]} - Username: {en.decode(row[1])}, Tag: {en.decode(row[4])}")
                                input("Press enter to back ..")
                                self.ter_cls()
                                continue

    def first_start_app(self):
        db = App_DB()
        user_data = {}
        username = self.get_current_text("Please inser your username: ")
        user_data.update({'username': username})
        password = self.get_current_text("Please inser your password: ", False)
        user_data.update({'password': password})
        secret = self.get_current_text("Please inser your secret: ", False)
        user_data.update({'secret': password if secret == '' else secret})
        domain = self.get_current_text("Please inser your domain: ")
        user_data.update({'domain': domain})
        sw_core = self.get_current_text("Please inser your SW-Core IP: ")
        user_data.update({'sw_core': sw_core})
        subnet = self.get_current_text("Please inser your IP subnet: ")
        user_data.update({'subnet': subnet})
        csv_name = self.get_current_text("Please inser your CSV name: ")
        user_data.update({'csv_name': csv_name})

        # db.insert_user_data(user_data)
        self.ter_cls()


"""
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  ██████████              █████              █████                                 |
| ░░███░░░░███            ░░███              ░░███                                  |
|  ░███   ░░███  ██████   ███████    ██████   ░███████   ██████    █████   ██████   |
|  ░███    ░███ ░░░░░███ ░░░███░    ░░░░░███  ░███░░███ ░░░░░███  ███░░   ███░░███  |
|  ░███    ░███  ███████   ░███      ███████  ░███ ░███  ███████ ░░█████ ░███████   |
|  ░███    ███  ███░░███   ░███ ███ ███░░███  ░███ ░███ ███░░███  ░░░░███░███░░░    |
|  ██████████  ░░████████  ░░█████ ░░████████ ████████ ░░████████ ██████ ░░██████   |
| ░░░░░░░░░░    ░░░░░░░░    ░░░░░   ░░░░░░░░ ░░░░░░░░   ░░░░░░░░ ░░░░░░   ░░░░░░    |
|                                                                                   |
+-----------------------------------------------------------------------------------+
"""


class App_DB:
    conn = None
    cursor = None

    def __init__(self):
        try:
            self.create_tables()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-__init__: {e}")
            sys.exit(1)

    def __open(self):
        try:
            cd = Config()
            self.conn = sqlite3.connect(cd.db_dir)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-__open: {e}")
            sys.exit(1)

    def __close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-__close: {e}")
            sys.exit(1)

    def create_tables(self):
        try:
            self.__open()
            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS app_settings (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    domain TEXT,
                                    sw_core TEXT,
                                    subnet TEXT,
                                    password TEXT,
                                    hint TEXT)
                                """)

            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS admin_data (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    username TEXT NOT NULL,
                                    password TEXT NOT NULL,
                                    secret TEXT,
                                    tag TEXT NOT NULL)
                                """)

            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS switch_links (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    link TEXT NOT NULL,
                                    insert_date TEXT NOT NULL,
                                    update_date TEXT NOT NULL)
                                """)

            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-create_tables: {e}")
            sys.exit(1)

    def count_user(self):
        try:
            self.__open()
            result = self.cursor.execute("SELECT * FROM admin_data")
            result = self.cursor.fetchall()
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-count_user: {e}")
            sys.exit(1)

        if len(result) <= 0:
            return False
        else:
            return True

    def insert_user_data(self, data):
        try:
            en = Encryption()
            self.__open()
            self.cursor.execute(
                """INSERT INTO admin_data (
                        username,
                        password,
                        secret,
                        domain,
                        sw_core,
                        subnet,
                        csv_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                    en.encode(data['username']),
                    en.encode(data['password']),
                    en.encode(data['secret']),
                    en.encode(data['domain']),
                    en.encode(data['sw_core']),
                    en.encode(data['subnet']),
                    en.encode(data['csv_name'])
                ))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_user_data: {e}")
            sys.exit(1)

    def insert_switch_link(self, link, datetime):
        try:
            self.cursor.execute(
                "INSERT INTO switch_links (link, insert_date, update_date) VALUES (?, ?, ?)", (link, datetime, datetime))
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_switch_link: {e}")
            sys.exit(1)

    def manage_switch_link(self, link, datetime):
        update = False
        try:
            self.__open()
            self.cursor.execute(
                "SELECT * FROM switch_links WHERE link = ?", (link,))

            row = self.cursor.fetchone()
            if row:
                self.cursor.execute(
                    "UPDATE switch_links SET update_date = ? WHERE link = ?", (datetime, link))
                update = True
            else:
                self.insert_switch_link(link, datetime)

            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-manage_switch_link: {e}")
            sys.exit(1)

        return update

    def set_admin_data(self, data):
        try:
            en = Encryption()
            self.__open()
            self.cursor.execute(
                """INSERT INTO admin_data (
                        username,
                        password,
                        secret,
                        tag
                    ) VALUES (?, ?, ?, ?)""", (
                    en.encode(data['username']),
                    en.encode(data['password']),
                    en.encode(data['secret']),
                    en.encode(data['tag'])
                ))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-set_admin_data: {e}")
            sys.exit(1)

    def get_admin_data(self):
        self.__open()
        try:
            self.cursor.execute("SELECT * FROM admin_data")
            rows = self.cursor.fetchall()
            self.__close()
            return rows
        except Exception as e:
            print(f"- F-core, C-App_DB, D-get_admin_data: {e}")
            sys.exit(1)
