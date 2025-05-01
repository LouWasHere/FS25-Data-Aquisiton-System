# FS25 Leeds Gryphons DAQ v1.0 "Kino"

This is the repository for the code run on our Raspberry Pi-powered DAQ for our Formula Student 2025 Internal Combustion car effort at the University of Leeds, as well as the code run on the client pitwall listeners.

More documentation and specification to follow.

Alongside the many other leaps forward for our team this year, we have also been developing our own proprietary Data Acquisition System that serves as a mechanism for telemetry, driver feedback and communication. 

With a Raspberry Pi 4B+ at its heart, the DAQ and its associated software software primarily serves to feed the 3.5-inch screen built into our steering wheel. The display informs the driver, in a legible and concise manner, information that would typically be relayed by a dashboard; speed, engine RPM, current gear among other values.

However, the functionality does not end there. We also have a live monitoring system that works over 5G to stream data to a client connected on the pit wall. The DAQ transmits all its telemetry data as well as its GPS location to the client, which runs specially designed monitoring software so that the team can analyze the current status of the car. 

The client software also features the functionality to "record" data locally - and once track time has ended, a final piece of software can be used to analyze race data that was recorded by the client tool. 

This suite of hardware sensors, software programs and network infrastructure is a valuable part of our electrics system and will help us further develop our efforts into the future.