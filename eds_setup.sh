#!/bin/bash
#
echo Initiating EDS Controller Setup...
echo ---
echo Creating EDSPython folder
mkdir -m 777 /home/pi/EDSPython
cd /home/pi/EDSPython
echo ---
#
echo Installing Python code from github.com/BUSolarLab/EDSFieldController...
git clone https://github.com/BUSolarLab/EDSFieldController.git
cp /home/pi/EDSPython/EDSFieldController/AM2315.py /home/pi/EDSPython
cp /home/pi/EDSPython/EDSFieldController/DataManager.py /home/pi/EDSPython
cp /home/pi/EDSPython/EDSFieldController/MasterManager.py /home/pi/EDSPython
cp /home/pi/EDSPython/EDSFieldController/StaticManager.py /home/pi/EDSPython
cp /home/pi/EDSPython/EDSFieldController/TestingManager.py /home/pi/EDSPython
cp /home/pi/EDSPython/EDSFieldController/SP420.py /home/pi/EDSPython
echo ---
#
echo Installing external dependencies. THIS TAKES A MINUTE. PLEASE WAIT...
sudo pip3 install RPI.GPIO
sudo pip3 install adafruit-circuitpython-pcf8523
sudo pip3 install adafruit-circuitpython-am2320
sudo pip3 install i2cdev
sudo apt-get update
sudo apt-get dist-upgrade
sudo apt-get upgrade
sudo apt-get install build-essential python-pip python-dev python-smbus git
git clone https://github.com/adafruit/Adafruit_Python_GPIO.git
cd Adafruit_Python_GPIO
sudo python3 setup.py install
git clone https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx
cd Adafruit_Python_MCP3xxx
sudo python3 setup.py install
echo ---
#
#echo Moving files around...
#cp -r /home/pi/.local/lib/p*/s*/adafruit_register /home/pi/EDSPython
#cp /home/pi/.local/lib/p*/s*/adafruit_pcf8523.py /home/pi/EDSPython
#cp -r /home/pi/EDSPython/Adafruit_Python_GPIO/Adafruit_Python_MCP3008 /home
#cp -r /home/Adafruit_Python_MCP3008/Adafruit_MCP3008 /home/pi/EDSPython
#cp -r /home/Adafruit_Python_GPIO/Adafruit_GPIO /home/pi/EDSPython
#echo ---
#
echo Installing USB auto mount library and setting config...
sudo apt-get install ntfs-3g
sudo apt-get install exfat-fuse
sudo apt-get install exfat-utils
sudo apt-get install usbmount
# change config settings
sed -i "s/\(FS_MOUNTOPTIONS *= *\).*/\1\"-fstype=vfat,gid=users,dmask=0007,fmask=0117\"/" /etc/usbmount/usbmount.conf
sed -i "s/\(MountFlags *= *\).*/\1shared/" /lib/systemd/system/systemd-udevd.service
echo ---
#
echo Installing Watchdog timer and setting config...
modprobe bcm2835_wdt
echo "bcm2835_wdt" | tee -a /etc/modules
sudo apt-get install watchdog
sudo update-rc.d watchdog defaults
# uncomment line for running watchdog device
sed -i '/watchdog-device/s/^#//g' /etc/watchdog.conf
# add timeout line
sed -i '/watchdog-device/ a\watchdog-timeout = 15' /etc/watchdog.conf
# uncomment max load
sed -i '/max-load-1/s/^#//g' /etc/watchdog.conf
sed -i '/max-load-15/s/^#*/#/g' /etc/watchdog.conf
# uncomment interval
sed -i '/interval/s/^#//g' /etc/watchdog.conf
# start the watchdog
sudo service watchdog start
echo ---
#
echo INSTALLATION COMPLETE. THANK YOU FOR PLAYING.
