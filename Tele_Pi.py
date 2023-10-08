#!/usr/bin/python3

import re
import os
import logging
import subprocess
import time
import requests
import psutil
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define command groups
system_commands = [
    {"name": "/update", "description": "Update the system"},
    {"name": "/reboot", "description": "reboots the system"},
    {"name": "/shutdown", "description": "Shuts the system down"},
    {"name": "/disk_usage", "description": "Show disk usage"},
    {"name": "/current_directory_usage", "description": "Show current directory usage"},
    {"name": "/free_memory", "description": "Show free memory"},
    {"name": "/show_processes", "description": "Show all processes"},
    {"name": "/show_system_services", "description": "Show system services"},
    {"name": "/start_monitoring", "description": "Start CPU temperature monitoring"},
    {"name": "/stop_monitoring", "description": "Stop CPU temperature monitoring"},    
    {"name": "/start_monitoring_ram", "description": "Start RAM monitoring"},
    {"name": "/stop_monitoring_ram", "description": "Stop RAM monitoring"}
]

network_commands = [
    {"name": "/show_network_info", "description": "Show network information"},
    {"name": "/ip", "description": "Show IP addresses"},
    {"name": "/wifi", "description": "Show list of available wifi access points"},
    {"name": "/show_bluetooth_devices", "description": "Show list of available Bluetooth devices"},
    {"name": "/external_ip", "description": "Show external IP address"},
    {"name": "/ping", "description": "Pings a remote host /ping IP or hostname"}
]

utility_commands = [
    {"name": "/echo", "description": "Echo back the user's message"},
    {"name": "/speedtest", "description": "Run speedtest"},
    {"name": "/uptime", "description": "Show system uptime"}
]

def start(update, context):
    # Send welcome message and command groups keyboard
    message = "Hi, I'm a bot. Please talk to me!\n"
    message += "Available commands:\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    
    keyboard = [[InlineKeyboardButton("System", callback_data="system"),
                 InlineKeyboardButton("Network", callback_data="network"),
                 InlineKeyboardButton("Utility", callback_data="utility")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Choose a command group:", reply_markup=reply_markup)

def button_callback(update, context):
    # Handle callback queries from command groups keyboard
    query = update.callback_query
    query.answer()
    if query.data == "system":
        message = "System commands:\n\n"
        for command in system_commands:
            message += f"{command['name']} - {command['description']}\n"
    elif query.data == "network":
        message = "Network commands:\n\n"
        for command in network_commands:
            message += f"{command['name']} - {command['description']}\n"
    elif query.data == "utility":
        message = "Utility commands:\n\n"
        for command in utility_commands:
            message += f"{command['name']} - {command['description']}\n"
    else:
        message = "Invalid command group"
    context.bot.send_message(chat_id=query.message.chat_id, text=message)

def echo(update, context):
    # Echo back the user's message
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def external_ip(update, context):
    # Show external IP address
    url = 'https://api.ipify.org'
    try:
        response = requests.get(url)
        ip = response.text
        context.bot.send_message(chat_id=update.effective_chat.id, text=ip)
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Could not retrieve external IP address: {e}")
        
def update(update, context):
    # Update the system
    context.bot.send_message(chat_id=update.effective_chat.id, text="Updating the system, please wait...")
    process = subprocess.Popen("sudo apt update && sudo apt upgrade -y", stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if error:
        context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred while updating.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Update complete.\n" + str(output.decode("utf-8")))

def uptime(update, context):
    # Show system uptime
    output = subprocess.check_output(["uptime"])
    context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))

def speedtest(update, context):
    # Run speedtest and return the result
    context.bot.send_message(chat_id=update.effective_chat.id, text="Running speedtest...")
    result = subprocess.run(["/usr/local/bin/speedtest-cli", "--secure"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    context.bot.send_message(chat_id=update.effective_chat.id, text=result.stdout.decode())

def disk_usage(update, context):
    # Show disk usage
    output = subprocess.check_output(["df", "-h"])
    context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))

def current_directory_usage(update, context):
    # Show current directory usage
    output = subprocess.check_output(["du", "-sh"])
    context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))

def free_memory(update, context):
    # Show free memory
    output = subprocess.check_output(["free", "-m"])
    context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))

def show_processes(update, context):
    # Show all processes
    output = subprocess.check_output(["ps", "-ef"]).decode("utf-8")
    chunks = [output[i:i + 4096] for i in range(0, len(output), 4096)]
    for chunk in chunks:
        context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)

