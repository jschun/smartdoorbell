# smartdoorbell
Raspberry Pi 3B Smartdoorbell with Sonos and Pushbullet (this will not work on a Raspberry Pi Zero unfortunately)

ronschaeffer has made an excellent script for using your Sonos speakers for the sound of your doorbell. 
I added the code for using the Raspberry Pi's GPIO pin GPIO17 (pin 11) for my doorbell button (and the other wire to ground offcourse, I use pin 6).

Also I use PushBullet to get a push message on my smartphone (and my wives does too) by using a PushBullet group in my account.

Don't forget to put in your own API key for PushBullet at line 153 "pb = Pushbullet('put API key here')"

Start with installing the extra software used for Sonos control and Push messages

pip install soco

sudo pip install pushbullet.py

Also to hold the doorbell sound files I install an appache2 for webservices (in the future I want to add a webgui for tracking visitors etc., so this seemed the obvious choice for now)

sudo apt-get install apache2 -y

