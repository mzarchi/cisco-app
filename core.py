from config import Config
from datetime import datetime
from database import Database
from encrypt import Encryption
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException
from concurrent.futures import ThreadPoolExecutor

import os
import re
import csv
import socket
import getpass
import platform
import ipaddress
import subprocess

class Core:
    cf = Config()
    db = Database()

    def __init__(self):
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
                result = subprocess.run(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
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

    def manage_content(self, content: str):
        content = content.split("-------------------------")
        del content[0]
        return content

    def switch_data(self, switch: list):
        result = {}
        deviveID_pattern = r".*Device ID:.*"
        deviveID_find = re.findall(deviveID_pattern, switch)[0]
        replacement = {"Device ID: ": "", Config.domain: ""}
        for i in replacement.keys():
            deviveID_find = deviveID_find.replace(i, replacement[i])
        result.update({"device": deviveID_find})

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
        message += "First-Commit: G0-2508, version: G132-2608\n" # G{CommitsCounts}-{YYMM}
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
        message += "\t5- Get DNS name by IP\n"
        message += "\t6- Switch Config Manager\n"
        message += "\t7- Access-List Manager\n"
        message += "\t8- Get Backup from Config/Interfaces/version/CDP details of switches\n"
        message += "\ts- Search in Switches IPs database\n"
        message += "\tc- Get CSV from database\n"
        message += "\tr- Run SQL Query on database\n"
        message += "\te- Exit\nPlease insert option number: "
        return message

    def ping_host(self, ip):
        cmd = ["ping", "-n", "1", "-w", "300", ip]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        db = Database()
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
                    self.log("core[]:core{}:case_switch_link():for:while:if:manage_content()")
                    sw_text = self.manage_content(content)
                    self.log("core[]:core{}:case_switch_link():for:while:if:CreateFile:cdp.txt")
                    with open(f"{self.cf.switchcdp_dir}{hostname}-CDP_{dt['date']}-{dt['time']}.txt", "a") as file:
                        file.write(content)

                    # def write_result
                    wr_result = ""
                    for i in range(0, len(sw_text)):
                        self.log("core[]:core{}:case_switch_link():for:while:if:for:switch_data()")
                        sw_data = self.switch_data(sw_text[i])
                        part_one = f"{self.__set_number()} - {Config.hostname+":":<30} {sw_data["ports"][0]:<25}"
                        part_two = f"{sw_data["device"]+":":<30} {sw_data["ports"][1]:<25}"
                        link = f"{Config.hostname}-{sw_data["ports"][0]}|{sw_data["device"]}-{sw_data["ports"][1]}"
                        msl_dt = f"{dt['date']}-{dt['time']}"
                        self.log("core[]:core{}:case_switch_link():for:while:if:for:App_DB{}:manage_switch_link()")
                        update = db.manage_switch_link(link, msl_dt)

                        part_three = "Insert (New!)"
                        if update:
                            part_three = "Update"

                        print(f"{part_one} ----> {part_two} {part_three}")
                        wr_result += f"{part_one} ----> {part_two} {part_three}\n"

                    result += wr_result

                except Exception as e:
                    self.log(f"core[]:core{{}}:case_switch_link():for:while:if:for:Error:{e}")
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
        result.update({"dati": now.strftime("%Y-%m-%d %H%M%S")})
        result.update({"unix": str(int(now.timestamp()))})
        return result

    def cudt(self, unixtime):
        dt_utc = datetime.fromtimestamp(unixtime)
        # dt_iran = dt_utc + timedelta(hours=3, minutes=30)
        return dt_utc.strftime('%Y-%m-%d %H:%M:%S')

    def ter_cls(self):
        os.system('cls')

    def app_settings_handler(self):
        self.log("core[]:core{}:app_settings_handler():Create Encryption obj")
        en = Encryption()
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t1- Add/Remove SSH data\n"
        message += "\t2- Add/Remove SSH user login\n"
        message += "\td- Debug Mode (Safe for user)\n"
        message += "\te- Exit from Settings\nPlease insert option number: "

        while True:
            self.log("core[]:core{}:app_settings_handler():case_number:input()")
            case_number = input(message)

            if case_number == "e":
                self.ter_cls()
                break

            match case_number:
                case "1":
                    self.log("core[]:core{}:app_settings_handler():case_number-1")
                    self.ter_cls()
                    c1_message = "Please select one of the options below:\n"
                    c1_message += "\t1- Add SSH Data\n"
                    c1_message += "\t2- Show SSH Data\n"
                    c1_message += "\t3- Remove SSH Data\n"
                    c1_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        self.log("core[]:core{}:app_settings_handler():c1_case_number:input()")
                        c1_case_number = input(c1_message)
                        if c1_case_number == "e":
                            self.ter_cls()
                            break

                        match c1_case_number:
                            case "1":
                                self.log("core[]:core{}:app_settings_handler():c1_case_number-1")
                                self.ter_cls()
                                ipsubnet_data = {}
                                ip_subnet = self.get_current_text("Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                domain = self.get_current_text("Please enter domain: ")

                                ipsubnet_data.update({
                                    "ip_subnet": ip_subnet,
                                    "domain": domain
                                })

                                self.log("core[]:core{}:app_settings_handler():c1_case_number-1:App_DB{}:set_ipsubnet_data()")
                                self.db.set_ipsubnet_data(ipsubnet_data)
                                input("Data Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.log("core[]:core{}:app_settings_handler():c1_case_number-2")
                                self.ter_cls()
                                self.log("core[]:core{}:app_settings_handler():App_DB{}:set_dict_ipsubnet_data()")
                                ip_subnet = self.db.set_dict_ipsubnet_data()

                                for key, value in ip_subnet.items():
                                    print(f"{key+1:<3} - IP: {value['ip_subnet']:<18} Domain: {value['domain']}")

                                input("\nPress any key to return ...")
                                continue

                            case "3":
                                self.log("core[]:core{}:app_settings_handler():c1_case_number-3")
                                self.ter_cls()
                                ip_subnet = self.get_current_text("Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                self.log("core[]:core{}:app_settings_handler():App_DB{}:del_ipsubnet_data()")
                                self.db.del_ipsubnet_data(ip_subnet)

                                input("\nPress any key to return ...")
                                continue
                        self.log("core[]:core{}:app_settings_handler():App_DB{}:set_dict_ipsubnet_data()")
                        self.db.set_dict_ipsubnet_data()

                case "2":
                    self.log("core[]:core{}:app_settings_handler():case_number-2")
                    self.ter_cls()
                    c2_message = "Please select one of the options below:\n"
                    c2_message += "\t1- Add Admin\n"
                    c2_message += "\t2- Show Admin\n"
                    c2_message += "\t3- Remove Admin\n"
                    c2_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number:imput()")
                        c2_case_number = input(c2_message)
                        if c2_case_number == "e":
                            break

                        match c2_case_number:
                            case "1":
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-1")
                                self.ter_cls()
                                user_data = {}
                                username = self.get_current_text("Please inser your username: ")
                                password = self.get_current_text("Please inser your password: ", False)
                                secret = self.get_current_text("Please inser your secret: ", False)
                                tag = self.get_current_text("Please inser admin tag: ")
                                user_data.update({
                                    "username": username,
                                    "password": password,
                                    "secret": secret,
                                    "tag": tag
                                })
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-1:App_DB{}:set_admin_data()")
                                self.db.set_admin_data(user_data)

                                input("User Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-2")
                                self.ter_cls()
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-2:App_DB{}:get_admin_data()")
                                rows = self.db.get_admin_data()
                                for i, row in enumerate(rows):
                                    print(f"id:{i+1} - Username: {en.decode(row[1])}, Tag: {en.decode(row[4])}")
                                input("Press enter to back ..")
                                self.ter_cls()
                                continue

                            case "3":
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3")
                                self.ter_cls()
                                c3_username = input("Input username for remove: ")
                                self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3:App_DB{}:del_admin_data()")
                                self.db.del_admin_data(en.encode(c3_username))

                    self.log("core[]:core{}:app_settings_handler():case_number-2:c2_case_number-3:App_DB{}:set_dict_admin_data()")
                    
                case "d":
                    self.log("core[]:core{}:app_settings_handler():case_number-d")
                    self.ter_cls()
                    dt = self.get_datetime()
                    cd_message = "Please select one of the options below:\n"
                    cd_message += "\tcct- Config Check Template\n"
                    cd_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        cd_case_number = input(cd_message)
                        if cd_case_number == "e":
                            break
                        
                        match cd_case_number:
                            case "cct":
                                self.ter_cls()
                                cct_message = "Please select one of the options below:\n"
                                cct_message += "1. All switch\n"
                                cct_message += "2. One switch\n"
                                cct_message += "e. Exit\nYour choose: "
                                while True:
                                    cct_user_input = input(cct_message)
                                    if cct_user_input == "e":
                                        break
                                    
                                    if cct_user_input == "1":
                                        self.scan_network()
                                        all_ip = self.cf.all_switches
                                    elif cct_user_input == "2":
                                        ip = input("Insert switch ip: ")
                                        all_ip = [ip]
                                    else:
                                        continue
                                    
                                    for i, ip in enumerate(all_ip):
                                        connect = self.switch_connect(ip)
                                        if connect is None:
                                            continue
                                        
                                        version_data = connect.send_command("show version")
                                        model = self.find_model(version_data)
                                        model_number = re.findall(r"\d{4}", model)
                                        switch_configs = connect.send_command("show running-config")
                                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                                        cct_text_file = "\n".join(switch_configs_lines) + "\n"
                                        
                                        cct_file_name = f"{self.cf.debug_result}{dt['date']}_{dt['time']}_{ip:-<15}_{model_number[0]}.txt"
                                        print(f"{ip:<15}: {cct_file_name}")
                                        with open(cct_file_name, "a") as file:
                                            file.write(cct_text_file)

        self.db.set_dict_admin_data()

    def case_switch_scan(self):
        super_putty = []
        self.log("core[]:core{}:case_switch_scan():scan_network()")
        self.scan_network()
        self.log("core[]:core{}:case_switch_scan():get_datetime()")
        dt = self.get_datetime()
        counter = 1
        for ip in (Config.all_switches):
            try:
                self.log(f"core[]:core{{}}:case_switch_scan():for:switch_connect({ip})")
                cnt = self.switch_connect(ip)
                self.log("core[]:core{}:case_switch_scan():for:send_command(show version)")
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
                ports, ios_version, ios_type = self.get_ios_details(version_data)
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
                self.log(f"core[]:core{{}}:case_switch_scan():for:manage_switch_data({ip})")
                update = self.db.manage_switch_data(data)
                update_msg = "update" if update else "insert (New!)"
                uptime_line_file = f"{counter:<3}- Hostname: {self.cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<4} d, {hours:<2} h, {minutes:<2} m, real-ports: {ports:<3} IOS-version: {ios_version:<15} IOS-type: {ios_type:<25} Action: {update_msg}"
                uptime_line_console = f"{counter:<3}- Hostname: {self.cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<4} d, {hours:<2} h, {minutes:<2} m, Action: {update_msg}"
                counter += 1
                # uptime_line = f"{counter:<3}- Hostname: {self.cf.hostname:<30} Uptime: {days:<3} d, {hours:<2} h, {minutes:<2} m"
                self.log(f"core[]:core{{}}:case_switch_scan():for:CreateFile:Switches-List.txt")
                with open(f"{self.cf.switchlist_dir}Switches-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(f"{uptime_line_file} \n")

                super_putty.append(f'<SessionData SessionId="{self.cf.hostname}" SessionName="{self.cf.hostname}" ImageKey="computer" Host="{ip}" Port="22" Proto="SSH" PuttySession="Default Settings" Username="" ExtraArgs="" SPSLFileName="" RemotePath="" LocalPath="" />')
                print(uptime_line_console)
            except Exception as e:
                continue

        self.log(f"core[]:core{{}}:case_switch_scan():CreateFile:super-putty.xml")
        with open(f"{self.cf.superputty_dir}super-putty_{dt['date']}-{dt['time']}.xml", "a") as file:
            file.write('<?xml version="1.0" encoding="utf-8"?> \n')
            file.write('<ArrayOfSessionData xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"> \n')
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

    def get_dns_name(self, ip):
        result = "None"
        try:
            name = socket.gethostbyaddr(ip)
            result = name[0].replace(self.cf.domain, "")
        except Exception as e:
            result = "---------------"
            self.log(f"core[]:core{{}}:get_dns_name():Error:{e}")

        return result

    def case_switch_ips(self, dns_mode) -> None:
        counter = 1
        connect_failed = 0
        switch_ips = []
        user_special_ip = input("Enter Special Switch IP or Enter: ")
        if user_special_ip == "":
            self.scan_network()
            switch_ips = self.cf.all_switches
        else:
            switch_ips.append(user_special_ip)

        dns_i = 0
        dt = self.get_datetime()
        self.log(f"core[]:core{{}}:case_switch_ips():{dt}")
        ip_text_file = ""
        for hip in switch_ips:
            connect = self.switch_connect(hip)
            if connect is None:
                self.log(f"core[]:core{{}}:case_switch_ips():for:if:NoConnectivity({hip})")
                connect_failed += 1
                if connect_failed == 3:
                    self.log(f"core[]:core{{}}:case_switch_ips():for:if:if:StopConnectToSwitches")
                    print(f"--- - IP: {hip:<18} You can't connect to switch!")
                    break
                else:
                    self.log(f"core[]:core{{}}:case_switch_ips():for:if:else:GoToNextSwitchIP")
                    continue

            self.log(f"core[]:core{{}}:case_switch_ips():for:Connectivity({hip})")
            connect_failed = 0
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
            
            date_time = f"{dt['unix']}"
            actives = ["ACTIVE", "Active", "active", "REACHABLE", "Reachable", "reachable"]
            for line in sidta.splitlines():
                if any(state in line.split() for state in actives):
                    match = pattern.search(line)
                    if match:
                        ip, mac, port = match.groups()
                        if dns_mode:
                            dns_name = self.get_dns_name(ip)
                            imsp = f"{dns_name}|{hip}|{port}"
                            self.log("core[]:core{}:case_switch_ips():for:for:if:if:if:App_DB{}.insert_dnsdata(imsp, date_time)")
                            new_imsp = self.db.insert_dnsdata(imsp, date_time)
                            imsp_sec = "Update"
                            if new_imsp:
                                imsp_sec = "Insert (New!)"
                                
                            if dns_name != "---------------":
                                dns_i += 1
                                line = f"({counter:<3}, {dns_i:<3}) - IP: {ip:<18} Switch: {hip:<18} Port: {port:<25} PC-Name: {dns_name:<30} Action: {imsp_sec}"
                            else:
                                line = f"({counter:<3}, ---) - IP: {ip:<18} Switch: {hip:<18} Port: {port:<25} PC-Name: {dns_name:<30} Action: {imsp_sec}"
                                
                            ip_text_file += f"{line}\n"
                            print(line)
                            counter += 1

                        else:
                            imsp = f"{ip}|{mac}|{hip}|{port}"
                            self.log(f"core[]:core{{}}:case_switch_ips():for:for:if:if:else:App_DB{{}}.insert_ipdata({imsp}, {date_time}, {dt['dati']})")
                            new_imsp = self.db.insert_ipdata(imsp, date_time, dt['dati'])
                            imsp_sec = "Update"
                            if new_imsp:
                                imsp_sec = "Insert (New!)"

                            line = f"{counter:<4}- IP: {ip:<18} MAC: {mac:<18} Switch: {hip:<18} Port: {port:<25} Action: {imsp_sec}"
                            ip_text_file += f"{line}\n"
                            print(line)
                            counter += 1

        if connect_failed < 3:
            self.log("core[]:core{}:case_switch_ips():for:for:CreateFile:IP-List.txt")
            if dns_mode:
                with open(f"{self.cf.recordDNS_dir}IP-DNS_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(ip_text_file)
            else:
                with open(f"{self.cf.ips_dir}IP-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(ip_text_file)
        self.cf.all_switches.clear()
        input("Press any key to exit ..")

    def case_access_list_manager(self) -> None:
        uc_msg = "Please select on of below:\n"
        uc_msg += "1. View switch access-list and rules\n"
        uc_msg += "2. Add switch access-list\n"
        uc_msg += "3. Add access-list rule\n"
        uc_msg += "4. Debug\n"
        uc_msg += "e. Exit\n"
        uc_msg += "Enter your choose: "
        while True:
            user_case = input(uc_msg)
            if user_case == "1":
                while True:
                    user_ip = input("Enter switch ip (e:exit): ")
                    print()
                    if user_ip == "e":
                        break
                    connect = self.switch_connect(user_ip)
                    result = self.__get_switch_access_list_dict(connect) 
                    for key, values in result.items():
                        print(key)
                        for index, value in enumerate(values):
                            branch = "└── " if index == len(values) - 1 else "├── "
                            print(f"{branch}{value}")
                        print()
                        
            elif user_case == "2":
                user_ip = input("Enter switch ip (e:exit): ")
                if user_ip == "e":
                    break
                
                while True:
                    ia = 1
                    os.system('cls')
                    print(f"Current Access-List (IP: {user_ip}):")
                    connect = self.switch_connect(user_ip)
                    result = self.__get_switch_access_list_dict(connect)
                    for key in result.keys():
                        print(f"{ia:<2}. {key}")
                        ia += 1
                    
                    al_hint = "\nAccess-List create hint:\n"
                    al_hint += "Type 1:\n"
                    al_hint += "├── access-list <name> permit 192.168.1.0 0.0.0.255\n"
                    al_hint += "└── access-list <name> deny any\n"
                    al_hint += "\nType 2:\n"
                    al_hint += "├── access-list <name> permit tcp 192.168.1.0 0.0.0.255 any eq 80\n"
                    al_hint += "└── access-list <name> deny ip any any\n"
                    al_hint += "\nType 3:\n"
                    al_hint += "├── ip access-list extended <name>\n"
                    al_hint += "├── permit tcp 192.168.1.0 0.0.0.255 any eq 80\n"
                    al_hint += "└── deny ip any any\n"
                    al_hint += "\nType 4:\n"
                    al_hint += "├── mac access-list extended <name>\n"
                    al_hint += "├── permit host aaaa.bbbb.cccc any\n"
                    al_hint += "└── deny any any\n"
                    al_hint += "\nEnter new access-list (e:exit): "
                    new_access_list = input(al_hint)
                    if new_access_list == "e":
                        break
                    connect.send_config_set(new_access_list)
                    
            elif user_case == "4":
                pass
            elif user_case == "e":
                break
            else:
                continue
    
    def __get_switch_access_list_dict(self, connect):
        command_result = connect.send_command("show access-lists")
        result = {}
        current_key = None

        for line in command_result.splitlines():
            if not line.strip():
                continue

            if not line.startswith(" "):
                current_key = line.strip()
                result[current_key] = []
            else:
                result[current_key].append(line.strip())
                
        return result
    
    def case_config_manager(self):
        """
        ### _Support Cases:_
        ```
        Method | Object | Obj-Type | Model | Which
        -------+--------+----------+-------+------
          VIEW | Switch |  ------  |  New  |  One
        -------+--------+----------+-------+------
          VIEW | Switch |  ------  |  New  |  All
        -------+--------+----------+-------+------
          VIEW | Switch |  ------  |  Old  |  One
        -------+--------+----------+-------+------
          VIEW | Switch |  ------  |  Old  |  All
        -------+--------+----------+-------+------
          SET  |  PORT  |  ACCESS  |  New  |  One
        -------+--------+----------+-------+------
          SET  |  PORT  |  ACCESS  |  New  |  All
        -------+--------+----------+-------+------
          SET  |  PORT  |  ACCESS  |  Old  |  One
        -------+--------+----------+-------+------
          SET  |  PORT  |  ACCESS  |  Old  |  All
        -------+--------+----------+-------+------
          SET  |  PORT  |  TRUNK   |  ALL  |  One
        -------+--------+----------+-------+------
          SET  |  PORT  |  TRUNK   |  ALL  |  All
        ```
        """
        os.system('cls')
        dt = self.get_datetime()
        files_dict = {}
        for root, dirs, files in os.walk(self.cf.config_dir):
            for i, name in enumerate(files):
                real_dir = str(os.path.join(root, name))
                files_dict.update({i+1: real_dir})

        for key in files_dict.keys():
            print(f"{key:3} {files_dict[key].replace(self.cf.data_dir, "./")}")

        key_file = int(input("Enter file number: "))
        lines = []
        with open(files_dict[key_file], "r", encoding="utf-8") as file:
            for line in file:
                lines.append(line.replace("\n", ""))

        print("Your Configs: ")
        txt_result = ""
        for i, fline in enumerate(lines[2:], start=2):
            txt_helper = f"{i:3}. {fline}"
            txt_result += f"{txt_helper}\n"
            print(txt_helper)
        user_agree = input("Start program with this config? [Y/N] ")
        if user_agree == 'Y' or user_agree == 'y':
            funcs = lines[1].split(":")
            matches = (funcs[0], funcs[1], funcs[2], funcs[3])
            match matches:
                case ("view", "switch", "-", "new"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]
                        
                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue
                        
                        version_data = connect.send_command("show version")
                        model = self.find_model(version_data)
                        model_number = re.findall(r"\d{4}", model)
                        if int(model_number[0]) < 9000:
                            continue
                        
                        switch_configs = connect.send_command("show running-config")
                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                        
                        nfind = []
                        for i, fline in enumerate(lines[2:], start=2):
                            if "****" in fline:
                                clean_keyword = fline.replace("****", "")
                                if not any(clean_keyword in sline for sline in switch_configs_lines):
                                    nfind.append(i)
                            else:
                                if fline not in switch_configs_lines:
                                    nfind.append(i)

                        
                        nfind_str = ""
                        for i in nfind:
                            nfind_str += f"{lines[i].replace('____', '\n  ')}\n"
                            
                        with open(f"{self.cf.logs_dir}{dt['unix']}-sw{ip}.txt", "a") as file:
                            file.write(nfind_str)
                            
                        txt_helper = f"ip: {ip:<18}, Model: {model:<20}, Count {len(nfind):<4}, Cases: {", ".join(f"{item:<3}" for item in nfind)}"
                        txt_result += f"{txt_helper}\n"
                        print(txt_helper)

                    with open(f"{self.cf.logs_dir}{dt['unix']}-{funcs[0]}_{funcs[1]}_{funcs[2]}_{funcs[3]}_result.txt", "a") as file:
                        file.write(txt_result)
                    input("Press any key to back ..")
                    
                case ("view", "switch", "-", "old"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]
                        
                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue
                        
                        version_data = connect.send_command("show version")
                        model = self.find_model(version_data)
                        model_number = re.findall(r"\d{4}", model)
                        if int(model_number[0]) > 3000:
                            continue
                        
                        switch_configs = connect.send_command("show running-config")
                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                        
                        nfind = []
                        for i, fline in enumerate(lines[2:], start=2):
                            if "****" in fline:
                                clean_keyword = fline.replace("****", "")
                                if not any(clean_keyword in sline for sline in switch_configs_lines):
                                    nfind.append(i)
                            else:
                                if fline not in switch_configs_lines:
                                    nfind.append(i)

                        
                        nfind_str = ""
                        for i in nfind:
                            nfind_str += f"{lines[i].replace('____', '\n  ')}\n"
                            
                        with open(f"{self.cf.logs_dir}{dt['unix']}-sw{ip}.txt", "a") as file:
                            file.write(nfind_str)
                            
                        txt_helper = f"ip: {ip:<18}, Model: {model:<20}, Count {len(nfind):<4}, Cases: {", ".join(f"{item:<3}" for item in nfind)}"
                        txt_result += f"{txt_helper}\n"
                        print(txt_helper)

                    with open(f"{self.cf.logs_dir}{dt['unix']}-{funcs[0]}_{funcs[1]}_{funcs[2]}_{funcs[3]}_result.txt", "a") as file:
                        file.write(txt_result)
                    input("Press any key to back ..")
                
                case ("set", "port", "access", "new"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]

                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue

                        version_data = connect.send_command("show version")
                        model = self.find_model(version_data)
                        model_number = re.findall(r"\d{4}", model)
                        if int(model_number[0]) < 9000:
                            continue

                        print(f"- {ip} is opened!")
                        switch_configs = connect.send_command("show running-config")
                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                        interfaces = self.parse_interfaces(switch_configs_lines)
                        for key in interfaces.keys():
                            if "switchport mode access" in interfaces[key]:
                                for i, fline in enumerate(lines[2:], start=2):
                                    if fline not in interfaces[key]:
                                        connect.send_config_set([f"interface {key}", fline,])
                                        print(f"{ip:15} - {key} is set!")
                                    else:
                                        print(f"{ip:15} - {key} already set!")
                        connect.save_config()

                case ("set", "port", "access", "old"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]

                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue

                        version_data = connect.send_command("show version")
                        model = self.find_model(version_data)
                        model_number = re.findall(r"\d{4}", model)
                        if int(model_number[0]) > 9000:
                            continue

                        print(f"- {ip} is opened!")
                        switch_configs = connect.send_command("show running-config")
                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                        interfaces = self.parse_interfaces(switch_configs_lines)
                        for key in interfaces.keys():
                            if "switchport mode access" in interfaces[key]:
                                for i, fline in enumerate(lines[2:], start=2):
                                    if fline not in interfaces[key]:
                                        connect.send_config_set([f"interface {key}", fline,])
                                        print(f"{ip:15} - {key} is set!")
                                    else:
                                        print(f"{ip:15} - {key} already set!")
                        connect.save_config()
                        
                case ("set", "switch", "-", "all"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]

                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue

                        print(f"- {ip} is opened!")
                        clines = lines[2:]
                        connect.send_config_set(clines)
                        connect.save_config()
                        
                case ("set", "port", "trunk", "all"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]

                    for i, ip in enumerate(all_ip):
                        connect = self.switch_connect(ip)
                        if connect is None:
                            continue

                        version_data = connect.send_command("show version")
                        model = self.find_model(version_data)
                        model_number = re.findall(r"\d{4}", model)

                        print(f"- {ip} is opened!")
                        switch_configs = connect.send_command("show running-config")
                        switch_configs_lines = self.coreConfigFormatChanger(switch_configs)
                        interfaces = self.parse_interfaces(switch_configs_lines)
                        for key in interfaces.keys():
                            if "switchport mode trunk" in interfaces[key]:
                                for i, fline in enumerate(lines[2:], start=2):
                                    if fline not in interfaces[key]:
                                        connect.send_config_set([f"interface {key}", fline,])
                                        print(f"{ip:15} - {key} is set!")
                                    else:
                                        print(f"{ip:15} - {key} already set!")
                        connect.save_config()
                        
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
                    joined = parent + "".join("____" + s for s in subs)
                    output.append(joined)
                parent = line.strip()
                subs = []
        if parent:
            joined = parent + "".join("____" + s for s in subs)
            output.append(joined)

        output = [item for item in output if not set(item) <= {"!"}]
        return output

    def parse_interfaces(self, switch_config):
        interfaces = {}
        for line in switch_config:
            line = line.strip()
            if not line.startswith("interface "):
                continue

            parts = line.split("____", 1)
            key = parts[0].replace("interface ", "")
            if "Vlan" not in key:
                interfaces[key] = line
        return interfaces

    def coreWriteFile(self, dir_name, contents):
        with open(dir_name, "a") as file:
            file.write(contents)

    def coreCreateExportCsvFile(self):
        ip_row = self.db.databaseGetIpData()
        with open("ip_data_export.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["IP Address", "MAC Address", "Switch IP", "Port", "Insert Data", "Update Data"])

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

                    self.log(f"core[]:core{{}}:coreGetSwitchesBackup():for:while:ConnectHandler({ip})")
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
                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show version)")
                    version_data = connect.send_command("show version")
                    hostname = self.find_hostname(version_data)
                    print(f"{counter:<3} - {hostname:<30} create ", end="")
                    self.coreWriteFile(f"{self.cf.version_dir}{hostname}-version_{dt['date']}-{dt['time']}.txt", version_data)
                    print("version, ", end="")

                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show running-config)")
                    running_config_data = connect.send_command("show running-config")
                    self.coreWriteFile(f"{self.cf.switchconfig_dir}{hostname}-config_{dt['date']}-{dt['time']}.txt", running_config_data)
                    print("config, ", end="")

                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show interfaces status)")
                    interface_status_data = connect.send_command("show interfaces status")
                    self.coreWriteFile(f"{self.cf.interface_dir}{hostname}-interface_{dt['date']}-{dt['time']}.txt", interface_status_data)
                    print("interfaces, ", end="")

                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show vlan brief)")
                    vlan_brief_data = connect.send_command("show vlan brief")
                    self.coreWriteFile(f"{self.cf.vlans_dir}{hostname}-vlan_{dt['date']}-{dt['time']}.txt", vlan_brief_data)
                    print("vlans, ", end="")

                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show cdp neighbors detail)")
                    show_cdp_data = connect.send_command("show cdp neighbors detail")
                    self.coreWriteFile(f"{self.cf.switchcdp_dir}{hostname}-cdp_{dt['date']}-{dt['time']}.txt", show_cdp_data)
                    print("cdp, ", end="")

                    ip_data = ""
                    try:
                        self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show ip device tracking all)")
                        ip_data = connect.send_command("show ip device tracking all")

                    except Exception as e:
                        self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:send_command(show device-tracking database)")
                        ip_data = connect.send_command("show device-tracking database")

                    self.coreWriteFile(f"{self.cf.ips_dir}{hostname}-ip_{dt['date']}-{dt['time']}.txt", ip_data)
                    print("ip, ", end="")

                    backup_msg = running_config_data + "\n\n\n"
                    backup_msg += version_data + "\n\n\n"
                    backup_msg += interface_status_data + "\n\n\n"
                    backup_msg += vlan_brief_data + "\n\n\n"
                    backup_msg += show_cdp_data + "\n\n\n"
                    backup_msg += ip_data + "\n\n\n"
                    self.coreWriteFile(f"{self.cf.backup_dir}{hostname}-backup_{dt['date']}-{dt['time']}.txt", backup_msg)
                    print("backup file successfully!")
                    self.log("core[]:core{}:coreGetSwitchesBackup():for:while:if:Files Created!")
                    counter += 1
                except Exception as e:
                    self.log(f"core[]:core{{}}:coreGetSwitchesBackup():for:while:if:Exception:{e}")

        input("Task finished! press Enter to continue ..")
        os.system('cls')

    def coreSearchSwitchesIPsDatabase(self):
        dt = self.get_datetime()
        self.log("core[]:core{}:coreGetSwitchesBackup():scan_network()")
        while True:
            result = "\n"
            counter = 1
            key = input("Insert a IP, MAC, Switch or 'e' for exit: ")
            try:
                if key == "e":
                    break
                else:
                    self.log(f"core[]:core{{}}:coreSearchSwitchesIPsDatabase():key:{type(key)}")
                    line_data = self.db.getDataFromIpDataTable(key)
                    self.log(f"core[]:core{{}}:coreSearchSwitchesIPsDatabase():line_data:{type(line_data)}")
                    for ld in line_data:
                        self.log(f"core[]:core{{}}:coreSearchSwitchesIPsDatabase():ld:{type(ld)}")
                        list_data = ld[1].split("|")
                        ip_age = int((int(ld[3]) - int(ld[2])) / 86400)
                        insert_age = int((int(dt['unix']) - int(ld[2])) / 86400)
                        update_age = int((int(dt['unix']) - int(ld[3])) / 86400)
                        self.log(f"core[]:core{{}}:coreSearchSwitchesIPsDatabase():list_data:{type(list_data)}")
                        result += f"Result ID: {counter}\n"
                        result += f"Database ID: {ld[0]}\n"
                        result += f"IP Address: {list_data[0]}\n"
                        result += f"IP Age: {ip_age} days\n"
                        result += f"MAC Address: {list_data[1]}\n"
                        result += f"Switch IP: {list_data[2]}\n"
                        result += f"Port Number: {list_data[3]}\n"
                        result += f"Insert Date: {self.cudt(int(ld[2]))} ({insert_age} days ago)\n"
                        result += f"Update Date: {self.cudt(int(ld[3]))} ({update_age} days ago)\n\n"
                        counter += 1
                    print(result)
            except Exception as e:
                self.log(f"core[]:core{{}}:coreSearchSwitchesIPsDatabase():Exeption:{e}")
                continue

    def coreRunSqlQuery(self):
        while True:
            user_sql = input("Enter SQL Query (exit:e, again:a): ").strip()

            if user_sql.lower() == 'e':
                return
            elif user_sql.lower() == 'a':
                continue
            else:
                try:
                    result = self.db.dbRunSqlQuery(user_sql)
                    if isinstance(result, list):
                        if not result:
                            print("--- No results found ---\n")
                        else:
                            print("\n" + "="*30)
                            for row in result:
                                print(row)
                            print("="*30)
                            print(f"Total rows: {len(result)}\n")
                    else:
                        print(f"Done. Result: {result}\n")

                except Exception as e:
                    print(f"Error executing query: {e}\n")