import sys
import time
import math
import board
import adafruit_bno055
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGridLayout, QWidget
from PyQt5.QtCore import Qt, QTimer

i2c = board.I2C()  # uses board.SCL and board.SDA

# Add a delay to ensure the sensor is ready
time.sleep(1)

sensor = adafruit_bno055.BNO055_I2C(i2c)

last_val = 0xFFFF

def temperature():
    global last_val
    result = sensor.temperature
    if abs(result - last_val) == 128:
        result = sensor.temperature
        if abs(result - last_val) == 128:
            return 0b00111111 & result
    last_val = result
    return result

try:
    sensor.mode = adafruit_bno055.NDOF_MODE
    print("Sensor mode set to:", sensor.mode)
except OSError as e:
    print(f"Failed to set sensor mode: {e}")
    sys.exit(1)

time.sleep(5)

class SensorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IMU Sensor Data")
        self.setGeometry(0, 0, 480, 320)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")

        self.layout = QGridLayout()

        # Values and annotations
        self.accel_value = QLabel("")
        self.accel_annotation = QLabel("Lin.Accel")
        self.gyro_x_value = QLabel("")
        self.gyro_x_annotation = QLabel("Gyro X")
        self.gyro_y_value = QLabel("")
        self.gyro_y_annotation = QLabel("Gyro Y")
        self.gyro_z_value = QLabel("")
        self.gyro_z_annotation = QLabel("Gyro Z")
        self.compass_value = QLabel("")
        self.compass_annotation = QLabel("Deg")

        # Style the values
        value_style = "font-size: 24pt; color: green; qproperty-alignment: AlignCenter;"
        self.accel_value.setStyleSheet(value_style)
        self.gyro_x_value.setStyleSheet(value_style)
        self.gyro_y_value.setStyleSheet(value_style)
        self.gyro_z_value.setStyleSheet(value_style)
        self.compass_value.setStyleSheet(value_style)

        # Style the annotations
        annotation_style = "font-size: 12pt; color: white; qproperty-alignment: AlignCenter;"
        self.accel_annotation.setStyleSheet(annotation_style)
        self.gyro_x_annotation.setStyleSheet(annotation_style)
        self.gyro_y_annotation.setStyleSheet(annotation_style)
        self.gyro_z_annotation.setStyleSheet(annotation_style)
        self.compass_annotation.setStyleSheet(annotation_style)

        # Add widgets to the layout
        self.layout.addWidget(self.accel_value, 0, 0)
        self.layout.addWidget(self.accel_annotation, 1, 0)
        self.layout.addWidget(self.gyro_x_value, 0, 1)
        self.layout.addWidget(self.gyro_x_annotation, 1, 1)
        self.layout.addWidget(self.gyro_y_value, 0, 2)
        self.layout.addWidget(self.gyro_y_annotation, 1, 2)
        self.layout.addWidget(self.gyro_z_value, 2, 0)
        self.layout.addWidget(self.gyro_z_annotation, 3, 0)
        self.layout.addWidget(self.compass_value, 2, 1)
        self.layout.addWidget(self.compass_annotation, 3, 1)

        # Set the layout
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Timer to update sensor data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_data)
        self.timer.start(1000)  # Update every second

    def update_sensor_data(self):
        try:
            linear_accel = sensor.linear_acceleration
            gyro = sensor.gyro
            euler = sensor.euler
            calibration = sensor.calibration_status

            if linear_accel is not None and all(v is not None for v in linear_accel):
                magnitude = math.sqrt(linear_accel[0]**2 + linear_accel[1]**2 + linear_accel[2]**2) / 9.81
                self.accel_value.setText(f"{magnitude:.2f} Gs")
                print(f"Linear Acceleration: {linear_accel}, Magnitude: {magnitude:.2f} Gs")
            else:
                self.accel_value.setText("N/A")
                print("Linear Acceleration: N/A")

            if gyro is not None and all(v is not None for v in gyro):
                self.gyro_x_value.setText(f"{gyro[0]:.2f}")
                self.gyro_y_value.setText(f"{gyro[1]:.2f}")
                self.gyro_z_value.setText(f"{gyro[2]:.2f}")
                print(f"Gyroscope: {gyro}")
            else:
                self.gyro_x_value.setText("N/A")
                self.gyro_y_value.setText("N/A")
                self.gyro_z_value.setText("N/A")
                print("Gyroscope: N/A")

            if euler is not None and euler[0] is not None:
                self.compass_value.setText(f"{euler[0]:.2f}°")
                print(f"Compass Angle: {euler[0]:.2f}°")
            else:
                self.compass_value.setText("N/A")
                print("Compass Angle: N/A")

            print(f"Calibration Status - Sys: {calibration[0]}, Gyro: {calibration[1]}, Accel: {calibration[2]}, Mag: {calibration[3]}")
        except OSError as e:
            print(f"Failed to read sensor data: {e}")

def main():
    app = QApplication(sys.argv)
    window = SensorWindow()
    window.showFullScreen()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()