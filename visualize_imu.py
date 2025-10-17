import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV (replace with your file path if needed)
df = pd.read_csv('imu_data.csv')

# Convert timestamp to numeric index for easier plotting (optional, if timestamps are uneven)
df['index'] = range(len(df))

# Plot acceleration axes
plt.figure(figsize=(14, 10))
plt.subplot(2, 1, 1)
plt.plot(df['index'], df['accel_x'], label='Accel X', color='r')
plt.plot(df['index'], df['accel_y'], label='Accel Y', color='g')
plt.plot(df['index'], df['accel_z'], label='Accel Z', color='b')
plt.title('Acceleration Patterns Over Time')
plt.xlabel('Sample Index')
plt.ylabel('Acceleration (g)')
plt.legend()
plt.grid(True)

# Plot gyroscope axes
plt.subplot(2, 1, 2)
plt.plot(df['index'], df['gyro_x'], label='Gyro X', color='r')
plt.plot(df['index'], df['gyro_y'], label='Gyro Y', color='g')
plt.plot(df['index'], df['gyro_z'], label='Gyro Z', color='b')
plt.title('Gyroscope Patterns Over Time')
plt.xlabel('Sample Index')
plt.ylabel('Angular Velocity (dps)')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('imu_visualization.png')  # Save plot as image
plt.show()