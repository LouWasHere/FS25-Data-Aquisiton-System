# FS25 Leeds Gryphons DAQ v1.0 "Kino"

This is the repository for the code run on our Raspberry Pi-powered DAQ for our Formula Student 2025 Internal Combustion car effort at the University of Leeds, as well as the code run on the client pitwall listeners.

## Abstract

Alongside the many other leaps forward for our team this year, we have also been developing our own proprietary Data Acquisition System that serves as a mechanism for telemetry, driver feedback and communication. 

With a Raspberry Pi 4B+ at its heart, the DAQ and its associated software software primarily serves to feed the 3.5-inch screen built into our steering wheel. The display informs the driver, in a legible and concise manner, information that would typically be relayed by a dashboard; speed, engine RPM and current gear among other values.

However, the functionality does not end there. We also have a live monitoring system that works over 5G to stream data to a client connected on the pit wall. The DAQ transmits all its telemetry data as well as its GPS location to the client, which runs specially designed monitoring software so that the team can analyze the current status of the car. 

The client software also features the functionality to "record" data locally - and once track time has ended, a final piece of software can be used to analyze race data that was recorded by the client tool. 

This suite of hardware sensors, software programs and network infrastructure is a valuable part of our electrics system and will help us further develop our efforts into the future.

# Design Documentation

## Hardware

The core of the DAQ system is the Raspberry Pi that hosts the server, collects data from the sensors and renders the dashboard shown to the driver on the steering-wheel mounted screen. That being said, the sandwich involved in making this happen is a little bigger than just the Pi. The GPS/GNSS HAT is mounted atop the Pi, and on top of that we designed a custom PCB that allows us to mount our IMU, Arduino for analog signal interptetation, RS232 signal translator chip as well as various other circuit components and connection points.

*SCREENSHOTS OF PCB DESIGN, SOLDERED HARDWARE AND ORIGINAL SCHEMATIC TO COME*

## Software Components

There are, as described, three aspects to the software suite developed to work alongside the DAQ. The code that runs on the car, as well as two programs that run on a remote device that provide real-time information and post-race analysis respectively.

### Server / Dashboard / Data Interpreter

This code is designed to be run on the Raspberry Pi, but can be run on any device to test functionality. This program operates three main threads at all times to keep track of each primary aspect of the program. These threads are:
 - Dashboard UI Display and Updating
 - Sensor querying, data acquisition and processing
 - Server connections and data transmission over the 4G network

The dashboard is written in PyQt. It renders a simple but primarily legible design onto a 3.5-inch screen mounted to the steering wheel of the car. This displays various pieces of information relevant to the driver, as gathered and calulated by the DAQ.

*SCREENSHOTS TO FOLLOW*

When used with an internet connection, the UI displays an address and port that can be used to access the server code running on the DAQ from any internet-connected device.

The DAQ features a SIM card tray that, when populated and the correct commands run, enable internat access and thus server hosting. Through ngrok, we are able to retain a static address and port to connect over despute the dynamic nature of a mobile network internet connection.

Data Acquisition involved interfacing with many devices - our Arduino to interpret analog signals (connected over UART Serial), the IMU (connected over I2C), the GPS module (proprietary connection) and the ECU (over RS232 translated to Serial).