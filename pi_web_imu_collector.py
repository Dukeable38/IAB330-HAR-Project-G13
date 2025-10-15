import asyncio
import os
import csv
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from bleak import BleakScanner, BleakClient

app = Flask(__name__)

# BLE Config
TARGET_NAME = "Nano33IoT_HAR"
SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
CMD_UUID = "19B10003-E8F2-537E-4F6C-D104768A1214"
IMU_UUID = "19B10004-E8F2-537E-4F6C-D104768A1214"

client = None
is_connected = False
recording = False
csv_file = 'imu_data.csv'
data_buffer = []  # Buffer data before writing

# IMU Notification Handler
def imu_handler(sender, data):
    global data_buffer
    try:
        readings = data.decode('utf-8').split(',')
        if len(readings) == 6:
            timestamp = datetime.now().isoformat()
            row = [timestamp] + readings
            data_buffer.append(row)
            print(f"IMU Data: {row}")
    except Exception as e:
        print(f"Decode error: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_connected, recording, client, data_buffer
    message = ""
    if request.method == 'POST':
        action = request.form['action']
        if action == 'connect':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(connect_device())
            message = "Connected!" if is_connected else "Connection failed."
        elif action == 'start':
            if is_connected:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_recording())
                message = "Recording started!"
            else:
                message = "Connect first!"
        elif action == 'stop':
            if recording:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(stop_recording())
                save_csv()
                message = "Recording stopped and saved to CSV."
            else:
                message = "Not recording!"

    return render_template_string("""
    <!doctype html>
    <html>
    <head><title>HAR IMU Collector</title></head>
    <body>
    <h1>HAR IMU Data Collector</h1>
    <p>Status: {{ 'Connected' if is_connected else 'Disconnected' }} | Recording: {{ 'Yes' if recording else 'No' }}</p>
    <p>{{ message }}</p>
    <form method="post">
        <button name="action" value="connect">Connect to Nano</button>
        <button name="action" value="start">Start Recording</button>
        <button name="action" value="stop">Stop Recording</button>
    </form>
    </body>
    </html>
    """, is_connected=is_connected, recording=recording, message=message)

async def connect_device():
    global client, is_connected
    try:
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name == TARGET_NAME:
                client = BleakClient(d.address)
                await client.connect(timeout=60.0)
                is_connected = True
                return
        print("Device not found.")
    except Exception as e:
        print(f"Connection error: {e}")
        is_connected = False

async def start_recording():
    global recording
    try:
        await client.write_gatt_char(CMD_UUID, bytearray([1]))
        await client.start_notify(IMU_UUID, imu_handler)
        recording = True
    except Exception as e:
        print(f"Start error: {e}")

async def stop_recording():
    global recording
    try:
        await client.write_gatt_char(CMD_UUID, bytearray([0]))
        await client.stop_notify(IMU_UUID)
        recording = False
    except Exception as e:
        print(f"Stop error: {e}")

def save_csv():
    global data_buffer
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'])
        writer.writerows(data_buffer)
    data_buffer = []  # Clear buffer

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)