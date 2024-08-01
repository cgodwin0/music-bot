import configparser
import os
import sys
import time
from bot import Bot

config_file = os.getcwd() + os.path.sep + "conf" + os.path.sep + "config.cfg"
config = configparser.RawConfigParser()


def draw_main():
    while True:
        clear()
        print("\tMain Menu\n      =============\n")
        print("\n1.....................Configure\n")
        print("2.....................Launch!\n\n")
        print("Choose an option. X to Exit")
        val = input("> ")
        if val == "x":
            sys.exit(0)
        if val == "1":
            draw_configure()
        if val == "2":
            print("Launching Music Monkey...")
            time.sleep(1)
            bot = Bot()
            clear()
            bot.start()
            sys.exit(0)
        else:
            print("Invalid Option")
            time.sleep(1)


def draw_configure():
    while True:
        clear()
        print("\tSettings\n      =============\n")
        print("\n1.....................General\n")
        print("2.....................Logging\n\n")
        print("Choose an option. X to go back")
        val = input("> ")
        if val == "x":
            draw_main()
        if val == "1":
            draw_general()
        if val == "2":
            draw_logging()
        else:
            print("Invalid Option")
            time.sleep(1)


def draw_general():
    config.read(config_file)
    while True:
        clear()
        item_list = config.items("general")
        option = 0
        print("\tGeneral Settings\n      ====================\n\n")
        for item in item_list:
            option += 1
            print(
                str(option) + "....................." + item[0] + ": " + item[1] + "\n"
            )
        print("S to save. X to go back")
        val = input("> ")
        if val == "x":
            draw_configure()
        if val == "s":
            with open(config_file, "w") as configfile:
                config.write(configfile)
            print("Saved.")
            time.sleep(1)
            draw_configure()
        try:
            if int(val) in range(1, 8):
                setting = input(item_list[int(val) - 1][0] + " > ")
                config.set("general", item_list[int(val) - 1][0], setting)
                continue
        except ValueError:
            print("Invalid Option")
            time.sleep(1)
        else:
            print("Invalid Option")
            time.sleep(1)


def draw_logging():
    config.read(config_file)
    while True:
        clear()
        item_list = config.items("logging")
        print("\tLogging Settings\n      ====================\n\n")
        print(
            "1......................" + item_list[0][0] + ": " + item_list[0][1] + "\n"
        )
        print("S to save. X to go back")
        val = input("> ")
        if val == "1":
            setting = input(item_list[0][0] + " > ").upper()
            if setting not in ["INFO", "DEBUG"]:
                print("Invalid Entry. Must be DEBUG or INFO")
                time.sleep(1)
                continue
            config.set("logging", item_list[0][0], setting)
            continue
        if val == "x":
            draw_configure()
        if val == "s":
            with open(config_file, "w") as configfile:
                config.write(configfile)
            print("Saved.")
            time.sleep(1)
            draw_configure()
        else:
            print("Invalid Option")
            time.sleep(1)


def clear():
    if os.name == "nt":
        _ = os.system("cls")

    else:
        _ = os.system("clear")
