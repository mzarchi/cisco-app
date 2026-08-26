from config import Config
#from core import Core
from encrypt import Encryption

import sqlite3
import sys

class Database:
    cf = Config()
    conn = None
    cursor = None
    #cr = None

    def __init__(self):
        try:
            #self.cr = Core()
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
                                    update_date TEXT NOT NULL,
                                    edit_field TEXT NOT NULL)
                                """)

            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS dns_data (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    imsp TEXT NOT NULL,
                                    insert_date TEXT NOT NULL,
                                    update_date TEXT NOT NULL)
                                """)
            
            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS app_variables (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    interval_switch_ip TEXT NOT NULL)
                                """)
            self.__close()
            
            self.init_app_variables()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-create_tables: {e}")
            sys.exit(1)

    def init_app_variables(self):
        self.__open()
        self.cursor.execute("SELECT * FROM app_variables")
        row = self.cursor.fetchone()
        if not row:
            self.cursor.execute("""INSERT INTO app_variables (interval_switch_ip) VALUES (?)""", ("240",))
        self.__close()
            
    def get_app_variables(self):
        try:
            self.__open()
            self.cursor.execute("SELECT * FROM app_variables WHERE id = 1")
            row = self.cursor.fetchone()
            self.__close()
            return row
        except Exception as e:
            pass
        
    def set_app_variables(self, value):
        try:
            self.__open()
            self.cursor.execute("UPDATE app_variables SET interval_switch_ip = ? WHERE id = 1", (value,))
            self.__close()
        except Exception as e:
            pass
        
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
            self.cursor.execute("SELECT * FROM switches_list WHERE mac = ?", (data['mac'],))

            row = self.cursor.fetchone()
            if row:
                self.cursor.execute("UPDATE switches_list SET update_date = ? WHERE mac = ?", (data['update_date'], data['mac']))
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
            self.cursor.execute("INSERT INTO switch_links (link, insert_date, update_date) VALUES (?, ?, ?)", (link, datetime, datetime))
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_switch_link: {e}")
            sys.exit(1)

    def manage_switch_link(self, link, datetime):
        update = False
        try:
            self.__open()
            self.cursor.execute("SELECT * FROM switch_links WHERE link = ?", (link,))

            row = self.cursor.fetchone()
            if row:
                self.cursor.execute("UPDATE switch_links SET update_date = ? WHERE link = ?", (datetime, link))
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
            self.cursor.execute("SELECT * FROM ip_domain WHERE ip_subnet = ?", (data['ip_subnet'],))
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
            self.cursor.execute("DELETE FROM admin_data WHERE username = ?", (username,))
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
        #self.cr.log("core[]:App_DB{}:set_dict_ipsubnet_data()")
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
            self.cursor.execute("DELETE FROM ip_domain WHERE ip_subnet = ?", (ipsubnet,))
            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-del_ipsubnet_data: {e}")
            sys.exit(1)

    def insert_ipdata(self, data:dict, date_time, edit_field):
        try:
            self.__open()
            for imsp in data.values():
                self.cursor.execute("SELECT * FROM ip_data WHERE imsp = ?", (imsp,))
                row = self.cursor.fetchone()

                if not row:
                    self.cursor.execute("INSERT INTO ip_data (imsp, insert_date, update_date, edit_field) VALUES (?, ?, ?, ?)", (imsp, date_time, date_time, edit_field,))
                else:
                    self.cursor.execute("UPDATE ip_data SET update_date = ?, edit_field = ? WHERE imsp = ?", (date_time, edit_field, imsp,))

            self.__close()
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_ipdata_worker: {e}")
            sys.exit(1)
            
    def insert_dnsdata(self, imsp, date_time):
        try:
            new_imsp = False
            self.__open()
            self.cursor.execute("SELECT * FROM dns_data WHERE imsp = ?", (imsp,))
            row = self.cursor.fetchone()

            if not row:
                new_imsp = True
                self.cursor.execute("""INSERT INTO dns_data (imsp, insert_date, update_date) VALUES (?, ?, ?)""", (imsp, date_time, date_time,))
            else:
                self.cursor.execute("UPDATE dns_data SET update_date = ? WHERE imsp = ?", (date_time, imsp))

            self.__close()
            return new_imsp
        except Exception as e:
            print(f"- F-core, C-App_DB, D-insert_ipdata: {e}")
            sys.exit(1)

    def databaseGetIpData(self):
        self.__open()
        self.cursor.execute("SELECT * FROM ip_data")
        return self.cursor.fetchall()

    def getDataFromIpDataTable(self, mini):
        self.__open()
        query = "SELECT * FROM ip_data WHERE imsp LIKE ? ORDER BY update_date DESC"
        self.cursor.execute(query, ('%' + mini + '%',))
        #self.__close()
        return self.cursor.fetchall()

    def dbRunSqlQuery(self, query):
        self.__open()
        # return self.cursor.execute(query)

        try:
            # conn = sqlite3.connect('your_database.db')
            # cursor = conn.cursor()

            self.cursor.execute(query)

            query_type = query.strip().split()[0].upper()

            if query_type == "SELECT":
                result = self.cursor.fetchall()
                self.__close()
                return result
            else:
                # conn.commit()
                row_count = self.cursor.rowcount
                self.__close()
                return f"Success! {row_count} rows affected."

        except sqlite3.Error as e:
            return f"Database Error: {e}"
