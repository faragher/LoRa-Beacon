#!/usr/bin/env python3

import os
import sys
import argparse
import RNS
#from kivy import Config
from RNode import RNodeInterface
#import kivy
#print(kivy.kivy_home_dir)
import plyer
import threading
import msgpack


#primaryChannel
#guardChannel

APP_NAME = "lora_beacon"

#def squawk(message):

def GetRNodeConfig(reticulum):
    cnf = reticulum.config
    for name in cnf["interfaces"]:
        RNS.log("Interface: "+name)
        c = cnf["interfaces"][name]
        if(("interface_enabled" in c) and c.as_bool("interface_enabled")) or (("enabled" in c) and c.as_bool("enabled")):
            if c["type"] == "RNodeInterface":
                frequency = int(c["frequency"]) if "frequency" in c else None
                bandwidth = int(c["bandwidth"]) if "bandwidth" in c else None
                txpower = int(c["txpower"]) if "txpower" in c else None
                spreadingfactor = int(c["spreadingfactor"]) if "spreadingfactor" in c else None
                codingrate = int(c["codingrate"]) if "codingrate" in c else None
                flow_control = c.as_bool("flow_control") if "flow_control" in c else False
                id_interval = int(c["id_interval"]) if "id_interval" in c else None
                id_callsign = c["id_callsign"] if "id_callsign" in c else None
                port = c["port"] if "port" in c else None
                RNS.log("Frequency: "+str(frequency))
                RNS.log("Bandwidth: "+str(bandwidth))
                RNS.log("TX Power: "+str(txpower))
                RNS.log("Spreading: "+str(spreadingfactor))
                RNS.log("Code Rate: "+str(codingrate))
                RNS.log("Callsign: "+str(id_callsign))
                RNS.log("Attached on "+str(port))
                RNS.log("Attemping to change TX power")
                c["txpower"] = 2
                txpower = int(c["txpower"]) if "txpower" in c else None
                RNS.log("TX Power: "+str(txpower))

class DataStore():
    config = {}
    def create_config(self):
        self.config["Name"] = "Unconfigured Beacon"
        self.config["Frequency"] = 915000000
        self.config["Bandwidth"] = 125000
        self.config["TXpower"] = 3
        self.config["Spread"] = 8
        self.config["CodeRate"] = 5 

    def __init__(self):
        self.app_dir       = plyer.storagepath.get_home_dir()+"/.config/LoRaBeacon"
        if self.app_dir.startswith("file://"):
            self.app_dir   = self.app_dir.replace("file://", "")
        if not os.path.isdir(self.app_dir+"/app_storage"):
            os.makedirs(self.app_dir+"/app_storage")
        RNS.log("App directory: "+self.app_dir)
        self.config_path   = self.app_dir+"/app_storage/LoRaBeacon_config"
        self.identity_path = self.app_dir+"/app_storage/beacon_identity"
        self.saving_configuration = False
        if not os.path.isfile(self.config_path):
            self.create_config()
        else:
            self.load_config()
            #self.first_run = False
        if not os.path.isfile(self.identity_path):
            RNS.log("Creating new identity")
            self.identity = RNS.Identity()
            self.identity.to_file(self.identity_path)
        else:
            RNS.log("Loading Identity")
            self.identity = RNS.Identity.from_file(self.identity_path)
            self.identity.load_known_destinations()
            RNS.log("Known Destinations: "+str(self.identity.known_destinations))


    def load_config(self):
        RNS.log("Loading Beacon configuration... "+str(self.config_path))
        config_file = open(self.config_path, "rb")
        self.config = msgpack.unpackb(config_file.read())
        config_file.close()

    def save_config(self):
        RNS.log("Saving LoRa Beacon configuration...")
        def save_function():
            while self.saving_configuration:
                time.sleep(0.15)
            try:
                self.saving_configuration = True
                config_file = open(self.config_path, "wb")
                config_file.write(msgpack.packb(DS.config))
                config_file.close()
                self.saving_configuration = False
            except Exception as e:
                self.saving_configuration = False
                RNS.log("Error while saving LoRa Beacon configuration: "+str(e), RNS.LOG_ERROR)

        threading.Thread(target=save_function, daemon=True).start()

DS=DataStore()

# This initialisation is executed when the program is started
def program_setup(configpath, channel=None):
    
    Radio = InitializeRadio()
    DS.save_config()
    RNS.log("ID: "+str(DS.identity))
    destination = RNS.Destination(
        DS.identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        APP_NAME,
        "Test Beacon"
    )
    destination.announce()
    
    TestLoop(Radio);
    
def TestLoop(Rd):
    while True:
        print("> ", end="")
        entered = input()#

        if entered != "":
            data    = entered.encode("utf-8","ignore")
            #packet  = RNS.Packet(destination, data)
            Rd.send(data)
    

#def packet_callback(data, packet):
#    # Simply print out the received data
#    print("")
#    print("Received data: "+data.decode("utf-8","ignore")+"\r\n> ", end="")
#    sys.stdout.flush()
#    
def gotPacket(data, rnode):
#	message = data.decode("utf-8","ignore")
    message = data.hex(' ')
    print("Received a packet: "+message)
    packet = RNS.Packet(None,data)
    packet.unpack()
    if packet.packet_type == RNS.Packet.ANNOUNCE:
        RNS.log("Parsing announce")
        if DS.identity.validate_announce(packet):
            RNS.log("Announce properly parsed.")
            RNS.log("Known Destinations: "+str(DS.identity.known_destinations))
            DS.identity.save_known_destinations()
            DS.identity.to_file(DS.identity_path)
    print("RSSI: "+str(rnode.r_stat_rssi)+" dBm")
    print("SNR:  "+str(rnode.r_stat_snr)+" dB")
    
def InitializeRadio():
    rnode = RNodeInterface(
	callback = gotPacket,
	name = DS.config["Name"],
	port = "COM6",
	frequency = DS.config["Frequency"],
	bandwidth = DS.config["Bandwidth"],
	txpower = DS.config["TXpower"],
	sf = DS.config["Spread"],
	cr = DS.config["CodeRate"],
	loglevel = RNodeInterface.LOG_DEBUG)
    return rnode
    
def TimedActions():
    pass

def SaveConfig():
    DS.save_config()

def LoadConfig():
    DS.load_config()


def broadcastLoop(destination):
    # Let the user know that everything is ready
    RNS.log(
        "Broadcast example "+
        RNS.prettyhexrep(destination.hash)+
        " running, enter text and hit enter to broadcast (Ctrl-C to quit)"
    )

    # We enter a loop that runs until the users exits.
    # If the user hits enter, we will send the information
    # that the user entered into the prompt.
    while True:
        print("> ", end="")
        entered = input()

        if entered != "":
            data    = entered.encode("utf-8")
            packet  = RNS.Packet(destination, data)
            packet.send()


##########################################################
#### Program Startup #####################################
##########################################################

# This part of the program gets run at startup,
# and parses input from the user, and then starts
# the program.
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(
            description="Reticulum example demonstrating sending and receiving broadcasts"
        )

        parser.add_argument(
            "--config",
            action="store",
            default=None,
            help="path to alternative Reticulum config directory",
            type=str
        )

        parser.add_argument(
            "--channel",
            action="store",
            default=None,
            help="broadcast channel name",
            type=str
        )

        args = parser.parse_args()

        if args.config:
            configarg = args.config
        else:
            configarg = None

        if args.channel:
            channelarg = args.channel
        else:
            channelarg = None

        program_setup(configarg, channelarg)

    except KeyboardInterrupt:
        print("")
        exit()
