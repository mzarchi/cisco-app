from concurrent.futures import ThreadPoolExecutor
from config import Config
from encrypt import Encryption

import re
import sys
import time
import getpass
import sqlite3
import platform
import subprocess


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

    def write_result(self, sw_text: list):
        for i in range(0, len(sw_text)):
            sw_data = self.switch_data(sw_text[i])
            part_one = f"{self.__set_number()} - {Config.hostname}: {sw_data["ports"][0]}"
            print(
                f"{part_one:<70} ----> {sw_data["device"]}: {sw_data["ports"][1]}")

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
        message = "Please select one of the options below:\n"
        message += "\t1- Switch Scan (Get list of your switches)\n"
        message += "\t2- IP Scan (Get list of your IP Address in your switch)\n"
        message += "\t0- Exit\nPlease insert option number: "
        return message


class App_DB:
    conn = None
    cursor = None

    def __init__(self):
        self.create_tables()

    def __open(self):
        cd = Config()
        self.conn = sqlite3.connect(cd.db_dir)
        self.cursor = self.conn.cursor()

    def __close(self):
        self.conn.commit()
        self.conn.close()

    def create_tables(self):
        self.__open()
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS admin_data (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL,
                                password TEXT NOT NULL,
                                secret TEXT,
                                domain TEXT,
                                sw_core TEXT,
                                subnet TEXT,
                                csv_name TEXT)
                            """)
        self.__close()

    def count_user(self):
        self.__open()
        result = self.cursor.execute("SELECT * FROM admin_data")
        result = self.cursor.fetchall()
        self.__close()

        if len(result) <= 0:
            return False
        else:
            return True

    def insert_user_data(self, data):
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
