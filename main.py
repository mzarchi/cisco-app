from config import Config
from core import Core, App_DB
from netmiko import ConnectHandler


ad = App_DB()
cr = Core()

if not ad.count_user():
    user_data = {}
    username = cr.get_current_text("Please inser your username: ")
    user_data.update({'username': username})
    password = cr.get_current_text("Please inser your password: ", False)
    user_data.update({'password': password})
    secret = cr.get_current_text("Please inser your secret: ", False)
    user_data.update({'secret': password if secret == '' else secret})
    domain = cr.get_current_text("Please inser your domain: ")
    user_data.update({'domain': domain})
    sw_core = cr.get_current_text("Please inser your SW-Core IP: ")
    user_data.update({'sw_core': sw_core})
    subnet = cr.get_current_text("Please inser your IP subnet: ")
    user_data.update({'subnet': subnet})
    csv_name = cr.get_current_text("Please inser your CSV name: ")
    user_data.update({'csv_name': csv_name})

    ad.insert_user_data(user_data)