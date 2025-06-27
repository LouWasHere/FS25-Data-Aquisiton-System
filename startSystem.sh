sudo dhclient -v usb0
sudo udhcpc -i usb0
sudo route add -net 0.0.0.0 usb0

ngrok tcp 22 &
sleep 5
kill -9 "$(pgrep ngrok)"
sleep 1
python3 /home/daq/Documents/server.py &
