import re
import sqlite3
import platform
import subprocess
from config import Config as cf
from concurrent.futures import ThreadPoolExecutor


class Core:
    def __init__(self):
        pass

    def scan_network(self):
        with ThreadPoolExecutor(max_workers=50) as executor:
            for i in range(1, 255):
                ip = f"{cf.ssh_switch_range}.{i}"
                executor.submit(self.ping_ip, ip)

    def ping_ip(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", ip]
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=1)
            cf.all_switches.append(ip)
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
        
        """
        IPv4 Value
        ipv4_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ipv4_find = re.findall(ipv4_pattern, switch)
        result.update({"sw_ip" : ipv4_find[0]})
        """

        # Switch Name
        deviveID_pattern = r".*Device ID:.*"
        deviveID_find = re.findall(deviveID_pattern, switch)[0]
        replacement = {"Device ID: ": "", cf.domain: ""}
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
            part_one = f"{self.__set_number()} - {cf.hostname}: {sw_data["ports"][0]}"
            print(
                f"{part_one:<70} ----> {sw_data["device"]}: {sw_data["ports"][1]}")

    def find_hostname(self, text):
        host_line = None
        for line in text.splitlines():
            if re.search(r"uptime\s+is", line, re.IGNORECASE):
                host_line = line.strip()

        host_line = host_line.split(" ")
        cf.hostname = host_line[0]

    def __set_number(self):
        cf.counter += 1
        result = cf.counter
        if result > 0 and result < 10:
            result = f"00{result}"
        elif result >= 10 and result < 100:
            result = f"0{result}"
        return result


class SQLite_Database:
    conn = None
    cursor = None

    def __init__(self):
        self.conn = sqlite3.connect("app_data.db")
        self.cursor = self.conn.cursor()

    def commit(self):
        self.conn.commit()
        self.conn.close()

    def create_tables(self):
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS admin_data (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL,
                                password TEXT NOT NULL,
                                secret TEXT,
                                domain TEXT,
                                ip_range TEXT,
                                subnet TEXT,
                                csv_name TEXT)
                            """)
