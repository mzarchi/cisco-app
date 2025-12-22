from config import Config
from datetime import datetime
from encrypt import Encryption
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException
from concurrent.futures import ThreadPoolExecutor

import os
import re
import sys
import csv
import time
import json
import socket
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
    cf = Config()

    def __init__(self):
        dt = self.get_datetime()
        for row, i in enumerate(self.cf.mk):
            if row > 6:
                os.makedirs(f"{i}{dt['backup']}/", exist_ok=True)
        pass

    def log(self, message, nl=False):
        dt = self.get_datetime()
        message = ("\n" if nl else "") + f"{dt['log']} - {message} \n"

        with open(f"{self.cf.systemlog_dir}AppLog_{dt['date']}.txt", "a") as file:
            file.write(message)

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
                if result and result not in Config.all_switches:
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
        message = f"Developer: github/mzarchi, Open-Source project\n"
        message += "First-Commit: G0-2508, version: G81-2512\n"
        message += "Repository: https://github.com/mzarchi/cisco-app\n"
        message += "Me at Twitter, Telegram and Instagram: @mhzarchi\n"
        message += "I always live in the depths of the Internet ❤️"
        print(message)

    def show_menu(self):
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t0- App Settings (Edit all app settings)\n"
        message += "\t1- IP Scanner + Subnet (Get all ip by subnet)\n"
        message += "\t2- Switch Scan (Get list of your switches)\n"
        message += "\t3- Switches Link (Get uplink of your switches)\n"
        message += "\t4- Swtiches IPs (Get list of your IP Address in your switch)\n"
        message += "\t5- Switch Config Manager\n"
        message += "\t6- Get Backup from Config/Interfaces/version/CDP details of switches\n"
        message += "\tc- Get CSV from database\n"
        message += "\te- Exit\nPlease insert option number: "
        return message

    def ping_host(self, ip):
        cmd = ["ping", "-n", "1", "-w", "300", ip]
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0

    def check_ports(self, ip):
        
        open_ports = []
        for port in self.cf.COMMON_PORTS:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
                s.close()
            except:
                pass
        return open_ports

    def case_ip_scanner(self, base_ip_subnet):
        dt = self.get_datetime()
        result_text = ""
        network = ipaddress.ip_network(f"{base_ip_subnet}", strict=False)
        print(f"Check {self.cf.COMMON_PORTS} on {base_ip_subnet}")
        message = ""
        for ip in network.hosts():
            try:
                ip = str(ip)
                alive = self.ping_host(ip)
                if alive:
                    message = ""
                    ports = self.check_ports(ip)
                    if ports:
                        message = f"[+] {ip:<15} alive | open ports: {ports}"
                        print(message)
                    else:
                        message = f"[+] {ip:<15} alive |"
                        print(message)
                    result_text += f"{message}\n"
                else:
                    print(f"[-] {ip:<15} down")
            except KeyboardInterrupt:
                message += "\nTask Killed!\n"
                self.log("core[]:core{}:case_ip_scanner():for:Task-Killed!")
                break

        self.log("core[]:core{}:case_ip_scanner():CreateFile:IP-Scanner.txt")
        with open(f"{self.cf.scanner_dir}IP-Scanner_{dt['date']}-{dt['time']}.txt", "a") as file:
            file.write(result_text)

        input(message + "Press any key to back ..")

    def case_switch_link(self):
        db = App_DB()
        self.log("core[]:core{}:case_switch_link():scan_network()")
        self.scan_network()
        result = ""
        switches = self.cf.all_switches

        # Put there for use two lines
        self.log("core[]:core{}:case_switch_link():get_datetime()")
        dt = self.get_datetime()

        for i, ip in enumerate(switches):
            connect = None
            auth_index = 0
            while True:
                try:
                    cisco_switch = {
                        'device_type': 'cisco_ios',
                        'host': ip,
                        'username': self.cf.auth_dict[auth_index]['username'],
                        'password': self.cf.auth_dict[auth_index]['password'],
                        'secret': self.cf.auth_dict[auth_index]['secret'],
                    }

                    self.log(f"core[]:core{{}}:case_switch_link():for:while:ConnectHandler({ip})")
                    connect = ConnectHandler(**cisco_switch)
                    connect.enable()
                    break

                except Exception as e:
                    if auth_index < len(self.cf.auth_dict):
                        auth_index += 1
                        continue
                    else:
                        break

            if connect != None:
                try:
                    self.log("core[]:core{}:case_switch_link():for:while:if:send_command(show version)")
                    version_data = connect.send_command("show version")
                    self.log("core[]:core{}:case_switch_link():for:while:if:find_hostname()")
                    hostname = self.find_hostname(version_data)

                    self.log("core[]:core{}:case_switch_link():for:while:if:CreateFile:version.txt")
                    with open(f"{self.cf.version_dir}{hostname}-version_{dt['date']}-{dt['time']}.txt", "a") as file:
                        file.write(version_data)
                    self.log("core[]:core{}:case_switch_link():for:while:if:send_command(show cdp neighbors detail)")
                    content = connect.send_command("show cdp neighbors detail")
                    self.log(
                        "core[]:core{}:case_switch_link():for:while:if:manage_content()")
                    sw_text = self.manage_content(content)
                    self.log(
                        "core[]:core{}:case_switch_link():for:while:if:CreateFile:cdp.txt")
                    with open(f"{self.cf.switchcdp_dir}{hostname}-CDP_{dt['date']}-{dt['time']}.txt", "a") as file:
                        file.write(content)

                    # def write_result
                    wr_result = ""
                    for i in range(0, len(sw_text)):
                        self.log(
                            "core[]:core{}:case_switch_link():for:while:if:for:switch_data()")
                        sw_data = self.switch_data(sw_text[i])
                        part_one = f"{self.__set_number()} - {Config.hostname+":":<30} {sw_data["ports"][0]:<25}"
                        part_two = f"{sw_data["device"]+":":<30} {sw_data["ports"][1]:<25}"
                        link = f"{Config.hostname}-{sw_data["ports"][0]}|{sw_data["device"]}-{sw_data["ports"][1]}"
                        msl_dt = f"{dt['date']}-{dt['time']}"
                        self.log(
                            "core[]:core{}:case_switch_link():for:while:if:for:App_DB{}:manage_switch_link()")
                        update = db.manage_switch_link(link, msl_dt)

                        part_three = "Insert (New!)"
                        if update:
                            part_three = "Update"

                        print(f"{part_one} ----> {part_two} {part_three}")
                        wr_result += f"{part_one} ----> {part_two} {part_three}\n"

                    result += wr_result

                except Exception as e:
                    self.log(
                        f"core[]:core{{}}:case_switch_link():for:while:if:for:Error:{e}")
                    print(f"- Error in {ip}: {e}")
                    continue

        self.log("core[]:core{}:case_switch_link():for:CreateFile:Switch-Links.txt")
        with open(f"{self.cf.switchlinks_dir}Switch-Links_{dt['date']}-{dt['time']}.txt", "a") as file:
            file.write(result)

        switches.clear()
        Config.counter = 0
        Config.all_switches.clear()
        input("Task finished! press Enter to continue ..")
        os.system('cls')

    def get_datetime(self):
        result = {}
        now = datetime.now()
        result.update({"date": now.strftime("%Y%m%d")})
        result.update({"time": now.strftime("%H%M%S")})
        result.update({"log": now.strftime("%H:%M:%S")})
        result.update({"backup": now.strftime("%Y-%m-%d")})
        return result

    def ter_cls(self):
        os.system('cls')

    def app_settings_handler(self):
        self.log("core[]:core{}:app_settings_handler():Create App_DB obj")
        ab = App_DB()
        self.log("core[]:core{}:app_settings_handler():Create Encryption obj")
        en = Encryption()
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t1- Add/Remove SSH data\n"
        message += "\t2- Add/Remove SSH user login\n"
        message += "\te- Exit from Settings\nPlease insert option number: "

        while True:  # ID: ash_w1
            self.log("core[]:core{}:app_settings_handler():case_number:input()")
            case_number = input(message)

            if case_number == "e":
                self.ter_cls()
                break

            match case_number:  # ID: ash_m1
                case "1":
                    self.log("core[]:core{}:app_settings_handler():case_number-1")
                    self.ter_cls()
                    c1_message = "Please select one of the options below:\n"
                    c1_message += "\t1- Add SSH Data\n"
                    c1_message += "\t2- Show SSH Data\n"
                    c1_message += "\t3- Remove SSH Data\n"
                    c1_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        self.log(
                            "core[]:core{}:app_settings_handler():c1_case_number:input()")
                        c1_case_number = input(c1_message)
                        if c1_case_number == "e":
                            self.ter_cls()
                            break

                        match c1_case_number:
                            case "1":
                                self.log(
                                    "core[]:core{}:app_settings_handler():c1_case_number-1")
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

                                self.log(
                                    "core[]:core{}:app_settings_handler():c1_case_number-1:App_DB{}:set_ipsubnet_data()")
                                ab.set_ipsubnet_data(ipsubnet_data)
                                input(
                                    "Data Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.log(
                                    "core[]:core{}:app_settings_handler():c1_case_number-2")
                                self.ter_cls()
                                self.log(
                                    "core[]:core{}:app_settings_handler():App_DB{}:set_dict_ipsubnet_data()")
                                ip_subnet = ab.set_dict_ipsubnet_data()

                                for key, value in ip_subnet.items():
                                    print(
                                        f"{key+1:<3} - IP: {value['ip_subnet']:<18} Domain: {value['domain']}")

                                input("\nPress any key to return ...")
                                continue

                            case "3":
                                self.log(
                                    "core[]:core{}:app_settings_handler():c1_case_number-3")
                                self.ter_cls()
                                ip_subnet = self.get_current_text(
                                    "Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                self.log(
                                    "core[]:core{}:app_settings_handler():App_DB{}:del_ipsubnet_data()")
                                ab.del_ipsubnet_data(ip_subnet)

                                input("\nPress any key to return ...")
                                continue
                        self.log(
                            "core[]:core{}:app_settings_handler():App_DB{}:set_dict_ipsubnet_data()")
                        ab.set_dict_ipsubnet_data()

                case "2":
                    self.log("core[]:core{}:app_settings_handler():case_number-2")
                    self.ter_cls()
                    c2_message = "Please select one of the options below:\n"
                    c2_message += "\t1- Add Admin\n"
                    c2_message += "\t2- Show Admin\n"
                    c2_message += "\t3- Remove Admin\n"
                    c2_message += "\te- Exit\nPlease insert option number: "
                    while True:  # ID: ash_w2
                        self.log(
                            "core[]:core{}:app_settings_handler():case_number-2:c2_case_number:imput()")
                        c2_case_number = input(c2_message)
                        if c2_case_number == "e":
                            break

                        match c2_case_number:  # ID: ash_m2
                            case "1":
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-1")
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
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-1:App_DB{}:set_admin_data()")
                                ab.set_admin_data(user_data)

                                input(
                                    "User Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-2")
                                self.ter_cls()
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-2:App_DB{}:get_admin_data()")
                                rows = ab.get_admin_data()
                                for i, row in enumerate(rows):
                                    print(
                                        f"id:{i+1} - Username: {en.decode(row[1])}, Tag: {en.decode(row[4])}")
                                input("Press enter to back ..")
                                self.ter_cls()
                                continue

                            case "3":
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3")
                                self.ter_cls()
                                c3_username = input(
                                    "Input username for remove: ")
                                self.log(
                                    "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3:App_DB{}:del_admin_data()")
                                ab.del_admin_data(en.encode(c3_username))

                    self.log(
                        "core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3:App_DB{}:set_dict_admin_data()")
                    ab.set_dict_admin_data()

    def case_switch_scan(self):
        
        ad = App_DB()
        super_putty = []
        self.log("core[]:core{}:case_switch_scan():scan_network()")
        self.scan_network()
        self.log("core[]:core{}:case_switch_scan():get_datetime()")
        dt = self.get_datetime()
        counter = 1
        for ip in (Config.all_switches):
            try:
                self.log(
                    f"core[]:core{{}}:case_switch_scan():for:switch_connect({ip})")
                cnt = self.switch_connect(ip)
                self.log(
                    "core[]:core{}:case_switch_scan():for:send_command(show version)")
                version_data = cnt.send_command("show version")
                self.log("core[]:core{}:case_switch_scan():for:find_hostname()")
                self.find_hostname(version_data)
                self.log("core[]:core{}:case_switch_scan():for:find_model()")
                model = self.find_model(version_data)
                self.log("core[]:core{}:case_switch_scan():for:find_mac()")
                sw_mac = self.find_mac(version_data)
                self.log("core[]:core{}:case_switch_scan():for:get_uptime()")
                days, hours, minutes = self.get_uptime(version_data)
                self.log("core[]:core{}:case_switch_scan():for:get_ios_details()")
                ports, ios_version, ios_type = self.get_ios_details(
                    version_data)
                data = {
                    'ip': ip,
                    'hostname': self.cf.hostname,
                    'model': model,
                    'mac': sw_mac,
                    'ports': ports,
                    'ios_version': ios_version,
                    'ios_type': ios_type,
                    'insert_date': f"{dt['date']} {dt['time']}",
                    'update_date': f"{dt['date']} {dt['time']}"
                }
                self.log(
                    f"core[]:core{{}}:case_switch_scan():for:manage_switch_data({ip})")
                update = ad.manage_switch_data(data)
                update_msg = "update" if update else "insert (New!)"
                uptime_line = f"{counter:<3}- Hostname: {self.cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<3} d, {hours:<2} h, {minutes:<2} m, real-ports: {ports:<3} IOS-version: {ios_version:<15} IOS-type: {ios_type:<25} Action: {update_msg}"
                counter += 1
                # uptime_line = f"{counter:<3}- Hostname: {self.cf.hostname:<30} Uptime: {days:<3} d, {hours:<2} h, {minutes:<2} m"
                self.log(
                    f"core[]:core{{}}:case_switch_scan():for:CreateFile:Switches-List.txt")
                with open(f"{self.cf.switchlist_dir}Switches-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(f"{uptime_line} \n")

                super_putty.append(
                    f'<SessionData SessionId="{self.cf.hostname}" SessionName="{self.cf.hostname}" ImageKey="computer" Host="{ip}" Port="22" Proto="SSH" PuttySession="Default Settings" Username="" ExtraArgs="" SPSLFileName="" RemotePath="" LocalPath="" />')
                print(uptime_line)
            except Exception as e:
                # print(f"- F-core, C-Core, D-case1_handler({ip}): {e}")
                continue

        self.log(
            f"core[]:core{{}}:case_switch_scan():CreateFile:super-putty.xml")
        with open(f"{self.cf.superputty_dir}super-putty_{dt['date']}-{dt['time']}.xml", "a") as file:
            file.write('<?xml version="1.0" encoding="utf-8"?> \n')
            file.write(
                '<ArrayOfSessionData xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"> \n')
            for switch in super_putty:
                file.write(f"  {switch} \n")
            file.write('</ArrayOfSessionData> \n')

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
            
            auth_index = 0
            while True:
                try:
                    cisco_switch = {
                        'device_type': 'cisco_ios',
                        'host': ip,
                        'username': self.cf.auth_dict[auth_index]['username'],
                        'password': self.cf.auth_dict[auth_index]['password'],
                        'secret': self.cf.auth_dict[auth_index]['secret'],
                    }

                    connect = ConnectHandler(**cisco_switch)
                    connect.enable()
                    return connect

                except NetmikoTimeoutException:
                    return None
                except Exception as e:
                    if auth_index < len(self.cf.auth_dict):
                        auth_index += 1
                        continue
                    else:
                        break

        except Exception as e:
            print(f"- F-core, C-Core, D-switch_connect: {e}")

    def case_switch_ips(self):
        db = App_DB()
        counter = 1
        connect_failed = 0
        switch_ips = []
        user_special_ip = input("Enter Special Switch IP or Enter: ")
        if user_special_ip == "":
            self.scan_network()
            switch_ips = self.cf.all_switches
        else:
            switch_ips.append(user_special_ip)
            
        dt = self.get_datetime()
        ip_text_file = ""
        for hip in switch_ips:
            connect = self.switch_connect(hip)
            if connect is None:
                self.log(f"core[]:core{{}}:case_switch_ips():for:if:NoConnectivity({hip})")
                connect_failed += 1
                if connect_failed == 3:
                    self.log(f"core[]:core{{}}:case_switch_ips():for:if:if:StopConnectToSwitches")
                    print("You can't connect to switch!")
                    break
                else:
                    self.log(f"core[]:core{{}}:case_switch_ips():for:if:else:GoToNextSwitchIP")
                    continue

            self.log(f"core[]:core{{}}:case_switch_ips():for:Connectivity({hip})")
            connect_failed = 0
            self.log("core[]:core{}:case_switch_ips():for:send_command(show version)")
            version_data = connect.send_command("show version")
            self.log("core[]:core{}:case_switch_ips():for:find_model(version_data)")
            model = self.find_model(version_data)
            model_number = re.findall(r"\d{4}", model)

            self.log("core[]:core{}:case_switch_ips():for:send_command(show ip device tracking all)")
            sidta = connect.send_command("show ip device tracking all")
            if "%" in sidta:
                self.log("core[]:core{}:case_switch_ips():for:if:send_command(show ip device tracking all)")
                sidta = connect.send_command("show device-tracking database")

            pattern = re.compile(
                r"(\d+\.\d+\.\d+\.\d+)"
                r".*?"
                r"([0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2})"
                r".*?"
                r"(\S*\/\S*)"
            )

            date_time = f"{dt['date']} {dt['time']}"
            for line in sidta.splitlines():
                match = pattern.search(line)
                if match:
                    ip, mac, port = match.groups()
                    imsp = f"{ip}|{mac}|{hip}|{port}"
                    self.log("core[]:core{}:case_switch_ips():for:for:if:App_DB{}.insert_ipdata(imsp, date_time)")
                    new_imsp = db.insert_ipdata(imsp, date_time)
                    imsp_sec = "Update"
                    if new_imsp:
                        imsp_sec = "Insert (New!)"

                    line = f"{counter:<4}- IP: {ip:<18} MAC: {mac:<18} Switch: {hip:<18} Port: ({model_number[0]}) {port:<25} Action: {imsp_sec}"
                    ip_text_file += f"{line}\n"
                    print(line)
                    counter += 1
                    time.sleep(0.001)

        if connect_failed < 3:
            self.log("core[]:core{}:case_switch_ips():for:for:CreateFile:IP-List.txt")
            with open(f"{self.cf.ips_dir}IP-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                file.write(ip_text_file)
        self.cf.all_switches.clear()
        input("Press any key to exit ..")

    def case_config_manager(self):
        """ Case Draft:
            1: All
            2: One
            -----------
            1: View
            2: Set
            3: Delete
            -----------
            1: Switch
            2: Vlans
            3: Ports
              1: Access
              2: Trunk
            -----------
        """
        menu = """- : Not Active
Switches-Config:
   111: Action: View       Target: All switches
   121: Action: Set        Target: All switches -
   131: Action: Delete     Target: All switches -
  
   211: Action: View       Target: One switch (IP) -
   221: Action: Set        Target: One switch (IP) -
   231: Action: Delete     Target: One switch (IP) -

Vlans-Config:
   112: Action: View       Target: All switches
   122: Action: Set        Target: All switches -
   132: Action: Delete     Target: All switches -
  
   212: Action: View       Target: One switch (IP) -
   222: Action: Set        Target: One switch (IP) -
   232: Action: Delete     Target: One switch (IP) -

Ports-Config:
  1131: Action: View   (Access Port)    Target: All switches 
  1231: Action: Config (Access Port)    Target: All switches    -
  1331: Action: Delete (Access Port)    Target: All switches
  
  2131: Action: View   (Access Port)    Target: One switch (IP) -
  2231: Action: Config (Access Port)    Target: One switch (IP) -
  2331: Action: Delete (Access Port)    Target: One switch (IP) -
  
  1132: Action: View   (Trunk Port)     Target: All switches
  1232: Action: Config (Trunk Port)     Target: All switches    -
  1332: Action: Delete (Trunk Port)     Target: All switches
  
  2132: Action: View   (Trunk Port)     Target: One switch (IP) -
  2232: Action: Config (Trunk Port)     Target: One switch (IP) -
  2332: Action: Delete (Trunk Port)     Target: One switch (IP) -
  
json: Set json config 

Please insert option number: """

        self.ter_cls()
        while True:  # ID: ash_w1
            case_number = input(menu)

            if case_number == "e":
                self.ter_cls()
                break

            match case_number:  # ID: ash_m1
                case "json":
                    data = {
                        'switch': 'all',
                        'action': 'json',
                        'target': 'port',
                        'type': 'access',
                    }
                    self.coreManagePortConfig(data)
                    break

                case "111":
                    self.coreSwitchSecurityCheck()
                    break

                case "1131":
                    self.coreCheckPortConfig(user_type="Access", set_number=0)
                    break

                case "1231":
                    self.coreCheckPortConfig(user_type="Access", set_number=4)
                    break

                case "1132":
                    self.coreCheckPortConfig(user_type="Trunk", set_number=0)
                    break

                case "1232":
                    self.coreCheckPortConfig(user_type="Trunk", set_number=6)
                    break

                case "1331":
                    data = {
                        'switch': 'all',     # 1
                        'action': 'delete',  # 3
                        'target': 'port',    # 3
                        'type': 'access',    # 1
                    }
                    self.coreManageConfig(data)
                    break

                case "1332":
                    data = {
                        'switch': 'all',     # 1
                        'action': 'delete',  # 3
                        'target': 'port',    # 3
                        'type': 'trunk',     # 2
                    }
                    self.coreManageConfig(data)
                    break

    def coreSwitchSecurityCheck(self):
        
        self.scan_network()

        user_config = self.coreUserConfigFormatChanger()
        print("Security check code:")
        for i, line in enumerate(user_config):
            print(f"{i+1:<3}- {line}")

        print("\nSwitch list with above code:")
        all_ip = self.cf.all_switches
        for i, ip in enumerate(all_ip):
            connect = self.switch_connect(ip)
            if connect is None:
                continue

            connect = self.switch_connect(ip)
            run_config = connect.send_command("show running-config")
            switch_config = self.coreConfigFormatChanger(run_config)

            results = [f"{i}:N" for i, word in enumerate(
                user_config, start=1) if word not in switch_config]
            output = "  ".join(results)
            print(f"{ip:<18} - {output}")

        input("Task finished! press Enter to continue ..")
        os.system('cls')

    def coreUserConfigFormatChanger(self):
        
        self.scan_network()
        filename = f"{self.cf.config_dir}/Switch-Configs.txt"

        lines = []
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        output = []
        parent = None
        subs = []

        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("    "):
                subs.append(line.strip())
            else:
                if parent:
                    joined = parent + "".join("___" + s for s in subs)
                    output.append(joined)
                parent = line.strip()
                subs = []
        if parent:
            joined = parent + "".join("___" + s for s in subs)
            output.append(joined)

        output = [item for item in output if not set(item) <= {"!"}]
        return output

    def coreConfigFormatChanger(self, config):
        output = []
        parent = None
        subs = []

        for line in config.splitlines():
            line = line.rstrip()
            if not line:
                continue
            if line.startswith(" "):
                subs.append(line.strip())
            else:
                if parent:
                    joined = parent + "".join("___" + s for s in subs)
                    output.append(joined)
                parent = line.strip()
                subs = []
        if parent:
            joined = parent + "".join("___" + s for s in subs)
            output.append(joined)

        output = [item for item in output if not set(item) <= {"!"}]
        return output

    def parse_interfaces(self, switch_config):
        interfaces = {}
        for line in switch_config:
            line = line.strip()
            if not line.startswith("interface "):
                continue

            parts = line.split("___", 1)
            key = parts[0].replace("interface ", "")
            if "Vlan" not in key:
                interfaces[key] = line
        return interfaces

    def coreWriteFile(self, dir_name, contents):
        with open(dir_name, "a") as file:
            file.write(contents)

    def coreManageConfig(self, data):
        match data['target']:
            case "port":
                self.coreManagePortConfig(data)

    def coreManagePortConfig(self, data):
        # Configuration list all or special switch for itered
        
        self.scan_network()
        switch_list = []
        if data['switch'] == "all":
            switch_list = self.cf.all_switches
        else:
            switch_list.append[data['switch_ip']]

        match data['action']:
            case "delete":
                port_config_delete_file = f"{self.cf.config_dir}/Ports-Access-Delete.txt"
                if data['type'] == "trunk":
                    port_config_delete_file = f"{self.cf.config_dir}/Ports-Trunk-Delete.txt"

                with open(port_config_delete_file, "r", encoding="utf-8") as f:
                    port_config_delete_file = [
                        f"no {line.strip()}" for line in f]

                for switch in switch_list:
                    try:
                        connect = self.switch_connect(switch)
                        switch_config = connect.send_command(
                            "show running-config")
                        switch_lines = self.coreConfigFormatChanger(
                            switch_config)
                        interfaces_dict = self.parse_interfaces(switch_lines)
                        for port, config in interfaces_dict.items():
                            if data['type'] == "access" and "access" in config:
                                commands = [
                                    f"interface {port}"] + port_config_delete_file
                                connect.send_config_set(commands)
                                print(
                                    f"Switch-IP: {switch:<18} Mode: access, Port: {port}")

                            elif data['type'] == "trunk" and "trunk" in config:
                                commands = [
                                    f"interface {port}"] + port_config_delete_file
                                connect.send_config_set(commands)
                                print(
                                    f"Switch-IP: {switch:<18} Mode: trunk, Port: {port}")
                        connect.save_config()
                    except Exception as e:
                        continue

            case "json":
                json_config_file = f"{self.cf.config_dir}/Free-Config.json"
                with open(json_config_file, "r", encoding="utf-8") as file:
                    json_data = json.load(file)
                switch_list = []
                if json_data['switch'] == "all":
                    switch_list = self.cf.all_switches
                else:
                    switch_list.append(json_data['switch_ip'])

                for ip in switch_list:
                    change_config = False
                    try:
                        connect = self.switch_connect(ip)
                        switch_config = connect.send_command(
                            "show running-config")
                        switch_lines = self.coreConfigFormatChanger(
                            switch_config)
                    except Exception as e:
                        continue

                    if json_data['target'] == "port":
                        interfaces_dict = self.parse_interfaces(switch_lines)
                        match json_data['type']:
                            case "all":
                                for key, value in interfaces_dict.items():
                                    try:
                                        if json_data['value'] not in value:
                                            commands = [f"interface {key}"]
                                            for item in json_data['commands']:
                                                commands.append(item)
                                                connect.send_config_set(
                                                    commands)
                                                print(
                                                    f"switch: {ip:<18} description: ********, Interface {key}")
                                                change_config = True
                                    except Exception as e:
                                        print(f"{key}: {e}")
                                        continue
                    if not change_config:
                        print(f"Switch: {ip:<18} not changed!")

                    if json_data['save']:
                        connect.save_config()

    def coreCheckPortConfig(self, user_type: str, set_number: int):
        
        dt = self.get_datetime()
        self.scan_network()

        user_lines = []
        filename = ""
        ports_configs = ""
        if user_type == "Trunk":
            ports_configs = f"{self.cf.config_dir}/Result/Ports-Trunk-Configs_{dt['date']}-{dt['time']}.txt"
            filename = f"{self.cf.config_dir}/Ports-Trunk-Configs.txt"
            with open(filename, "r", encoding="utf-8") as f:
                user_lines = [line.strip() for line in f]
        else:
            ports_configs = f"{self.cf.config_dir}/Result/Ports-Access-Configs_{dt['date']}-{dt['time']}.txt"
            filename = f"{self.cf.config_dir}/Ports-Access-Configs.txt"
            with open(filename, "r", encoding="utf-8") as f:
                user_lines = [line.strip() for line in f]

        print("Ports User Config:")
        print("\n".join(f"{str(i+1).zfill(2)}: {item}" for i,
                        item in enumerate(user_lines)), "\n\nPorts Status:\n")

        for ip in self.cf.all_switches:
            try:
                connect = self.switch_connect(ip)
                switch_config = connect.send_command("show running-config")
                switch_lines = self.coreConfigFormatChanger(switch_config)
                interfaces_dict = self.parse_interfaces(switch_lines)

                version_data = connect.send_command("show version")
                model = self.find_model(version_data)
                model_number = re.findall(r"\d{4}", model)

                port_commands = {}
                for key, value in interfaces_dict.items():
                    port_commands[key] = []
                    port_type = "Warning!"
                    if "switchport access vlan" in value:
                        port_type = "Access"
                    elif "switchport mode trunk" in value:
                        port_type = "Trunk"

                    if (user_type == "Trunk" and port_type == "Trunk") or (user_type == "Access" and port_type == "Access"):
                        msg2 = f"- IP: {ip:<18} Switch-Model: {model_number[0]}     Port: {key:<30} Port-Type: {port_type:<10} Missings: "
                        self.coreWriteFile(ports_configs, msg2)
                        print(msg2, end="")
                        for ul in user_lines:
                            if ul not in value:
                                port_commands[key].append(ul)
                                msg3 = f"{str(user_lines.index(ul)+1).zfill(2)}:N "
                                self.coreWriteFile(ports_configs, msg3)
                                print(msg3, end="")

                        self.coreWriteFile(ports_configs, "\n")
                        print("")
                if set_number != 0:
                    accept_set = input("Add this commands to switch (Y/N) ? ")
                    if accept_set == "Y" or accept_set == "y":
                        for key, value in port_commands.items():
                            commands = port_commands[key]
                            if len(commands) > 0:
                                port = key
                                connect.send_config_set(
                                    [f"interface {port}"] + commands)
                                print(f"port {key}: Add {commands}")
                        connect.save_config()

            except Exception as e:
                continue

        input("Task finished! press Enter to continue ..")
        os.system('cls')

    def coreCreateExportCsvFile(self):
        db = App_DB()
        ip_row = db.databaseGetIpData()
        with open("ip_data_export.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["IP Address", "MAC Address",
                            "Switch IP", "Port", "Insert Data", "Update Data"])

            for row in ip_row:
                imsp_value = row[1]
                insert_date = row[2]
                update_date = row[3]

                parts = imsp_value.split("|")
                writer.writerow(parts + [insert_date, update_date])

        input("Task finished! press Enter to continue ..")

    def coreGetSwitchesBackup(self):
        self.log("core[]:core{}:coreGetSwitchesBackup():scan_network()")
        self.scan_network()
        switches = self.cf.all_switches

        # Put there for use two lines
        self.log("core[]:core{}:coreGetSwitchesBackup():get_datetime()")
        dt = self.get_datetime()
        counter = 1
        for ip in switches:
            connect = None
            auth_index = 0
            while True:
                try:
                    cisco_switch = {
                        'device_type': 'cisco_ios',
                        'host': ip,
                        'username': self.cf.auth_dict[auth_index]['username'],
                        'password': self.cf.auth_dict[auth_index]['password'],
                        'secret': self.cf.auth_dict[auth_index]['secret'],
                    }

                    self.log(
                        f"core[]:core{{}}:coreGetSwitchesBackup():for:while:ConnectHandler({ip})")
                    connect = ConnectHandler(**cisco_switch)
                    connect.enable()
                    break

                except Exception as e:
                    if auth_index < len(self.cf.auth_dict):
                        auth_index += 1
                        continue
                    else:
                        break

            if connect != None:
                try:
                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show version)")
                    version_data = connect.send_command("show version")
                    hostname = self.find_hostname(version_data)
                    print(f"{counter:<3} - {hostname:<30} create ", end="")
                    self.coreWriteFile(
                        f"{self.cf.version_dir}{dt['backup']}/{hostname}-version_{dt['date']}-{dt['time']}.txt", version_data)
                    print("version, ", end="")

                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show running-config)")
                    running_config_data = connect.send_command(
                        "show running-config")
                    self.coreWriteFile(
                        f"{self.cf.switchconfig_dir}{dt['backup']}/{hostname}-config_{dt['date']}-{dt['time']}.txt", running_config_data)
                    print("config, ", end="")

                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show interfaces status)")
                    interface_status_data = connect.send_command(
                        "show interfaces status")
                    self.coreWriteFile(
                        f"{self.cf.interface_dir}{dt['backup']}/{hostname}-interface_{dt['date']}-{dt['time']}.txt", interface_status_data)
                    print("interfaces, ", end="")

                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show vlan brief)")
                    vlan_brief_data = connect.send_command("show vlan brief")
                    self.coreWriteFile(
                        f"{self.cf.vlans_dir}{dt['backup']}/{hostname}-vlan_{dt['date']}-{dt['time']}.txt", vlan_brief_data)
                    print("vlans, ", end="")

                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show cdp neighbors detail)")
                    show_cdp_data = connect.send_command(
                        "show cdp neighbors detail")
                    self.coreWriteFile(
                        f"{self.cf.switchcdp_dir}{dt['backup']}/{hostname}-cdp_{dt['date']}-{dt['time']}.txt", show_cdp_data)
                    print("cdp, ", end="")

                    ip_data = ""
                    try:
                        self.log(
                            "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show ip device tracking all)")
                        ip_data = connect.send_command(
                            "show ip device tracking all")

                    except Exception as e:
                        self.log(
                            "core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show device-tracking database)")
                        ip_data = connect.send_command(
                            "show device-tracking database")

                    self.coreWriteFile(
                        f"{self.cf.ips_dir}{dt['backup']}/{hostname}-ip_{dt['date']}-{dt['time']}.txt", ip_data)
                    print("vlans, ", end="")

                    backup_msg = running_config_data + "\n\n\n"
                    backup_msg += version_data + "\n\n\n"
                    backup_msg += interface_status_data + "\n\n\n"
                    backup_msg += vlan_brief_data + "\n\n\n"
                    backup_msg += show_cdp_data + "\n\n\n"
                    backup_msg += ip_data + "\n\n\n"
                    self.coreWriteFile(
                        f"{self.cf.backup_dir}{dt['backup']}/{hostname}-backup_{dt['date']}-{dt['time']}.txt", backup_msg)
                    print("backup file successfully!")
                    self.log(
                        "core[]:core{}:coreGetSwitchesBackup():for:while:if:Files Created!")
                    counter += 1
                except Exception as e:
                    self.log(
                        f"core[]:core{{}}:coreGetSwitchesBackup():for:while:if:Exception:{e}")

        input("Task finished! press Enter to continue ..")
        os.system('cls')


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
    cf = Config()
    conn = None
    cursor = None
    cr = None

    def __init__(self):
        try:
            self.cr = Core()
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

            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS ip_data (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    imsp TEXT NOT NULL,
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
            
            en = Encryption()
            self.__open()
            self.cursor.execute("SELECT * FROM admin_data")
            rows = self.cursor.fetchall()

            for i, row in enumerate(rows):
                self.cf.auth_dict.update({i: {
                    "type": en.decode(row[4]),
                    "username": en.decode(row[1]),
                    "password": en.decode(row[2]),
                    "secret": en.decode(row[3])
                }})

        except Exception as e:
            print(f"- F-core, C-App_DB, D-set_dict_admin_data: {e}")
            sys.exit(1)

    def set_dict_ipsubnet_data(self):
        self.cr.log("core[]:App_DB{}:set_dict_ipsubnet_data()")
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

    def insert_ipdata(self, imsp, date_time):
        try:
            new_imsp = False
            self.__open()
            self.cursor.execute(
                "SELECT * FROM ip_data WHERE imsp = ?", (imsp,))
            row = self.cursor.fetchone()

            if not row:
                new_imsp = True
                self.cursor.execute(
                    """INSERT INTO ip_data (
                            imsp,
                            insert_date,
                            update_date
                        ) VALUES (?, ?, ?)""", (
                        imsp,
                        date_time,
                        date_time,
                    ))
            else:
                self.cursor.execute(
                    "UPDATE ip_data SET update_date = ? WHERE imsp = ?", (date_time, imsp))

            self.__close()
            return new_imsp
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_ipdata: {e}")
            sys.exit(1)

    def databaseGetIpData(self):
        self.__open()
        self.cursor.execute("SELECT * FROM ip_data")
        return self.cursor.fetchall()
