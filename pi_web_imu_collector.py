import asyncio
import csv
from datetime import datetime
from flask import Flask, render_template_string, request
from bleak import BleakScanner, BleakClient
import threading

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
data_buffer = []
loop = asyncio.new_event_loop()  # Single persistent loop
thread = None

# IMU Notification Handler
def imu_handler(sender, data):
    global data_buffer
    try:
        readings_str = data.decode('utf-8')
        print(f"Raw data received: {readings_str}")  # Debug raw
        readings = readings_str.split(',')
        if len(readings) == 6:
            timestamp = datetime.now().isoformat()
            row = [timestamp] + readings
            data_buffer.append(row)
            print(f"IMU Data: {row}")
    except Exception as e:
        print(f"Decode error: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_connected, recording, data_buffer
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
                run_ble_task("start")
                message = "Recording started!" if recording else "Start failed."
            else:
                message = "Connect first!"
        elif action == 'stop':
            if recording:
                run_ble_task("stop")
                save_csv()
                message = "Stopped and saved to CSV."
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

def save_csv():
    global data_buffer
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'])
        writer.writerows(data_buffer)
    print(f"Saved {len(data_buffer)} rows to CSV.")
    data_buffer = []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)