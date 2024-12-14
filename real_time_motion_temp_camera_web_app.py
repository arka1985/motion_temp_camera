import os
import time
import threading
import tempfile
from flask import Flask, render_template, jsonify, Response
from smbus2 import SMBus
from mlx90614 import MLX90614
import picamzero
import RPi.GPIO as GPIO

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
ambient_temp_threshold = 27.45  # Threshold for ambient temperature (in Celsius)

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

# Function to generate frames for the video stream
def generate_frames():
    global camera
    while True:
        with camera_lock:
            if camera:
                try:
                    # Save the image to a temporary file
                    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                        camera.take_photo(temp_file.name)
                        temp_file.seek(0)  # Go back to the start of the file
                        frame = temp_file.read()  # Read the image bytes

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                except Exception as e:
                    print(f"Error capturing frame: {e}")
                    break
        time.sleep(0.1)  # Small delay to prevent overload

# Flask route to serve the video stream
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Function to handle motion detection and temperature reading
def monitor_sensors():
    global motion_detected, body_temp_fahrenheit, ambient_temp_celsius, camera

    while True:
        # Read ambient temperature continuously
        ambient_temp_celsius = sensor.get_ambient()

        # Check PIR sensor for motion
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            motion_detected = True
        else:
            motion_detected = False

        # If motion is detected or ambient temperature is above the threshold, open the camera
        with camera_lock:
            if (motion_detected or ambient_temp_celsius > ambient_temp_threshold) and camera is None:
                camera = picamzero.Camera()
                camera.start_preview()  # Start camera preview

        # If no motion and ambient temperature is below threshold, stop the camera
        if not motion_detected and ambient_temp_celsius <= ambient_temp_threshold:
            with camera_lock:
                if camera is not None:
                    camera.stop_preview()  # Stop camera preview
                    camera = None  # Release the camera object

        # Get body temperature if motion is detected
        if motion_detected:
            try:
                body_temp = sensor.get_object_1()
                body_temp_fahrenheit = (body_temp * 1.8) + 32
            except Exception as e:
                print(f"Error reading sensor: {e}")
                body_temp_fahrenheit = None

        # Log the ambient temperature for debugging
        print(f"Ambient Temperature: {ambient_temp_celsius} °C")

        time.sleep(1)

# Start a background thread to monitor sensors
sensor_thread = threading.Thread(target=monitor_sensors)
sensor_thread.daemon = True
sensor_thread.start()

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
