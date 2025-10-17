import asyncio
import csv
from datetime import datetime
from flask import Flask, render_template_string, request
from bleak import BleakScanner, BleakClient
import matplotlib.animation as animation
import pandas as pd
import matplotlib.pyplot as plt

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
            print(f"Appended row: {row}")  # Debug appended
        else:
            print(f"Invalid length: {len(readings)}")  # Debug invalid
    except Exception as e:
        print(f"Handler error: {e}")


# Global fig and axes for live plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
line_ax, line_ay, line_az = ax1.plot([], [], 'r-', label='Accel X'), ax1.plot([], [], 'g-', label='Accel Y'), ax1.plot([], [], 'b-', label='Accel Z')
line_gx, line_gy, line_gz = ax2.plot([], [], 'r-', label='Gyro X'), ax2.plot([], [], 'g-', label='Gyro Y'), ax2.plot([], [], 'b-', label='Gyro Z')
ax1.legend(); ax1.set_title('Live Acceleration'); ax1.set_ylabel('g')
ax2.legend(); ax2.set_title('Live Gyroscope'); ax2.set_ylabel('dps'); ax2.set_xlabel('Samples')

def update_live_plot(frame):
    if data_buffer:
        df_live = pd.DataFrame(data_buffer, columns=['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'])
        index = range(len(df_live))
        line_ax[0].set_data(index, df_live['accel_x'])
        line_ay[0].set_data(index, df_live['accel_y'])
        line_az[0].set_data(index, df_live['accel_z'])
        ax1.relim(); ax1.autoscale_view()

        line_gx[0].set_data(index, df_live['gyro_x'])
        line_gy[0].set_data(index, df_live['gyro_y'])
        line_gz[0].set_data(index, df_live['gyro_z'])
        ax2.relim(); ax2.autoscale_view()
    return line_ax + line_ay + line_az + line_gx + line_gy + line_gz

ani = animation.FuncAnimation(fig, update_live_plot, interval=1000)  # Update every 1s
plt.show(block=False)  # Run in background

# BLE Tasks
async def ble_task(action):
    global client, is_connected, recording
    try:
        if action == "connect":
            devices = await BleakScanner.discover()
            for d in devices:
                if d.name == TARGET_NAME:
                    client = BleakClient(d.address)
                    await client.connect(timeout=60.0)
                    is_connected = True
                    print("Connected successfully!")
                    return
            print("Device not found.")
        elif action == "start" and is_connected:
            await client.write_gatt_char(CMD_UUID, bytearray([1]))
            await client.start_notify(IMU_UUID, imu_handler)
            recording = True
            print("Notifications started!")
        elif action == "stop" and recording:
            await client.write_gatt_char(CMD_UUID, bytearray([0]))
            await client.stop_notify(IMU_UUID)
            recording = False
            print("Notifications stopped!")
    except Exception as e:
        print(f"BLE error ({action}): {e}")

def run_ble_task(action):
    asyncio.run_coroutine_threadsafe(ble_task(action), loop)

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_connected, recording, data_buffer
    message = ""
    if request.method == 'POST':
        action = request.form['action']
        if action == 'connect':
            run_ble_task("connect")
            message = "Connecting..."  # Update immediately, reflect on next render
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
    print("Starting app on http://127.0.0.1:5000/")  # Explicit startup
    # Start loop in thread
    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    # Run Flask with waitress
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    except ImportError:
        app.run(host='0.0.0.0', port=5000, debug=True)