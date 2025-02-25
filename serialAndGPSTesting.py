#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO

import serial
import time

ser = serial.Serial('/dev/ttyS0',115200)
ser.flushInput()

arduinoSerial = serial.Serial('/dev/ttyAMA2', 9600, timeout=1)
arduinoSerial.flush()

power_key = 6
rec_buff = ''
rec_buff2 = ''
time_count = 0

def send_at(command,back,timeout):
	rec_buff = ''
	ser.write((command+'\r\n').encode())
	time.sleep(timeout)
	if ser.inWaiting():
		time.sleep(0.01 )
		rec_buff = ser.read(ser.inWaiting())
	if rec_buff != '':
		if back not in rec_buff.decode():
			print(command + ' ERROR')
			print(command + ' back:\t' + rec_buff.decode())
			return 0
		else:
			
			#print(rec_buff.decode())
			
			#Additions to Demo Code Written by Tim!
			global GPSDATA
			#print(GPSDATA)
			GPSDATA = str(rec_buff.decode()).replace('\n','').replace('\r','').replace('AT','').replace('+CGPSINFO','').replace(': ','')
			Cleaned = GPSDATA
			
			print(Cleaned)
			if ",,,,,," in Cleaned:
				print('GPS is not ready')
				return 0

			if len(Cleaned) < 12:
				print("GPS is not ready")
				return 0
			
			Lat = Cleaned[:2]
			SmallLat = Cleaned[2:11]
			NorthOrSouth = Cleaned[12]
			
			#print(Lat, SmallLat, NorthOrSouth)
			
			Long = Cleaned[14:17]
			SmallLong = Cleaned[17:26]
			EastOrWest = Cleaned[27]
			
			#print(Long, SmallLong, EastOrWest)   
			FinalLat = float(Lat) + (float(SmallLat)/60)
			FinalLong = float(Long) + (float(SmallLong)/60)
			
			if NorthOrSouth == 'S': FinalLat = -FinalLat
			if EastOrWest == 'W': FinalLong = -FinalLong
			
			print(FinalLat, FinalLong)
			
			#print(FinalLat, FinalLong)
			#print(rec_buff.decode())
			
			return 1
	else:
		print('GPS is not ready')
		return 0

def get_gps_position():
	rec_null = True
	answer = 0
	print('Start GPS session...')
	rec_buff = ''
	send_at('AT+CGPS=1,1','OK',1)
	time.sleep(2)
	while rec_null:
		if arduinoSerial.in_waiting > 0:
			data = arduinoSerial.readline().decode('utf-8').rstrip()
			print("Sensor Value: ", data)
		answer = send_at('AT+CGPSINFO','+CGPSINFO: ',1)
		if 1 == answer:
			answer = 0
			if ',,,,,,' in rec_buff:
				print('GPS is not ready')
				rec_null = False
				time.sleep(1)
		else:
			print('error %d'%answer)
			rec_buff = ''
			send_at('AT+CGPS=0','OK',1)
			return False
		time.sleep(1.5)


def power_on(power_key):
	print('SIM7600X is starting:')
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(power_key,GPIO.OUT)
	time.sleep(0.1)
	GPIO.output(power_key,GPIO.HIGH)
	time.sleep(2)
	GPIO.output(power_key,GPIO.LOW)
	time.sleep(20)
	ser.flushInput()
	print('SIM7600X is ready')

def power_down(power_key):
	print('SIM7600X is loging off:')
	GPIO.output(power_key,GPIO.HIGH)
	time.sleep(3)
	GPIO.output(power_key,GPIO.LOW)
	time.sleep(18)
	print('Good bye')

#Additions to Demo GPS.py Code Added by Tim // Simplfing the GPS Start up process
power_on(power_key)
while True:
	get_gps_position()