def ip(update, context):
    result = subprocess.run(["ip", "a"], stdout=subprocess.PIPE)
    context.bot.send_message(chat_id=update.effective_chat.id, text=result.stdout.decode())

def show_network_info(update, context):
    # Show network information
    output = subprocess.check_output(["ifconfig"])
    context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))

def show_system_services(update, context):
    # Show system services
    output = subprocess.check_output(["systemctl", "list-units"])
    output = output.decode("utf-8").split("\n")
    for line in output:
        context.bot.send_message(chat_id=update.effective_chat.id, text=line, timeout=20)
        time.sleep(0.2)  # Add a small delay between messages to avoid flooding

THRESHOLD_TEMP = 62  # Celsius

# Global flag variable to stop the monitoring thread
monitoring = True

def monitor_cpu_temp(update, context):
    # Monitor CPU temperature
    while True:
        temp = psutil.sensors_temperatures()["cpu_thermal"][0].current
        if temp > THRESHOLD_TEMP:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"CPU temperature is too high ({temp}°C)")
        time.sleep(60)

def start_monitoring(update, context):
    # Start monitoring CPU temperature
    global monitoring
    monitoring = True
    thread = threading.Thread(target=monitor_cpu_temp, args=(update, context))
    thread.start()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Started monitoring CPU temperature")

def stop_monitoring(update, context):
    # Stop monitoring CPU temperature
    global monitoring
    monitoring = False
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stopped monitoring CPU temperature")

def show_bluetooth_devices(update, context):
    # Send "Scanning..." message to indicate that the program is scanning for devices
    context.bot.send_message(chat_id=update.effective_chat.id, text="Scanning for Bluetooth devices...")

    # Start Bluetooth scan
    subprocess.Popen(["bluetoothctl", "scan", "on"])

    # Wait for 20 seconds to allow time for the scan to complete
    time.sleep(20)

    # Show list of available Bluetooth devices with type information
    output = subprocess.check_output(["bluetoothctl", "devices"])
    output = output.decode("utf-8")
    devices_with_type = []
    for line in output.split("\n"):
        match = re.search(r"Device\s+([0-9A-F:]{17})\s+(.+)", line)
        if match:
            mac_address = match.group(1)
            device_name = match.group(2)
            device_type_output = subprocess.check_output(["bluetoothctl", "info", mac_address])
            device_type_output = device_type_output.decode("utf-8")
            device_type_match = re.search(r"\s+Class:\s+(\w+)", device_type_output)
            device_type = device_type_match.group(1) if device_type_match else "Unknown"
            devices_with_type.append(f"{device_name} ({device_type})")
    if devices_with_type:
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(devices_with_type))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No devices found.")

def wifi(update, context):
    # Send "Scanning..." message to indicate that the program is scanning for access points
    context.bot.send_message(chat_id=update.effective_chat.id, text="Scanning for WiFi access points...")

    # Start the wifi scan
    subprocess.Popen(["sudo", "iwlist", "wlan1", "scan"])

    # Wait for 20 seconds to allow time for the scan to complete
    time.sleep(20)

    # Show list of available wifi access points with encryption type
    output = subprocess.check_output(["sudo", "iwlist", "wlan1", "scan"])
    output = output.decode("utf-8")
    lines = output.split("\n")
    essids_with_encryption = []
    for i in range(len(lines)):
        if "ESSID" in lines[i]:
            essid = lines[i].split(":")[1].strip().strip('"')
            if essid:
                encryption = "Not encrypted"
                for j in range(i, len(lines)):
                    if "Encryption key:" in lines[j]:
                        if "on" in lines[j]:
                            encryption = "WPA/WPA2"
                        else:
                            encryption = "WEP"
                        break
                essids_with_encryption.append(f"{essid} ({encryption})")
    if essids_with_encryption:
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(essids_with_encryption))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No ESSIDs found")
       
def reboot(update, context):
    # Reboot the system
    context.bot.send_message(chat_id=update.effective_chat.id, text="Rebooting the system, please wait...")
    subprocess.run(["sudo", "reboot"])

def shutdown(update, context):
    # Shutdown the system
    context.bot.send_message(chat_id=update.effective_chat.id, text="Shutting down the system, please wait...")
    subprocess.run(["sudo", "shutdown", "-h", "now"])
    
