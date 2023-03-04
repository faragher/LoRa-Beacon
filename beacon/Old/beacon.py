#!/usr/bin/env python3

import os
import argparse
import time
import threading
import RNS
import plyer
import msgpack


APP_NAME = "lora_beacon"


IncidentCommandHash = "c485c00b07ae1ab51449a252d24c9c76"
IncidentCommandID = None
IncidentCommandDest = None
IncidentCommandPath = False

TeamLeadHash = None
TeamLeadID = None
TeamLeadDest = None
TeamLeadPath = False

LocalIdentity = None

LatestTimeOfOperation = None

latest_link = None




def RequestID(id_hash, friendly):
    RNS.log("Starting request for "+friendly)
    RNS.Transport.request_path(id_hash)
    #def RunRequest(id_hash,friendly):
    #    #RNS.Transport.request_path(id_hash)
    #    while not RNS.Transport.has_path(id_hash):
    #        time.sleep(0.1)
    #    RNS.log(friendly + "path received.")
    #threading.Thread(target=RunRequest, daemon=True, args=(id_hash,friendly)).start()
    RNS.log(friendly + " path received.")
    if not RNS.Transport.has_path(id_hash):
        RNS.log("Just kidding.")

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
        self.app_dir = plyer.storagepath.get_home_dir()+"/.config/LoRaBeacon"
        if self.app_dir.startswith("file://"):
            self.app_dir = self.app_dir.replace("file://", "")
        if not os.path.isdir(self.app_dir+"/app_storage"):
            os.makedirs(self.app_dir+"/app_storage")
        RNS.log("App directory: "+self.app_dir)
        self.config_path = self.app_dir+"/app_storage/LoRaBeacon_config1"
        self.identity_path = self.app_dir+"/app_storage/beacon_identity1"
        self.saving_configuration = False
        self.reticulum = RNS.Reticulum(None)
        
        if not os.path.isfile(self.config_path):
            self.create_config()
        else:
            self.load_config()
        if not os.path.isfile(self.identity_path):
            RNS.log("Creating new identity")
            self.identity = RNS.Identity()
            self.identity.to_file(self.identity_path)
        else:
            RNS.log("Loading Identity")
            self.identity = RNS.Identity.from_file(self.identity_path)
            self.identity.load_known_destinations()
            #RNS.log("Known Destinations: "+str(self.identity.known_destinations))
            
            
        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            APP_NAME,
            "Uplink",
            "request"
            )
            
        if RNS.loglevel < RNS.LOG_INFO:
            RNS.loglevel = RNS.LOG_INFO
        self.destination.set_packet_callback(gotPacket)
        self.destination.set_proof_strategy(RNS.Destination.PROVE_ALL)
        RNS.log("Sending announce")
        self.destination.announce()
            
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


def PrepareUplinks():
    if IncidentCommandHash != None:
        RNS.log("Loading Incident Command.")
        RNS.log("Hash: "+IncidentCommandHash)
        ICH = bytes.fromhex(IncidentCommandHash)
        if RNS.Transport.has_path(ICH):
            RNS.log("Incident Command identity on record.")
            IncidentCommandID = RNS.Identity.recall(ICH)
            IncidentCommandDest = RNS.Destination(
            IncidentCommandID,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            APP_NAME,
            "Uplink",
            "request"
            )
            IncidentCommandPath = true
        else:
            RNS.log("Incident Command identity not on record. Waiting for broadcast...")
            RequestID(ICH, "Incident Command")

    else:
        RNS.log("No Incident Command address specified")
        
    if TeamLeadHash != None:
        RNS.log("Loading Team Lead.")
        RNS.log("Hash: "+TeamLeadHash)
        TLH = bytes.fromhex(TeamLeadHash)
        if RNS.Transport.has_path(TLH):
            RNS.log("Team Lead identity on record.")
        else:
            RNS.log("Team Lead identity not on record. Querying...")
            RequestID(TLH)
        TeamLeadID = RNS.Identity.recall(TLH)
        TeamLeadDestDest = RNS.Destination(
            TeamLeadID,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            APP_NAME,
            "Uplink",
            "request"
            )
    else:
        RNS.log("No Team Lead address specified")        

def gotPacket(data, packet):
    message = data.decode("utf-8","ignore")
    #message = data.hex(' ')
    print("Received a packet: "+message)
    #packet = RNS.Packet(None,data)
    packet.unpack()
    #if packet.packet_type == RNS.Packet.ANNOUNCE:
    #    RNS.log("Parsing announce")
    #    if DS.identity.validate_announce(packet):
    #        RNS.log("Announce properly parsed.")
            #RNS.log("Known Destinations: "+str(DS.identity.known_destinations))
    #        DS.identity.save_known_destinations()
    #        DS.identity.to_file(DS.identity_path)
    print("RSSI: "+str(rnode.r_stat_rssi)+" dBm")
    print("SNR:  "+str(rnode.r_stat_snr)+" dB")

    

def program_setup(configpath, channel=None):
    #DS.Radio = InitializeRadio()
    DS.save_config()
    RNS.log("ID: "+str(DS.identity))
    PrepareUplinks()
    
    TestLoop();

def TestLoop():
    while True:
        print("> ", end="")
        entered = input()#
        if entered != "":
            if IncidentCommandDest != None:
                RNS.log("Sending Packet")
                data    = entered.encode("utf-8","ignore")
                echo_request = RNS.Packet(IncidentCommandDest, RNS.Identity.get_random_hash())
                echo_request.send()
                RNS.log("Sent echo request to "+RNS.prettyhexrep(request_destination.hash))
            else:
                RNS.log("Nope")
                PrepareUplinks()
            #packet  = RNS.Packet(destination, data)
            #Rd.send(data)
            #squawk(data)
    
DS = DataStore()

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
