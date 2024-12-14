
import os
import time
import tkinter
import threading
import RPi.GPIO as GPIO
from smbus2 import SMBus
from mlx90614 import MLX90614
from flask import Flask, render_template, jsonify
import picamzero #sudo apt-get install python3-picamzero

import os
import time
import threading
import RPi.GPIO as GPIO
from smbus2 import SMBus
from mlx90614 import MLX90614
from flask import Flask, render_template, jsonify
import picamzero

# Setup GPIO and PIR sensor
GPIO.setmode(GPIO.BCM)
PIR_PIN = 21
GPIO.setup(PIR_PIN, GPIO.IN)

# Initialize I2C bus and MLX90614 sensor
bus = SMBus(1)
sensor = MLX90614(bus, address=0x5A)

# Global variables for Flask
motion_detected = False
body_temp_fahrenheit = 0
ambient_temp_celsius = 0

# Initialize Flask app
app = Flask(__name__)

# Camera object (initialized to None)
camera = None
camera_lock = threading.Lock()  # Thread lock for camera access

# Flask route to serve the main dashboard
@app.route('/')
def index():
    return render_template('index.html', motion_detected=motion_detected, body_temp_fahrenheit=body_temp_fahrenheit, ambient_temp_celsius=ambient_temp_celsius)

# Flask route to get temperature data in JSON format
@app.route('/data')
def get_data():
    return jsonify({
        "motion_detected": motion_detected,
        "body_temperature": round(body_temp_fahrenheit, 2),
        "ambient_temperature": round(ambient_temp_celsius, 2)
    })

# Function to handle motion detection and temperature reading
def monitor_sensors():
    global motion_detected, body_temp_fahrenheit, ambient_temp_celsius, camera

    while True:
        # Check PIR sensor for motion
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            motion_detected = True
            # Open the camera when motion is detected, and ensure it's not already open
            with camera_lock:
                if camera is None:
                    camera = picamzero.Camera()
                    camera.start_preview()  # Start camera preview
        else:
            motion_detected = False
            # Stop the camera when there is no motion, only if the camera is already open
            with camera_lock:
                if camera is not None:
                    camera.stop_preview()  # Stop camera preview
                    camera = None  # Release the camera object

        if motion_detected:
            try:
                # Get body and ambient temperature
                body_temp = sensor.get_object_1()
                ambient_temp = sensor.get_ambient()

                # Convert body temperature to Fahrenheit
                body_temp_fahrenheit = (body_temp * 1.8) + 32
                ambient_temp_celsius = ambient_temp

            except Exception as e:
                print(f"Error reading sensor: {e}")
                body_temp_fahrenheit = None
                ambient_temp_celsius = None

        time.sleep(1)

# Start a background thread to monitor sensors
sensor_thread = threading.Thread(target=monitor_sensors)
sensor_thread.daemon = True
sensor_thread.start()

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
