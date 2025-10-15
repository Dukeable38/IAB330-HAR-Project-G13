#include <ArduinoBLE.h>
#include <Arduino_LSM6DS3.h>

const char* serviceUUID = "19B10000-E8F2-537E-4F6C-D104768A1214";
const char* cmdUUID = "19B10003-E8F2-537E-4F6C-D104768A1214";
const char* imuUUID = "19B10004-E8F2-537E-4F6C-D104768A1214";

BLEService sensorService(serviceUUID);
BLEByteCharacteristic cmdChar(cmdUUID, BLERead | BLEWrite);
BLECharacteristic imuChar(imuUUID, BLERead | BLENotify, 64); // Larger buffer for IMU string

bool streaming = false;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("IMU init failed!");
    while (1);
  }
  if (!BLE.begin()) {
    Serial.println("BLE init failed!");
    while (1);
  }

  BLE.setLocalName("Nano33IoT_HAR");
  sensorService.addCharacteristic(cmdChar);
  sensorService.addCharacteristic(imuChar);
  BLE.addService(sensorService);
  imuChar.writeValue("READY");
  BLE.advertise();
  Serial.println("Advertising...");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("Connected: ");
    Serial.println(central.address());
    while (central.connected()) {
      BLE.poll();
      if (cmdChar.written()) {
        byte cmd = cmdChar.value();
        if (cmd == 1) {
          streaming = true;
          Serial.println("Streaming started");
        } else if (cmd == 0) {
          streaming = false;
          Serial.println("Streaming stopped");
        }
      }
      if (streaming) {
        streamIMU();
      }
    }
    Serial.println("Disconnected");
    streaming = false; // Reset on disconnect
  }
}

void streamIMU() {
  float ax, ay, az, gx, gy, gz;
  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(ax, ay, az);
    IMU.readGyroscope(gx, gy, gz);
    char buffer[64];
    int len = snprintf(buffer, 64, "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f", ax, ay, az, gx, gy, gz);
    if (len > 0) {
      imuChar.writeValue(buffer);
      Serial.print("Sent IMU: "); Serial.println(buffer); // Debug print
    } else {
      Serial.println("snprintf failed!");
    }
    delay(20); // ~50Hz
  } else {
    Serial.println("IMU not available!"); // Debug if sensor fails
  }
}