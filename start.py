import argparse
import menu
import os
import sys
import time
from bot import Bot


async def startup():
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", help="run this silently", action="store_true")
    args = parser.parse_args()
    if args.silent:
        bot = Bot()
        await bot.start()
        sys.exit(0)
    menu.clear()
    print("\nWelcome to Music Monkey!\n------------------------\n")
    create_and_check_config()
    input("Press Enter to continue...")
    menu.draw_main()


def check_config():
    menu.config.read(menu.config_file)
    time.sleep(1)
    if menu.config.get("general", "discord_token") == "N/A":
        print("Discord Account token not configured.\n")
    if menu.config.get("general", "bot_channel_id") == "N/A":
        print("Discord Bot channel not configured.\n")
    time.sleep(1)


def create_and_check_config():
    if not os.path.exists(menu.config_file):
        menu.config.add_section("general")
        menu.config.add_section("logging")
        menu.config.set("general", "discord_token", "N/A")
        menu.config.set("general", "bot_channel_id", "N/A")
        menu.config.set("logging", "level", "INFO")
        with open(menu.config_file, "w") as configfile:
            menu.config.write(configfile)
    check_config()


if __name__ == "__main__":
    import asyncio
    asyncio.run(startup())
