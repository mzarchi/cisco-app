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
import ipaddress
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
        ip_subnet = Config.ssh_switch_range
        network = ipaddress.ip_network(ip_subnet, strict=False)

        def ping(ip):
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", ip]
            try:
                result = subprocess.run(command, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, timeout=1)
                if result.returncode == 0:
                    return ip
            except subprocess.TimeoutExpired:
                return None

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(ping, str(host))
                       for host in network.hosts()]
            for future in futures:
                result = future.result()
                if result:
                    Config.all_switches.append(result)

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
        return host_line[0]

    def find_model(self, text):
        model_line = None
        for line in text.splitlines():
            if re.search(r'Model Number', line, re.IGNORECASE):
                model_line = line.strip()

        model_line = model_line.split(":")
        result = model_line[1].replace(" ", "")
        return result

    def find_mac(self, text):
        mac_line = None
        for line in text.splitlines():
            if re.search(r'Base Ethernet MAC Address', line, re.IGNORECASE):
                mac_line = line.strip()
                mac_line = re.search(
                    r'([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5})', mac_line)

        return mac_line.group(0)

    def get_uptime(self, text):
        uptime = {"years": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0}

        for line in text.splitlines():
            if re.search(r"uptime\s+is", line, re.IGNORECASE):
                uptime_line = line.strip()
                pattern = r"(\d+)\s+(year|years|week|weeks|day|days|hour|hours|minute|minutes)"
                matches = re.findall(pattern, uptime_line)

                for value, unit in matches:
                    value = int(value)
                    if unit.startswith("year"):
                        uptime["years"] = value
                    elif unit.startswith("week"):
                        uptime["weeks"] = value
                    elif unit.startswith("day"):
                        uptime["days"] = value
                    elif unit.startswith("hour"):
                        uptime["hours"] = value
                    elif unit.startswith("minute"):
                        uptime["minutes"] = value

                all_days = (uptime['years'] * 365) + \
                    (uptime['weeks'] * 7) + uptime['days']
                return all_days, uptime['hours'], uptime['minutes']

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
        message = "Developer: github/mzarchi, version: 0.1 (202509)\n"
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
        message += "\t1- Add/Remove SSH data\n"
        message += "\t2- Add/Remove SSH user login\n"
        message += "\te- Exit from Settings\nPlease insert option number: "

        while True:  # ID: ash_w1
            case_number = input(message)

            if case_number == "e":
                self.ter_cls()
                break

            match case_number:  # ID: ash_m1
                case "1":
                    self.ter_cls()
                    c1_message = "Please select one of the options below:\n"
                    c1_message += "\t1- Add SSH Data\n"
                    c1_message += "\t2- Show SSH Data\n"
                    c1_message += "\t3- Remove SSH Data\n"
                    c1_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        c1_case_number = input(c1_message)
                        if c1_case_number == "e":
                            self.ter_cls()
                            break

                        match c1_case_number:
                            case "1":
                                self.ter_cls()
                                ipsubnet_data = {}
                                ip_subnet = self.get_current_text(
                                    "Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                domain = self.get_current_text(
                                    "Please enter domain: ")

                                ipsubnet_data.update({
                                    "ip_subnet": ip_subnet,
                                    "domain": domain
                                })

                                ab.set_ipsubnet_data(ipsubnet_data)
                                input(
                                    "Data Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.ter_cls()
                                ip_subnet = ab.set_dict_ipsubnet_data()

                                for key, value in ip_subnet.items():
                                    print(
                                        f"{key+1:<3} - IP: {value['ip_subnet']:<18} Domain: {value['domain']}")

                                input("\nPress any key to return ...")
                                continue

                            case "3":
                                self.ter_cls()
                                ip_subnet = self.get_current_text(
                                    "Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                ab.del_ipsubnet_data(ip_subnet)

                                input("\nPress any key to return ...")
                                continue

                case "2":
                    self.ter_cls()
                    c2_message = "Please select one of the options below:\n"
                    c2_message += "\t1- Add Admin\n"
                    c2_message += "\t2- Show Admin\n"
                    c2_message += "\t3- Remove Admin\n"
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

                            case "2":
                                self.ter_cls()
                                rows = ab.get_admin_data()
                                for i, row in enumerate(rows):
                                    print(
                                        f"id:{i+1} - Username: {en.decode(row[1])}, Tag: {en.decode(row[4])}")
                                input("Press enter to back ..")
                                self.ter_cls()
                                continue

                            case "3":
                                self.ter_cls()
                                c3_username = input(
                                    "Input username for remove: ")
                                ab.del_admin_data(en.encode(c3_username))

    def case1_handler(self):
        cf = Config()
        ad = App_DB()
        dt = self.get_datetime()
        self.scan_network()
        dt = self.get_datetime()
        counter = 1
        for ip in (Config.all_switches):
            try:
                cnt = self.switch_connect(ip)
                version_data = cnt.send_command("show version")
                self.find_hostname(version_data)
                model = self.find_model(version_data)
                sw_mac = self.find_mac(version_data)
                days, hours, minutes = self.get_uptime(version_data)
                ports, ios_version, ios_type = self.get_ios_details(
                    version_data)
                data = {
                    'ip': ip,
                    'hostname': cf.hostname,
                    'model': model,
                    'mac': sw_mac,
                    'ports': ports,
                    'ios_version': ios_version,
                    'ios_type': ios_type,
                    'insert_date': f"{dt['date']} {dt['time']}",
                    'update_date': f"{dt['date']} {dt['time']}"
                }
                update = ad.manage_switch_data(data)
                update_msg = "update" if update else "insert (New!)"
                uptime_line = f"{counter:<3}- Hostname: {cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<3} d, {hours:<2} h, {minutes:<2} m, real-ports: {ports:<3} IOS-version: {ios_version:<15} IOS-type: {ios_type:<25} Action: {update_msg}"
                counter += 1
                # uptime_line = f"{counter:<3}- Hostname: {cf.hostname:<30} Uptime: {days:<3} d, {hours:<2} h, {minutes:<2} m"
                with open(f"{cf.data_dir}Switches-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(f"{uptime_line} \n")
                print(uptime_line)
            except Exception as e:
                # print(f"- F-core, C-Core, D-case1_handler({ip}): {e}")
                continue

        input("Press any key to exit ..")

    def get_ios_details(self, text):
        pattern = r"\*\s+\d+\s+(\d+)\s+\S+\s+(\S+)\s+(\S+)"

        match = re.search(pattern, text)
        if match:
            ports = match.group(1)        # Ports
            ios_version = match.group(2)  # SW Version
            ios_type = match.group(3)     # SW Image
            return ports, ios_version, ios_type

        else:
            return 0, 0, 0

    def switch_connect(self, ip):
        try:
            cf = Config()
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
                    return connect

                except Exception as e:
                    if auth_index < len(cf.auth_dict):
                        auth_index += 1
                        continue
                    else:
                        break
        except Exception as e:
            print(f"- F-core, C-Core, D-switch_connect: {e}")


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
                                CREATE TABLE IF NOT EXISTS ip_domain (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    ip_subnet TEXT,
                                    domain TEXT)
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

            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS switches_list (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    ip TEXT NOT NULL,
                                    hostname TEXT NOT NULL,
                                    model TEXT NOT NULL,
                                    mac TEXT NOT NULL,
                                    ports TEXT NOT NULL,
                                    ios_version TEXT NOT NULL,
                                    ios_type TEXT NOT NULL,
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

    def insert_switch_data(self, data):
        try:
            self.cursor.execute(
                """INSERT INTO switches_list (
                        ip,
                        hostname,
                        model,
                        mac,
                        ports,
                        ios_version,
                        ios_type,
                        insert_date,
                        update_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    data['ip'],
                    data['hostname'],
                    data['model'],
                    data['mac'],
                    data['ports'],
                    data['ios_version'],
                    data['ios_type'],
                    data['insert_date'],
                    data['update_date']
                ))
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_switch_data: {e}")
            sys.exit(1)

    def manage_switch_data(self, data):
        update = False
        try:
            self.__open()
            self.cursor.execute(
                "SELECT * FROM switches_list WHERE mac = ?", (data['mac'],))

            row = self.cursor.fetchone()
            if row:
                self.cursor.execute(
                    "UPDATE switches_list SET update_date = ? WHERE mac = ?", (data['update_date'], data['mac']))
                update = True
            else:
                self.insert_switch_data(data)

            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-manage_switch_link: {e}")
            sys.exit(1)

        return update

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

    def set_ipsubnet_data(self, data):
        try:
            self.__open()
            self.cursor.execute(
                "SELECT * FROM ip_domain WHERE ip_subnet = ?", (data['ip_subnet'],))
            row = self.cursor.fetchone()

            if not row:
                self.cursor.execute(
                    """INSERT INTO ip_domain (
                            ip_subnet,
                            domain
                        ) VALUES (?, ?)""", (
                        data['ip_subnet'],
                        data['domain'],
                    ))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-set_ipsubnet_data: {e}")
            sys.exit(1)

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

    def del_admin_data(self, username):
        self.__open()
        try:
            self.cursor.execute(
                "DELETE FROM admin_data WHERE username = ?", (username,))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-del_admin_data: {e}")
            sys.exit(1)

    def set_dict_admin_data(self):
        try:
            cf = Config()
            en = Encryption()
            self.__open()
            self.cursor.execute("SELECT * FROM admin_data")
            rows = self.cursor.fetchall()

            for i, row in enumerate(rows):
                cf.auth_dict.update({i: {
                    "type": en.decode(row[4]),
                    "username": en.decode(row[1]),
                    "password": en.decode(row[2]),
                    "secret": en.decode(row[3])
                }})

        except Exception as e:
            print(f"- F-core, C-App_DB, D-set_dict_admin_data: {e}")
            sys.exit(1)

    def set_dict_ipsubnet_data(self):
        try:
            self.__open()
            ip_subnet = {}
            self.cursor.execute("SELECT * FROM ip_domain")
            rows = self.cursor.fetchall()

            for i, row in enumerate(rows):
                Config.ssh_switch_range = row[1]
                Config.domain = row[2]

                ip_subnet.update({i: {
                    "ip_subnet": row[1],
                    "domain": row[2],
                }})

            return ip_subnet
        except Exception as e:
            print(f"- F-core, C-App_DB, D-set_dict_ipsubnet_data: {e}")
            sys.exit(1)

    def del_ipsubnet_data(self, ipsubnet):
        self.__open()
        try:
            self.cursor.execute(
                "DELETE FROM ip_domain WHERE ip_subnet = ?", (ipsubnet,))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-del_ipsubnet_data: {e}")
            sys.exit(1)