def ping(update, context):
    host = context.args[0]  # Get the host to ping from the user's input
    process = subprocess.Popen(["ping", "-c", "4", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred while pinging.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=output.decode("utf-8"))
        
THRESHOLD_RAM = 80  # percent

def monitor_ram_usage(update, context):
    # Monitor RAM usage
    while monitoring:
        ram_usage = psutil.virtual_memory().percent
        if ram_usage > THRESHOLD_RAM:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"RAM usage is too high ({ram_usage}%)")
        time.sleep(60)
        
def start_monitoring_ram(update, context):
    # Start monitoring RAM usage
    global monitoring
    monitoring = True
    thread = threading.Thread(target=monitor_ram_usage, args=(update, context))
    thread.start()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Started monitoring RAM usage")

def stop_monitoring_ram(update, context):
    # Stop monitoring RAM usage
    global monitoring
    monitoring = False
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stopped monitoring RAM usage")



def help(update, context):
    # Show list of available commands
    message = "Available commands:\n"
    message += "/start - Start the bot\n"
    message += "/echo - Echo back the user's message\n"
    message += "/update - Update the system\n"
    message += "/reboot - Reboots the system\n"
    message += "/shutdown - Shuts the system down\n"
    message += "/help - Show this message\n"
    message += "/disk_usage - Show disk usage\n"
    message += "/current_directory_usage - Show current directory usage\n"
    message += "/free_memory - Show free memory\n"
    message += "/show_processes - Show all processes\n"
    message += "/show_network_info - Show network information\n"
    message += "/show_system_services - Show system services\n"
    message += "/speedtest - Run speedtest\n"
    message += "/ip - Show IP addresses\n"
    message += "/uptime - Show system uptime\n"
    message += "/external_ip - Show external IP address\n"
    message += "/start_monitoring - Start CPU Monitoring\n"
    message += "/stop_monitoring - Stop CPU monitor\n"
    message += "/show_bluetooth_devices - Show list of available Bluetooth devices\n"
    message += "/wifi - Show list of available wifi access points\n"
    message += "/ping - ping a remote host\n"
    message += "/start_monitoring_ram - Start RAM monitoring\n"
    message += "/stop_monitoring_ram - Stop RAM monitoring\n"
    
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("BOT-ID-HERE", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add command handler to start function
    dp.add_handler(CommandHandler("start", start))

    # Add command handler to echo function
    dp.add_handler(CommandHandler("echo", echo))

    # Add command handler to update function
    dp.add_handler(CommandHandler("update", update))

    # Add command handler to help function
    dp.add_handler(CommandHandler("help", help))

    # Add command handler to speedtest function
    dp.add_handler(CommandHandler("speedtest", speedtest))

     # Add command handler to disk_usage function
    dp.add_handler(CommandHandler("disk_usage", disk_usage))

    # Add command handler to current_directory_usage function
    dp.add_handler(CommandHandler("current_directory_usage", current_directory_usage))

    # Add command handler to free_memory function
    dp.add_handler(CommandHandler("free_memory", free_memory))

    # Add command handler to show_processes function
    dp.add_handler(CommandHandler("show_processes", show_processes))

    # Add command handler to show_network_info function
    dp.add_handler(CommandHandler("show_network_info", show_network_info))

    # Add command handler to show_system_services function
    dp.add_handler(CommandHandler("show_system_services", show_system_services))

    # Add command handler to ip function
    dp.add_handler(CommandHandler("ip", ip))

    # Add command handler to uptime function
    dp.add_handler(CommandHandler("uptime", uptime))

    # Add command handler to external_ip function
    dp.add_handler(CommandHandler("external_ip", external_ip))

    # Add command handler to show_bluetooth_devices function
    dp.add_handler(CommandHandler("show_bluetooth_devices", show_bluetooth_devices))

    # Add command handler to wifi function
    dp.add_handler(CommandHandler("wifi", wifi))
    
    # Add CallbackQueryHandler to button_callback function
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    # Add command handler to start_monitoring function
    dp.add_handler(CommandHandler("start_monitoring", start_monitoring))

    # Add command handler to stop_monitoring function
    dp.add_handler(CommandHandler("stop_monitoring", stop_monitoring))
    
    # Add command handler to reboot function
    dp.add_handler(CommandHandler("reboot", reboot))

    # Add command handler to shutdown function
    dp.add_handler(CommandHandler("shutdown", shutdown))
    
    # Add command handler to ping function
    dp.add_handler(CommandHandler("ping", ping))
    
    # Add command handler to ping function
    dp.add_handler(CommandHandler("start_monitoring_ram", start_monitoring_ram))
    
    # Add command handler to ping function
    dp.add_handler(CommandHandler("stop_monitoring_ram", stop_monitoring_ram))
             
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()   

