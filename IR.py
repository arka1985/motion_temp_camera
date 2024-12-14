import os
import time
import tkinter
import RPi.GPIO as GPIO
from smbus2 import SMBus
from mlx90614 import MLX90614

# Setup GPIO and PIR sensor
GPIO.setmode(GPIO.BCM)
PIR_PIN = 21
GPIO.setup(PIR_PIN, GPIO.IN)

# Initialize I2C bus and MLX90614 sensor
bus = SMBus(1)
sensor = MLX90614(bus, address=0x5A)

# Create a Tkinter window
class App:
    def __init__(self, window, window_title):
        self.window = window
        self.motion_detected = False

        # Title Labels
        self.TitleLbl = tkinter.Label(window, text="MLX90614 WITH RASPBERRY PI", font=("Arial", 20, 'bold'), fg="black", relief="raised", borderwidth=2)
        self.TitleLbl.pack(anchor=tkinter.CENTER, expand=True)

        self.TitleLbl = tkinter.Label(window, text="DEVELOPER : DR ARKAPRABHA SAU", font=("Arial", 15, 'bold'), fg="dark orchid", relief="raised", borderwidth=1)
        self.TitleLbl.pack(anchor=tkinter.CENTER, expand=True)

        # Temperature Labels
        self.Temp1Lbl = tkinter.Label(window, text="[Body Temperature    : ]", font=("Arial", 20), fg="red", relief="ridge", borderwidth=2)
        self.Temp1Lbl.pack(anchor=tkinter.CENTER, expand=True)

        self.Temp2Lbl = tkinter.Label(window, text="[Ambient Temperature : ]", font=("Arial", 20), fg="blue", relief="ridge", borderwidth=2)
        self.Temp2Lbl.pack(anchor=tkinter.CENTER, expand=True)

        # Initialize update loop
        self.delay = 1000  # Update every 1 second
        self.update()

        # Start GUI loop
        self.window.mainloop()

    def update(self):
        # Check PIR sensor for motion
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            self.motion_detected = True
        else:
            self.motion_detected = False

        # If motion is detected, show temperature data
        if self.motion_detected:
            self.show_temperatures()
        else:
            # Only show ambient temperature when no motion is detected
            ambient_temp = sensor.get_ambient()
            self.Temp1Lbl['text'] = "[Body Temperature    : --]"
            self.Temp2Lbl['text'] = f"[Ambient Temperature : {round(ambient_temp, 2)} °C]"

        # Update GUI again after the delay
        self.window.after(self.delay, self.update)

    def show_temperatures(self):
        try:
            # Get body and ambient temperature
            body_temp = sensor.get_object_1()
            ambient_temp = sensor.get_ambient()

            # Convert body temperature to Fahrenheit
            body_temp_fahrenheit = (body_temp * 1.8) + 32

            # Update the labels with new temperature values
            self.Temp1Lbl['text'] = f"[Body Temperature    : {round(body_temp_fahrenheit, 2)} °F]"
            self.Temp2Lbl['text'] = f"[Ambient Temperature : {round(ambient_temp, 2)} °C]"

            # Print motion detected and temperatures to console (for debugging)
            print(f"Motion Detected! Body Temp: {round(body_temp_fahrenheit, 2)} °F, Ambient Temp: {round(ambient_temp, 2)} °C")
        except Exception as e:
            print(f"Error reading sensor: {e}")
            self.Temp1Lbl['text'] = "[Body Temperature    : Error]"
            self.Temp2Lbl['text'] = "[Ambient Temperature : Error]"

# Function to format time for motion detection logging
def format_time(time_array):
    h = time_array[3]
    m = time_array[4]
    s = time_array[5]
    return ":".join([str(h), str(m), str(s)])

# Global variable for debouncing
last_motion_time = 0  # Variable to store the last motion detection time

# PIR motion detection callback function with debouncing
def motion_callback(PIR_PIN, app):
    global last_motion_time
    current_time = time.time()
    
    # Only register motion if enough time has passed since the last motion event
    if current_time - last_motion_time > 2:  # 2 seconds debounce
        print(f"{format_time(time.localtime())} - Motion Detected!")
        app.motion_detected = True  # Set the motion detection flag to True
        last_motion_time = current_time  # Update last motion time

# Setup PIR motion detection
GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=lambda pin: motion_callback(pin, app))  # Motion detected on rising edge

# Create the Tkinter window and start the app
root = tkinter.Tk()
root.geometry("+250+50")
app = App(root, "Infrared Temperature and Motion Sensor")

# Handle cleanup on exit
try:
    print("PIR Module Test (CTRL+C to exit)")
    time.sleep(0.01)
    print("Ready")
    root.mainloop()
except KeyboardInterrupt:
    print("Quit")
finally:
    GPIO.cleanup()  # Clean up GPIO on exit
