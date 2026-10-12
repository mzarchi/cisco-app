from config import Config
from zoneinfo import ZoneInfo
from datetime import datetime
from database import Database
from encrypt import Encryption
from decorators import method_logger, lg
from matplotlib.ticker import MultipleLocator
from concurrent.futures import ThreadPoolExecutor
from netmiko.base_connection import BaseConnection
from netmiko import ConnectHandler, NetmikoTimeoutException, NetMikoAuthenticationException, ReadTimeout

import os
import re
import csv
import time
import socket
import getpass
import platform
import ipaddress
import subprocess
import threading
import pandas as pd
import matplotlib.pyplot as plt


class Core:
    cf = Config()
    db = Database()
    sw_con = {}
    sw_con_lock = threading.Lock()

    def __init__(self):
        pass

    def ping(self, ip):
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", ip]
            try:
                result = subprocess.run(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
                if result.returncode == 0:
                    return ip
            except subprocess.TimeoutExpired as e:
                # lg(f"{ip}:{type(e).__name__}") Igored
                return None
            except Exception as e:
                lg(f"{ip}:{type(e).__name__}")
                return None
            
    def scan_network(self):
        ip_subnet = Config.ssh_switch_range
        network = ipaddress.ip_network(ip_subnet, strict=False)

        

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(self.ping, str(host)) for host in network.hosts()]
            for future in futures:
                result = future.result()
                if result and result not in Config.all_switches:
                    self.cf.all_switches.append(result)

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
        message += "First-Commit: G0-2508, version: G190-2609\n" # G{CommitsCounts}-{YYMM}
        message += "Repository: https://github.com/mzarchi/cisco-app\n"
        message += "Me at Twitter, Telegram and Instagram: @mhzarchi\n"
        message += "I always live in the depths of the Internet ❤️"
        print(message)

    def show_menu(self, last_worker_run="Never", worker_status="Waiting"):
        self.ter_cls()
        services = f"Services last-run & status: {last_worker_run} ({worker_status})\n"
        menu = f"""Please select one of the options below:
            0- App Settings (Edit all app settings)
            1- IP Scanner + Subnet (Get all ip by subnet)
            2- Switch Scan (Get list of your switches)
            3- Switch Statuses
            4- Switches Link (Get uplink of your switches)
            5- Switches IPs (Get list of your IP Address in your switch)
            6- Get DNS name by IP
            7- Switch Config Manager
            8- Access-List Manager
            9- Get Backup from Config/Interfaces/version/CDP details of switches
            s- Search in Switches IPs database
            c- Get CSV from database
            r- Run SQL Query on database
            e- Exit"""
        return f"{services}{menu}\n\nPlease insert option number: "

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
            except Exception as e:
                lg(type(e).__name__)
                pass
        return open_ports

    def switch_statuses(self):
        self.ter_cls()
        while True:
            msg_select_duration = "List of time range:\n"
            msg_select_duration += "\td.  1 Day before\n"
            msg_select_duration += "\tw.  1 Week before\n"
            msg_select_duration += "\tm.  1 Month before (30 days)\n"
            msg_select_duration += "\ty.  1 Month before (365 days)\n"
            msg_select_duration += "\tat. All Switch/Time in all Temp\n"
            msg_select_duration += "\tar. All Switch/Time in all Ram\n"
            msg_select_duration += "\tac. All Switch/Time in all CPU\n"
            msg_select_duration += "\tb. back\n"
            msg_select_duration += "Enter your choose: "
            user_case = input(msg_select_duration)
            
            start_search = 0
            pname = None
            one_switch = True
            match user_case:
                case "d":
                    start_search = int(self.get_datetime()['unix']) - 86400
                    
                case "w":
                    start_search = int(self.get_datetime()['unix']) - 604800
                    
                case "m":
                    start_search = int(self.get_datetime()['unix']) - 2592000
                    
                case "y":
                    start_search = int(self.get_datetime()['unix']) - 31536000
                    
                case "at" | "ar" | "ac":
                    one_switch = False
                    pname = {'at':'temp','ar':'ram','ac':'cpu'}[user_case]
                    
                case "b":
                    break
            
            self.ter_cls()
            while True:
                sw_ip = 0
                if one_switch:
                    sw_ip = input("Enter your Switch IP (b: back): ")
                    if sw_ip == "b":
                        break
                
                sw_data = self.db.get_switch_statuses(start_search, sw_ip , pname)
                if not sw_data:
                    input("No Data found, press any key to continue ..")
                    continue
                self.plot_envelope(sw_data)
            
    
    def plot_envelope(self, sw_data):
        df = pd.DataFrame(sw_data)
        if df.empty:
            print("No data found for the selected time range.")
            input("Press any key to continue ..")
            return
    
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["unixt"] = pd.to_numeric(df["unixt"], errors="coerce")
        df = df.dropna(subset=["unixt", "value"])
        df = df[df["value"] > 0]
        
        df["datetime_utc"] = pd.to_datetime(df["unixt"], unit="s", utc=True)
        df["datetime"] = df["datetime_utc"].dt.tz_convert(ZoneInfo("Asia/Tehran"))
        df["hour_float"] = (
            df["datetime"].dt.hour
            + df["datetime"].dt.minute / 60
            + df["datetime"].dt.second / 3600
        )
        
        all_ips = sorted(df["sw_ip"].unique())
        if len(all_ips) == 1:
            ip_display = all_ips[0]
        else:
            ip_display = ", ".join(all_ips)
        
        params = [
            ("temp", "Temperature (°C)", "red", "blue"),
            ("cpu",  "CPU (%)",          "darkred", "darkblue"),
            ("ram",  "RAM (%)",          "darkred", "darkblue"),
        ]
        
        for pname, ylabel, max_color, min_color in params:
            sub = df[df["pname"] == pname].copy()
            
            if sub.empty:
                continue
            
            sub["time_bin"] = (sub["hour_float"] * 10).round() / 10
            envelope = sub.groupby("time_bin")["value"].agg(["min", "max"]).reset_index()
            envelope = envelope.sort_values("time_bin")
            
            global_max = envelope["max"].max()
            global_min = envelope["min"].min()
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            for sw_ip in all_ips:
                sw_ip_data = sub[sub["sw_ip"] == sw_ip].sort_values("hour_float")
                ax.plot(
                    sw_ip_data["hour_float"],
                    sw_ip_data["value"],
                    marker="o",
                    markersize=1,
                    linestyle="none",
                    alpha=0.5
                )
            
            ax.plot(
                envelope["time_bin"],
                envelope["max"],
                color=max_color,
                linewidth=1.0,
                linestyle="-",
                label=f"Max {pname} ({global_max:.1f})",
                zorder=5
            )
            
            ax.plot(
                envelope["time_bin"],
                envelope["min"],
                color=min_color,
                linewidth=1.0,
                linestyle="-",
                label=f"Min {pname} ({global_min:.1f})",
                zorder=5
            )
            
            ax.set_xlim(0, 24)
            ax.set_ylim(0, 100)
            
            ax.set_xlabel("Hour of Day", fontsize=12, fontweight="bold", labelpad=10)
            ax.set_ylabel(ylabel, fontsize=12, fontweight="bold", labelpad=10)
            
            ax.set_title(
                f"CiscoApp {pname.upper()} Envelope Plot",
                fontsize=18,
                fontweight="bold",
                pad=20
            )
            
            now = datetime.now()
            subtitle_text = f"Switch Graph {ip_display}  ({now.strftime('%Y-%m-%d %H:%M:%S')})"
            fig.text(
                0.5, 0.02,
                subtitle_text,
                ha="center",
                va="bottom",
                fontsize=11,
                color="#444444",
                style="italic"
            )
            
            ax.yaxis.set_major_locator(MultipleLocator(10))
            ax.yaxis.set_minor_locator(MultipleLocator(1))
            
            ax.xaxis.set_major_locator(MultipleLocator(1))
            ax.xaxis.set_minor_locator(MultipleLocator(0.1))
            
            x_ticks = list(range(0, 25))
            x_labels = [str(h) if h <= 23 else "" for h in x_ticks]
            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_labels)
            
            ax.grid(True, which="major", axis="y", alpha=0.5, linewidth=0.9,
                    color="#555555", linestyle="--")
            ax.grid(True, which="minor", axis="y", alpha=0.2, linewidth=0.7,
                    color="#999999", linestyle="--")
            ax.grid(True, which="major", axis="x", alpha=0.4, linewidth=0.8,
                    color="#666666", linestyle="--")
            ax.grid(True, which="minor", axis="x", alpha=0.12, linewidth=0.5,
                    color="#AAAAAA", linestyle="--")
            
            ax.tick_params(axis="both", which="both", length=0)
            ax.legend(loc="upper right", fontsize=9)
            plt.tight_layout(rect=[0, 0.05, 1, 1])
        
        plt.show()
    
    def __get_switch_temp(self, ip) -> int:
        int_value = 0
        try:
            cnt = self.__cnt(ip)
            showenvall = cnt.send_command("show env all")
            if "FAULTY" in showenvall:
                lg(f"ip: {ip}, Switch should be check!")
                
            match_legacy = re.search(r"System Temperature Value:\s*(\d+)\s*Degree Celsius", showenvall)
            if match_legacy:
                return int(match_legacy.group(1))

            match_xe = re.search(r"SYSTEM HOTSPOT\s+\d+\s+\w+\s+(\d+)\s+Celsius", showenvall)
            if match_xe:
                return int(match_xe.group(1))

        except ReadTimeout as rt:
            lg(f"ip: {ip}, Error: ReadTimeout")
            0
        except Exception as e:
            lg(f"IP: {ip}, {type(e).__name__}")

        return int_value

    def __get_switch_ram(self, ip) -> int:
        try:
            cnt = self.__cnt(ip)
            showmemorystatistics = cnt.send_command("show memory statistics")
            pattern = r"^Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)"
            memory = re.search(pattern, showmemorystatistics, re.MULTILINE)
            ram_percent = 0
            if memory:
                total = int(memory.group(1))
                used = int(memory.group(2))
                ram_percent = int((used * 100) / total)
                
            return ram_percent
        except Exception as e:
            lg(f"IP: {ip}, {type(e).__name__}")
            return 0
        
    def __get_switch_cpu(self, ip) -> int:
        try:
            cnt = self.__cnt(ip)
            showprocesscpu = cnt.send_command("show processes cpu | include CPU")
            cpu = re.search(r"five minutes:\s*(\d+%)", showprocesscpu)
            five_minutes_cpu = 0
            if cpu:
                five_minutes_cpu = int(cpu.group(1).replace("%", ""))
            
            return five_minutes_cpu
        
        except Exception as e:
            lg(f"IP: {ip}, {type(e).__name__}")
            return 0
        
        
    @method_logger
    def case_ip_scanner(self):
        base_ip_subnet = input("Insert your ip: ")
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
            except KeyboardInterrupt as e:
                message += "\nTask Killed!\n"
                lg(type(e).__name__)
                break

        with open(f"{self.cf.scanner_dir}IP-Scanner_{dt['date']}-{dt['time']}.txt", "a") as file:
            file.write(result_text)

        input(message + "Press any key to back ..")

    @method_logger
    def case_switch_link(self):
        db = Database()
        self.scan_network()
        result = ""
        switches = self.cf.all_switches
        dt = self.get_datetime()
        switch_al = []
        al = input("Do you get all link? (1:yes, 2:no) ")

        for i, ip in enumerate(switches):
            connect = self.__cnt(ip)
            if connect != None:
                try:
                    version_data = connect.send_command("show version")
                    hostname = self.find_hostname(version_data)

                    with open(f"{self.cf.version_dir}{hostname}-version_{dt['date']}-{dt['time']}.txt", "a") as file:
                        file.write(version_data)
                    content = connect.send_command("show cdp neighbors detail")
                    sw_text = self.manage_content(content)
                    with open(f"{self.cf.switchcdp_dir}{hostname}-CDP_{dt['date']}-{dt['time']}.txt", "a") as file:
                        file.write(content)

                    wr_result = ""
                    for j in range(0, len(sw_text)):
                        sw_data = self.switch_data(sw_text[j])
                        part_one = f"{Config.hostname + ':':<30} {sw_data['ports'][0]:<25}"
                        part_two = f"{sw_data['device'] + ':':<30} {sw_data['ports'][1]:<25}"
                        link1 = f"{Config.hostname}-{sw_data["ports"][0]}|{sw_data["device"]}-{sw_data["ports"][1]}"
                        link2 = f"{sw_data["device"]}-{sw_data["ports"][1]}|{Config.hostname}-{sw_data["ports"][0]}"
                        msl_dt = f"{dt['date']}-{dt['time']}"
                        
                        if al == "1":
                            update = db.manage_switch_link(link1, msl_dt)
                            part_three = "Insert (New!)"
                            if update:
                                part_three = "Update"
    
                            print(f"{part_one} ----> {part_two} {part_three}")
                            wr_result += f"{part_one} ----> {part_two} {part_three}\n"
                            
                        elif al == "2":
                            if link1 not in switch_al and link2 not in switch_al:
                                update = db.manage_switch_link(link1, msl_dt)
                                switch_al.append(link1)
                                part_three = "Insert (New!)"
                                if update:
                                    part_three = "Update"
    
                                print(f"{part_one} ----> {part_two} {part_three}")
                                wr_result += f"{part_one} ----> {part_two} {part_three}\n"

                    result += wr_result
                except Exception as e:
                    lg(type(e).__name__)
                    continue

        with open(f"{self.cf.switchlinks_dir}Switch-Links_{dt['date']}-{dt['time']}.txt", "a") as file:
            file.write(result)

        Config.counter = 0
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
        result.update({"psc": now.strftime("%Y-%m-%d %H:%M:%S")})
        result.update({"unix": str(int(now.timestamp()))})
        return result

    def cudt(self, unixtime):
        dt_utc = datetime.fromtimestamp(unixtime)
        # dt_iran = dt_utc + timedelta(hours=3, minutes=30)
        return dt_utc.strftime('%Y-%m-%d %H:%M:%S')

    def ter_cls(self):
        os.system('cls')

    @method_logger
    def app_settings_handler(self):
        en = Encryption()
        self.ter_cls()
        message = "Please select one of the options below:\n"
        message += "\t1- Add/Remove SSH data\n"
        message += "\t2- Add/Remove SSH user login\n"
        message += "\t3- Set switch_ips_worker Interval\n"
        message += "\t4- Show defs in all switches (write-in-file)\n"
        message += "\td- Debug Mode (Safe for user)\n"
        message += "\te- Exit from Settings\nPlease insert option number: "

        while True:
            case_number = input(message)

            if case_number == "e":
                self.ter_cls()
                break

            match case_number:
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
                                ip_subnet = self.get_current_text("Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                domain = self.get_current_text("Please enter domain: ")

                                ipsubnet_data.update({
                                    "ip_subnet": ip_subnet,
                                    "domain": domain
                                })

                                self.db.set_ipsubnet_data(ipsubnet_data)
                                input("Data Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.ter_cls()
                                ip_subnet = self.db.set_dict_ipsubnet_data()

                                for key, value in ip_subnet.items():
                                    print(f"{key+1:<3} - IP: {value['ip_subnet']:<18} Domain: {value['domain']}")

                                input("\nPress any key to return ...")
                                continue

                            case "3":
                                self.ter_cls()
                                ip_subnet = self.get_current_text("Please enter ip and subnet (ex: 192.168.1.0/24): ")
                                self.db.del_ipsubnet_data(ip_subnet)

                                input("\nPress any key to return ...")
                                continue
                        self.db.set_dict_ipsubnet_data()

                case "2":
                    self.ter_cls()
                    c2_message = "Please select one of the options below:\n"
                    c2_message += "\t1- Add Admin\n"
                    c2_message += "\t2- Show Admin\n"
                    c2_message += "\t3- Remove Admin\n"
                    c2_message += "\te- Exit\nPlease insert option number: "
                    while True:
                        c2_case_number = input(c2_message)
                        if c2_case_number == "e":
                            break

                        match c2_case_number:
                            case "1":
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
                                self.db.set_admin_data(user_data)

                                input("User Added to Database!\nPress enter to back ..")
                                self.ter_cls()
                                continue

                            case "2":
                                self.ter_cls()
                                rows = self.db.get_admin_data()
                                for i, row in enumerate(rows):
                                    print(f"id:{i+1} - Username: {en.decode(row[1])}, Tag: {en.decode(row[4])}")
                                input("Press enter to back ..")
                                self.ter_cls()
                                continue

                            case "3":
                                self.ter_cls()
                                c3_username = input("Input username for remove: ")
                                self.db.del_admin_data(en.encode(c3_username))

                case "3":
                    data = self.db.get_app_variables()
                    new_value = input(f"Enter a switch_ips_worker interval (current:{data[1]}s, e:exit): ")
                    if new_value != "e":
                        self.db.set_app_variables(new_value)
                        Config.interval_changed_flag = True

                case "4":
                    self.ter_cls()
                    user_imputs = input("Enter your Show Switch Method: ")
                    connect_failed = 0
                    switch_ips = []
                    switch_ips = self.cf.all_switches.copy()
                    for hip in switch_ips:
                        try:
                            connect = self.__cnt(hip)
                            if connect is None:
                                connect_failed += 1
                                if connect_failed == 3:
                                    break
                                else:
                                    continue

                            connect_failed = 0
                            show_result = connect.send_command(user_imputs)
                            self.coreWriteFile(f"{self.cf.showDefResult}/{hip}-{user_imputs.replace(" ", "")}.txt", show_result)
                            
                        except Exception as e:
                            lg(type(e).__name__)
                            if hip == switch_ips[-1]:
                                break
                            else:
                                continue
                            
                case "d":
                    self.ter_cls()
                    dt = self.get_datetime()
                    cd_message = "Please select one of the options below:\n"
                    cd_message += "\tcct- Config Check Template\n"
                    cd_message += "\tpsc- Print Switches Connection (dict)\n"
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
                                        connect = self.__cnt(ip)
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

                            case "psc":
                                for ip in self.sw_con.keys():
                                    print(f"{ip:<15}, obj: {self.sw_con[ip]['obj']}, create: {self.sw_con[ip]['created']}, used: {self.sw_con[ip]['used']}")
                                input("\nPress any key to exit ...")

        self.db.set_dict_admin_data()

    @method_logger
    def case_switch_scan(self):
        super_putty = []
        show_result_file = {}
        show_result_console = {}
        self.scan_network()
        dt = self.get_datetime()

        total = len(Config.all_switches)
        current = 0

        for ip in Config.all_switches:
            current += 1
            percent = int((current / total) * 100) if total > 0 else 0
            print(f"\rPlease wait ({current}/{total}) {percent}%", end="", flush=True)

            try:
                cnt = self.__cnt(ip)
                version_data = cnt.send_command("show version")
                self.find_hostname(version_data)
                model = self.find_model(version_data)
                sw_mac = self.find_mac(version_data)
                days, hours, minutes = self.get_uptime(version_data)
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
                update = self.db.manage_switch_data(data)
                update_msg = "update" if update else "insert (New!)"
                uptime_line_file = f"Hostname: {self.cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<4} d, {hours:<2} h, {minutes:<2} m, real-ports: {ports:<3} IOS-version: {ios_version:<15} IOS-type: {ios_type:<25} Action: {update_msg}"
                uptime_line_console = f"Hostname: {self.cf.hostname:<30} Model: {model:<20} Mac-Address: {sw_mac:<20} Uptime: {days:<4} d, {hours:<2} h, {minutes:<2} m, Action: {update_msg}"
                if model in show_result_file.keys():
                    show_result_file[model].append(uptime_line_file)
                else:
                    show_result_file.update({model:[uptime_line_file]})

                if model in show_result_console.keys():
                    show_result_console[model].append(uptime_line_console)
                else:
                    show_result_console.update({model:[uptime_line_console]})

                super_putty.append(f'<SessionData SessionId="{self.cf.hostname}" SessionName="{self.cf.hostname}" ImageKey="computer" Host="{ip}" Port="22" Proto="SSH" PuttySession="Default Settings" Username="" ExtraArgs="" SPSLFileName="" RemotePath="" LocalPath="" />')
            except Exception as e:
                lg(type(e).__name__)
                continue

        print()

        all_file_lines = []
        all_console_lines = []
        for i in show_result_file.keys():
            all_file_lines.extend(show_result_file[i])
            all_console_lines.extend(show_result_console[i])

        with open(f"{self.cf.switchlist_dir}Switches-List_{dt['date']}-{dt['time']}.txt", "a", encoding="utf-8") as file:
            file.write("\n".join(all_file_lines) + "\n")

        xml_lines = ['<?xml version="1.0" encoding="utf-8"?>',
                     '<ArrayOfSessionData xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">']
        xml_lines.extend(f"  {switch}" for switch in super_putty)
        xml_lines.append('</ArrayOfSessionData>')

        with open(f"{self.cf.superputty_dir}super-putty_{dt['date']}-{dt['time']}.xml", "a", encoding="utf-8") as file:
            file.write("\n".join(xml_lines) + "\n")

        print("\n".join(all_console_lines))

        Config.counter = 0
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

    def cnt(self, ip):
        return self.__cnt(ip)
    
    def __cnt(self, ip):
        connect = None
        dt = self.get_datetime()
        date_time = f"{dt['psc']}"

        with self.sw_con_lock:
            if ip in self.sw_con:
                connect = self.sw_con[ip]['obj']
                if connect.is_alive():
                    self.sw_con[ip]['used'] = date_time
                    return connect
                else:
                    del self.sw_con[ip]

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
                with self.sw_con_lock:
                    self.sw_con.update({ip: {"obj": connect, "created": date_time, "used": date_time}})
                return connect
            
            except NetmikoTimeoutException as nte:
                # lg(f"{ip}:{type(nte).__name__}") Ignored
                break

            except NetMikoAuthenticationException as nae:
                # lg(f"{ip}:{type(nae).__name__}") Ignored
                if auth_index < len(self.cf.auth_dict):
                    auth_index += 1
                    continue
                else:
                    break

            except ReadTimeout as rt:
                # lg(f"{ip}:{type(rt).__name__}") Ignored
                break
            
            except KeyError as ke:
                lg(f"{ip}:{type(ke).__name__}")
                with self.sw_con_lock:
                    if ip in self.sw_con:
                        del self.sw_con[ip]
                break
                
                
            except Exception as e:
                lg(f"{ip}:{type(e).__name__}")
                break

    def get_dns_name(self, ip):
        result = "None"
        try:
            name = socket.gethostbyaddr(ip)
            result = name[0].replace(self.cf.domain, "")
        except Exception as e:
            lg(type(e).__name__)
            result = "---------------"

        return result

    @method_logger
    def case_switch_ips(self, dns_mode=False) -> None:
        counter = 1
        connect_failed = 0
        ready_data = {}
        switch_ips = []
        user_special_ip = input("Enter Special Switch IP or Enter: ")
        if user_special_ip == "":
            self.scan_network()
            switch_ips = self.cf.all_switches
        else:
            switch_ips.append(user_special_ip)

        dns_i = 0
        dt = self.get_datetime()
        date_time = f"{dt['unix']}"
        ip_text_file = ""
        for hip in switch_ips:
            try:
                connect = self.__cnt(hip)
                if connect is None:
                    connect_failed += 1
                    if connect_failed == 3:
                        print(f"--- - IP: {hip:<18} You can't connect to switch!")
                        break
                    else:
                        continue

                connect_failed = 0
                sidta = connect.send_command("show ip device tracking all")
                if "%" in sidta:
                    sidta = connect.send_command("show device-tracking database")

                pattern = re.compile(
                    r"(\d+\.\d+\.\d+\.\d+)"
                    r".*?"
                    r"([0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2})"
                    r".*?"
                    r"(\S*\/\S*)"
                )

                # date_time = f"{dt['unix']}"
                actives = ["ACTIVE", "Active", "active", "REACHABLE", "Reachable", "reachable"]
                for line in sidta.splitlines():
                    if any(state in line.split() for state in actives):
                        match = pattern.search(line)
                        if match:
                            ip, mac, port = match.groups()
                            if dns_mode:
                                dns_name = self.get_dns_name(ip)
                                imsp = f"{dns_name}|{hip}|{port}"
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
                                ready_data.update({ip: imsp})
                                line = f"{counter:<4}- IP: {ip:<18} MAC: {mac:<18} Switch: {hip:<18} Port: {port:<25}"
                                ip_text_file += f"{line}\n"
                                print(line)
                                counter += 1
            except KeyboardInterrupt as ki:
                lg(type(ki).__name__)
                break
            
            except Exception as e:
                lg(type(e).__name__)
                pass

        if dns_mode == False:
            self.db.insert_ipdata(ready_data, {}, date_time, dt['dati'])
        if connect_failed < 3:
            if dns_mode:
                with open(f"{self.cf.recordDNS_dir}IP-DNS_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(ip_text_file)
            else:
                with open(f"{self.cf.ips_dir}IP-List_{dt['date']}-{dt['time']}.txt", "a") as file:
                    file.write(ip_text_file)
                    
        input("Press any key to exit ..")

    @method_logger
    def switch_ips_worker(self) -> None:
        lg("Started!")
        self.cf.renew_all_switches += 1
        if self.cf.renew_all_switches > self.cf.renew_all_switches_interval:
            self.cf.renew_all_switches = 1
            self.scan_network()
            
        connect_failed = 0
        ready_data = {}
        sw_statuse = {}
        switch_ips = self.cf.all_switches.copy()

        dt = self.get_datetime()
        date_time = f"{dt['unix']}"

        for hip in switch_ips:
            sw_statuse_helper = {}
            try:
                connect = self.__cnt(hip)
                if connect is None:
                    connect_failed += 1
                    if connect_failed == 3:
                        break
                    else:
                        continue

                connect_failed = 0
                temp = self.__get_switch_temp(hip)
                cpu = self.__get_switch_cpu(hip)
                ram = self.__get_switch_ram(hip)
                sw_statuse_helper.update({"tmp":temp})
                sw_statuse_helper.update({"cpu":cpu})
                sw_statuse_helper.update({"ram":ram})
                sw_statuse.update({hip:sw_statuse_helper})
                
                sidta = connect.send_command("show ip device tracking all")
                if "%" in sidta:
                    sidta = connect.send_command("show device-tracking database")
                

                pattern = re.compile(
                    r"(\d+\.\d+\.\d+\.\d+)"
                    r".*?"
                    r"([0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2})"
                    r".*?"
                    r"(\S*\/\S*)"
                )

                actives = ["ACTIVE", "Active", "active", "REACHABLE", "Reachable", "reachable"]
                for line in sidta.splitlines():
                    if any(state in line.split() for state in actives):
                        match = pattern.search(line)
                        if match:
                            ip, mac, port = match.groups()
                            imsp = f"{ip}|{mac}|{hip}|{port}"
                            ready_data.update({ip: imsp})
            except Exception as e:
                lg(f"IP: {hip}, {type(e).__name__}")
                if hip == switch_ips[-1]:
                    break
                else:
                    continue
                
        self.db.insert_ipdata(ready_data, sw_statuse, date_time, dt['dati'])
        if connect_failed < 3:
            pass

    @method_logger
    def case_access_list_manager(self) -> None:
        self.ter_cls()
        uc_msg = "Please select on of below:\n"
        uc_msg += "1. View switch access-list and rules\n"
        uc_msg += "2. Add switch access-list\n"
        uc_msg += "3. Add access-list rule\n"
        uc_msg += "4. Delete access-list\n"
        uc_msg += "5. Delete access-list rule\n"
        uc_msg += "d. Debug\n"
        uc_msg += "e. Exit\n"
        uc_msg += "Enter your choose: "
        while True:
            user_case = input(uc_msg)
            match user_case:
                case "1":
                    while True:
                        user_ip = input("Enter switch ip (e:exit): ")
                        print()
                        if user_ip == "e":
                            break
                        connect = self.__cnt(user_ip)
                        result = self.__get_switch_access_list_dict(connect)
                        for key, values in result.items():
                            print(key)
                            for index, value in enumerate(values):
                                branch = "└── " if index == len(values) - 1 else "├── "
                                print(f"{branch}{value}")
                            print()

                case "2":
                    user_ip = input("Enter switch ip (e:exit): ")
                    if user_ip == "e":
                        break

                    while True:
                        ia = 1
                        self.ter_cls()
                        print(f"Current Access-List (IP: {user_ip}):")
                        connect = self.__cnt(user_ip)
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
                        connect.save_config()

                case "3":
                    user_ip = input("Enter switch ip (e:exit): ")
                    if user_ip == "e":
                        break

                    connect = self.__cnt(user_ip)
                    result = self.__get_switch_access_list_dict(connect)

                    print(f"Current Access-List (IP: {user_ip}):")
                    d_acl = {}
                    ia = 1
                    for key in result.keys():
                        print(f"{ia:<2}. {key}")
                        d_acl[ia] = key
                        ia += 1

                    try:
                        acl_num = int(input("Choose access-list number: "))
                    except ValueError:
                        print("Your number is invalid!")
                        continue

                    if acl_num not in d_acl:
                        print("Your acl not in switch")
                        continue

                    acl_name = d_acl[acl_num]

                    prefix = "Extended IP access list "
                    if acl_name.startswith(prefix):
                        acl_name = acl_name[len(prefix):].strip()

                    print("\nEnter rule to add below this ACL.")
                    print("Example:")
                    print("permit tcp any any eq 80")
                    print("deny ip any any")
                    rule = input("Enter rule: ")

                    config_commands = [f"ip access-list extended {acl_name}", rule]
                    connect.send_config_set(config_commands)
                    self.__save(connect)

                case "4":
                    user_ip = input("Enter switch ip (e:exit): ")
                    if user_ip == "e":
                        break

                    connect = None
                    while True:
                        ia = 1
                        os.system('cls')
                        d_acl = {}
                        print(f"Current Access-List (IP: {user_ip}):")
                        if connect == None:
                            connect = self.__cnt(user_ip)
                        result = self.__get_switch_access_list_dict(connect)
                        for key in result.keys():
                            print(f"{ia:<2}. {key}")
                            d_acl.update({ia: key})
                            ia += 1
                        user_case_delete = input("Enter number of access-list for delete (e:exit): ")
                        if user_case_delete == "e":
                            break
                        user_case_delete = int(user_case_delete)
                        user_config = self.__set_aclConfig_aclComand(d_acl[user_case_delete])
                        print(f"log: {user_config} is running ..")
                        connect.send_config_set(user_config)
                        print(f"log: saving switch config!")
                        self.__save(connect)

                case "5":
                    user_ip = input("Enter switch ip (e:exit): ")
                    if user_ip == "e":
                        break

                    connect = self.__cnt(user_ip)

                    while True:
                        self.ter_cls()
                        result = self.__get_switch_access_list_dict(connect)

                        if not result:
                            print("No access-list found.")
                            input("\nPress Enter to continue...")
                            break

                        print(f"Current Access-List and Rules (IP: {user_ip}):\n")
                        rules_map = {}

                        for acl_index, (acl_name, rules) in enumerate(result.items(), start=1):
                            print(f"{acl_index}. {acl_name}")

                            for rule_index, rule in enumerate(rules, start=1):
                                rule_number = acl_index * 10 + rule_index
                                rules_map[rule_number] = (acl_name, rule)
                                branch = "└── " if rule_index == len(rules) else "├── "
                                print(f"   {branch}{rule_number}. {rule}")
                            print()

                        user_choice = input("Enter rule number to delete (e:exit): ").strip()
                        if user_choice.lower() == "e":
                            break

                        try:
                            rule_number = int(user_choice)
                        except ValueError:
                            print("Invalid number!")
                            time.sleep(1.5)
                            continue

                        if rule_number not in rules_map:
                            print("Rule number not found!")
                            time.sleep(1.5)
                            continue

                        target_acl, target_rule = rules_map[rule_number]
                        target_acl_clean = target_acl.split()[-1]
                        sequence_number = target_rule.strip().split()[0]
                        delete_commands = [f"ip access-list extended {target_acl_clean}", f"no {sequence_number}",]
                        connect.send_config_set(delete_commands)
                        self.__save(connect)

                case "d":
                    user_ip = input("Enter switch ip (e:exit): ")
                    connect = self.__cnt(user_ip)
                    connect.config_mode()
                    input()

                case "e":
                    break

    def __save(self, connect: BaseConnection):
        output = connect.send_command_timing("copy running-config startup-config")
        if "Destination filename" in output:
            output += connect.send_command_timing("\n")

    def __set_aclConfig_aclComand(self, sw_config):
        sw_conf_list = sw_config.split(" ")
        if sw_conf_list[0] == "Extended":
            return f"no ip access-list extended {sw_conf_list[-1]}"

    def __get_switch_access_list_dict(self, connect: BaseConnection):
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

    @method_logger
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
                        connect = self.__cnt(ip)
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

                        cases_str = ", ".join(f"{item:<3}" for item in nfind)
                        txt_helper = f"ip: {ip:<18}, Model: {model:<20}, Count {len(nfind):<4}, Cases: {cases_str}"
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
                        connect = self.__cnt(ip)
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

                        cases_str = ", ".join(f"{item:<3}" for item in nfind)
                        txt_helper = f"ip: {ip:<18}, Model: {model:<20}, Count {len(nfind):<4}, Cases: {cases_str}"
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
                        connect = self.__cnt(ip)
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
                        connect = self.__cnt(ip)
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

                case ("set", "switch", "-", "new"):
                    if funcs[4] == "all":
                        self.scan_network()
                        all_ip = self.cf.all_switches
                    else:
                        all_ip = [funcs[4]]

                    for i, ip in enumerate(all_ip):
                        connect = self.__cnt(ip)
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
                        connect = self.__cnt(ip)
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
                
                case ("set", "switch", "-", "all"):
                    target_ips = self.cf.all_switches
                    if funcs[4] == "all":
                        for i, ip in enumerate(target_ips):
                            try:
                                connect = self.__cnt(ip)
                                if connect is None:
                                    continue

                                print(f"{i:<3} - {ip:<15} is opened: ", end="")
                                configs_lines = lines[2:]
                                connect.send_config_set(configs_lines)
                                connect.save_config()
                                print(f"set config and saved!")
                            except Exception as e:
                                lg(type(e).__name__)
                        input("press any key to continue ..")

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

    @method_logger
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

    @method_logger
    def coreGetSwitchesBackup(self):
        self.scan_network()
        switches = self.cf.all_switches

        dt = self.get_datetime()
        counter = 1
        for ip in switches:
            connect = self.__cnt(ip)
            if connect != None:
                try:
                    version_data = connect.send_command("show version")
                    hostname = self.find_hostname(version_data)
                    print(f"{counter:<3} - {hostname:<30} create ", end="")
                    self.coreWriteFile(f"{self.cf.version_dir}{hostname}-version_{dt['date']}-{dt['time']}.txt", version_data)
                    print("version, ", end="")

                    running_config_data = connect.send_command("show running-config")
                    self.coreWriteFile(f"{self.cf.switchconfig_dir}{hostname}-config_{dt['date']}-{dt['time']}.txt", running_config_data)
                    print("config, ", end="")

                    interface_status_data = connect.send_command("show interfaces status")
                    self.coreWriteFile(f"{self.cf.interface_dir}{hostname}-interface_{dt['date']}-{dt['time']}.txt", interface_status_data)
                    print("interfaces, ", end="")

                    vlan_brief_data = connect.send_command("show vlan brief")
                    self.coreWriteFile(f"{self.cf.vlans_dir}{hostname}-vlan_{dt['date']}-{dt['time']}.txt", vlan_brief_data)
                    print("vlans, ", end="")

                    show_cdp_data = connect.send_command("show cdp neighbors detail")
                    self.coreWriteFile(f"{self.cf.switchcdp_dir}{hostname}-cdp_{dt['date']}-{dt['time']}.txt", show_cdp_data)
                    print("cdp, ", end="")

                    ip_data = ""
                    try:
                        ip_data = connect.send_command("show ip device tracking all")

                    except Exception as e:
                        lg(type(e).__name__)
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
                    counter += 1
                except Exception as e:
                    lg(type(e).__name__)
                    pass

        input("Task finished! press Enter to continue ..")
        os.system('cls')

    @method_logger
    def coreSearchSwitchesIPsDatabase(self):
        self.ter_cls()
        dt = self.get_datetime()
        while True:
            result = "\n"
            counter = 1
            key = input("Insert a IP, MAC, Switch or 'e' for exit: ")
            try:
                if key == "e":
                    break
                else:
                    line_data = self.db.getDataFromIpDataTable(key)
                    for ld in line_data:
                        list_data = ld[1].split("|")
                        ip_age = int((int(ld[3]) - int(ld[2])) / 86400)
                        insert_age = int((int(dt['unix']) - int(ld[2])) / 86400)
                        update_age = int((int(dt['unix']) - int(ld[3])) / 86400)
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
                lg(type(e).__name__)
                continue

    @method_logger
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
                    lg(type(e).__name__)
                    print(f"Error executing query: {e}\n")
