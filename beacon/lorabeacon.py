#!/usr/bin/env python3

import os
import sys
import argparse
import time
import threading
import RNS
import plyer
import msgpack
from datetime import datetime

class DataStore():
    config = {}
    
    def create_config(self):
        self.config["Name"] = "Unconfigured Beacon"
        self.config["Frequency"] = 915000000
        self.config["Bandwidth"] = 125000
        self.config["TXpower"] = 3
        self.config["Spread"] = 8
        self.config["CodeRate"] = 5 
        self.config["ReportTime"] = 180 #seconds
        self.config["TargetSecond"] = 0 
        self.config["UseRNSLogFile"] = False
        self.config["UseCustomLogFile"] = False

       
       
        
    def __init__(self):
        #Initialize operational variables
        self.LastReport = 0
        self.ICHash = None
        self.TLHash = None
        self.isTeamLead = False
        self.isIncidentCommand = False
        
    
        #Initialize directories
        self.app_dir = plyer.storagepath.get_home_dir()+"/.config/LoRaBeacon"
        if self.app_dir.startswith("file://"):
            self.app_dir = self.app_dir.replace("file://", "")
        if not os.path.isdir(self.app_dir+"/app_storage"):
            os.makedirs(self.app_dir+"/app_storage")
        RNS.log("App directory: "+self.app_dir)
        self.config_path = self.app_dir+"/app_storage/LoRaBeacon_config"
        self.identity_path = self.app_dir+"/app_storage/beacon_identity"
        self.recordkeeping_path = self.app_dir+"/app_storage/record"
        self.saving_configuration = False
        
        #Initialize configuration
        if not os.path.isfile(self.config_path):
            self.create_config()
        else:
            self.load_config()
        self.app_name = self.config["Name"]
        
        #Creating persistent log
        if self.config["UseRNSLogFile"]:
            RNS.log("Logging to file: "+self.app_dir+"/app_storage/log")
            RNS.logdest = RNS.LOG_FILE
            RNS.logfile = self.app_dir+"/app_storage/log"
            
        if self.config["UseCustomLogFile"]:
            RNS.log("Using custom recordkeeping file")


            

        
        #Initialize Reticulum
        #self.reticulum = RNS.Reticulum(None)
            
        #Initialize input destination
        #self.destination = RNS.Destination(
        #    self.identity,
        #    RNS.Destination.IN,
        #    RNS.Destination.SINGLE,
        #    self.app_name,
        #    "Uplink",
        #    "request",
        #    "identifyexample"
        #    )
        #self.destination.set_packet_callback(gotPacket)
        #self.destination.set_proof_strategy(RNS.Destination.PROVE_ALL)
            
        #Set minimum log level
        if RNS.loglevel < RNS.LOG_INFO:
            RNS.loglevel = RNS.LOG_INFO
            
            

        #RNS.log("Sending announce")
        #self.destination.announce()
        
    def get_identity(self):
        #Initialize identity    
        if not os.path.isfile(self.identity_path):
            RNS.log("Creating new identity")
            self.identity = RNS.Identity()
            self.identity.to_file(self.identity_path)
        else:
            RNS.log("Loading Identity")
            self.identity = RNS.Identity.from_file(self.identity_path)
            self.identity.load_known_destinations()
            #RNS.log("Known Destinations: "+str(self.identity.known_destinations))
        return self.identity
            
            
    def set_packet_callback(self, call):
        self.destination.set_packet_callback(call)
        
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

    def record(self,message):
        if self.config["UseCustomLogFile"] == False:
            return
        try:
            date = datetime.utcnow().strftime('%d%b%Y')
            DT = datetime.utcnow().strftime('%d%b%Y %H%M:%S UTC')
            logfile = self.recordkeeping_path+date
            LOG_MAXSIZE  = 5*1024*1024
            file = open(logfile, "a")
            file.write("["+DT+"]"+message+"\n")
            file.close()
                
            if os.path.getsize(logfile) > LOG_MAXSIZE:
                hour = datetime.utcnow().strftime('%H')
                prevfile = logfile+"."+hour
                os.rename(logfile, prevfile)

        except Exception as e:
            RNS.log("Exception occurred while writing log message to log file: "+str(e), RNS.LOG_CRITICAL)
    
    
    
    

def set_endpoint(hexhash):
    hash = bytes.fromhex(hexhash)
    # Check if we know a path to the destination
    if not RNS.Transport.has_path(hash):
        RNS.log("Destination is not yet known. Requesting path and waiting for announce to arrive...")
        RNS.Transport.request_path(hash)
        while not RNS.Transport.has_path(hash):
            time.sleep(0.1)

    # Recall the server identity
    server_identity = RNS.Identity.recall(hash)
    return server_identity
    
def set_destination(ID,DS):
    destination = RNS.Destination(
        ID,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        DS.app_name,
        "identifyexample"
    )
    return destination
    
