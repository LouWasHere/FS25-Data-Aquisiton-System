import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)
print("I2C initialized:", i2c.try_lock())
devices = i2c.scan()
i2c.unlock()
print("I2C devices found:", devices)
