sleep 5

sudo dhclient -v usb0
sudo udhcpc -i usb0
sudo route add -net 0.0.0.0 usb0

ngrok tcp 22 &
sleep 5
python3 Documents/message_Qt.py