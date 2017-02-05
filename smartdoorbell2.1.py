# /usr/bin/env python3

# Importeer de noodzakelijke libraries voor deurbel
import time
import RPi.GPIO as GPIO
import os
import sys

from soco import SoCo
from soco.snapshot import Snapshot
from pushbullet import Pushbullet

# Zet deurbel geluid
sys.path.insert(0, '/home/pi/SmartDoorbell/soco-0.11.1') # Add soco location to system path

# Zet GPIO pin nummer variabele voor deurbel
deurbel=17

# Zet GPIO pins voor deurbel
GPIO.setmode(GPIO.BCM)

# Zet deurbel knoppen op INPUT en zet pull-up weerstand op UP
GPIO.setup(deurbel,GPIO.IN,pull_up_down=GPIO.PUD_UP)

# Continue loop om te checken of de deurbel wordt ingedrukt
print ("deurbel is actief")

while(1):
	if GPIO.input(deurbel)==0:
		
		print("Starting Doorbell Player...")

		# Definieer MP3 file als deurbel geluid en zet volume (30-50 is redelijk, 100 max)
		bellsound = "http://www.jschun.nl/smartdoorbell/doorbell-2.mp3"
		bellvolume = 40

		# Definieer alle Sonos zones/speakers en hun IP adres
		Keuken = SoCo('192.168.2.42')
		Woonkamer = SoCo('192.168.2.43')
		Slaapkamer = SoCo('192.168.2.45')
		#Playbar = SoCo('192.168.1.238')
		#Sub = SoCo('192.168.1.208')

		# Geef aan welke speakers meedoen als deurbel (doorbellx)en welke niet (nondoorbellx)
		doorbell1 = Keuken
		doorbell2 = Woonkamer
		#doorbell3 = diningroom
		#doorbell4 = kitchen

		nondoorbell1 = Slaapkamer
		#nondoorbell2 = guestroom
		#nondoorbell3 = livingroom

		# Creeer groeplijsten voor doorbellgroup met doorbell, nondoobellgroup met non-doorbell en zgn invisible zones (speakers die er wel zijn, maar niet meedoen zoals Sonos Sub bijv.)
		doorbellgroup = [doorbell1, doorbell2]
		nondoorbellgroup = [nondoorbell1]
		invisiblezones = [Slaapkamer]


		### Bewaar Sonos status

		# Snapshot van de doorbellgroup speakers
		for zp in doorbellgroup:
			print("\nSnapshotting current state of " + zp.player_name + "\n")
			zp.snap = Snapshot(zp)
			zp.snap.snapshot()
	
		# Build descriptor list voor iedere doorbellgroup speaker voor latere processing & restoration
		for zp in doorbellgroup:
			print("\nGetting current group state of " + zp.player_name + "\n")
			zp.groupstatus = [zp,								# 0 player object
				bool(len(set(zp.group.members) - set(invisiblezones)) != 1),		# 1 in a group? (can't rely on boolean return from Snapshot, because invisible players are included in group/non-group status)
				zp.is_coordinator,							# 2 is coordinator?
				zp.group.coordinator,							# 3 curent coordinator object
				bool(set(zp.group.members) & set(nondoorbellgroup)),			# 4 heterogeneous group? (made up of both doorbell and non-doorbell players)
				(list(set(nondoorbellgroup) & set(zp.group.members)) + [False])[0]	# 5 First non-doorbell group member from list; Blank if only doorbellgroup members
				]
		
		### Deurbel routine

		# Pause and unjoin doorbell zone players from any current groups
		print("Unjoining doorbell group players from current groups...\n") 
		for zp in doorbellgroup :
			zp.unjoin()

		# Join doornell zone players into a group with doorbell1 as master
		print("Joining doorbell group players with " + doorbell1.player_name + " as master...\n")
		for i in range(1,len(doorbellgroup)):
			zp = doorbellgroup[i]
			zp.join(doorbell1)
	
		# Wait for zone players to be ready
		while not doorbell1.is_coordinator:
			print("Waiting for " + doorbell1.player_name + " to be coordinator...\n")
			time.sleep(0.1)

		# Set volume for doorbell sound
		for zp in doorbellgroup:
			zp.volume = bellvolume
			print("Setting " + zp.player_name + " volume.\n")

		# Play doorbell sound  
		doorbell1.play_uri(uri=bellsound)
		track = doorbell1.get_current_track_info()
		print(track['title'])

		# Show state of playing doorbell
		while str(doorbell1.get_current_transport_info()[u'current_transport_state']) != "PLAYING":
			print("Waiting to start playing...")
			time.sleep(0.1)
		while str(doorbell1.get_current_transport_info()[u'current_transport_state']) == "PLAYING":
			print("Ringing...")
			time.sleep(0.1)

		# Unjoin doornbell zone players doorbell group
		print("\nUnjoining doorbell group players from doorbell group...")
		for zp in doorbellgroup:
			zp.unjoin()

		# Wait for zone players to be ungrouped
		for zp in doorbellgroup:
			while not zp.is_coordinator:
				print("\nWaiting for " + zp.player_name + " to be ungrouped...")
				time.sleep(0.1)

		### Restore and regroup doorbell players
		
		# Restore original state of doorbell players
		print("\nRestoring doorbell group players to former states...")	  
		for zp in doorbellgroup:
			zp.snap.restore(fade=0)
			time.sleep(1)

		# Restore groups based on zp.groupstatus descriptor list of original group state
		print("\nRestoring groups...")
		for zp in doorbellgroup:
			if zp.groupstatus[1] == False:							# Loner
				pass									#### Do nothing; was not in a group
			elif zp.groupstatus[2] == False and zp.groupstatus[4] == False:			# Homog group slave
				zp.join(zp.groupstatus[3])						##### Rejoin to original coord
			elif zp.groupstatus[2] == True and zp.groupstatus[4] == False:			# Homog group coord
				pass									#### Do nothing; slaves are rejoined above
			elif zp.groupstatus[2] == True and zp.groupstatus[4] == True:			# Former coord of heterog group
				zp.join(zp.groupstatus[5].group.coordinator)				##### Query new coord of non-doorbell group member & rejoin to it
			elif zp.groupstatus[2] == False and zp.groupstatus[3] not in doorbellgroup:	# Slave in heterog group with non-doorbell coord
				zp.join(zp.groupstatus[3])						#### Rejoin to original coord
			else:										# Slave in heterog group with doorbell coord
				zp.join(zp.groupstatus[5].group.coordinator)				#### Query new coord of non-doorbell group member & rejoin to it

		# Finish
		
		# Verstuur Push bericht (PushBullet)
		pb = Pushbullet('put API key here')
		my_channel = pb.get_channel('slimme_deurbel')
		push = my_channel.push_note("Ding Dong!", "Er is net aangebeld")
		
		time.sleep(.5)
		os.system('clear')
		print ("deurbel is weer actief")
		
#Reset de GPIO instellingen naar standaard (DEFAULT)
GPIO.cleanup()
