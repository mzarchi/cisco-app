from config import Config as cf
from core import Core
from netmiko import ConnectHandler

cr = Core()
cr.scan_network()

switches = cf.all_switches
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
            cr.find_hostname(version_data)
            content = connect.send_command("show cdp neighbors detail")
            # content = cr.read_file(cf.root_dir, "sample.txt")
            sw_text = cr.manage_content(content)
            cr.write_result(sw_text)
        except Exception as e:
            print(f"- Error in {ip}: {e}")
            continue
