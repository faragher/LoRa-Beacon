##########################################################
# Derived from Reticulum Identify (or maybe link)        #
# reference example                                      #
##########################################################

import os
import sys
import time
import argparse
import RNS
from lorabeacon import DataStore
import lorabeacon as LB

DS = DataStore()
DS.app_name = "example_utilities"


##########################################################
#### Server Part #########################################
##########################################################

# A reference to the latest client link that connected
latest_client_link = None

# This initialisation is executed when the users chooses
# to run as a server
def server(configpath):
    # We must first initialise Reticulum
    reticulum = RNS.Reticulum(configpath)
    
    # Randomly create a new identity for our link example
    server_identity = RNS.Identity()

    # We create a destination that clients can connect to. We
    # want clients to create links to this destination, so we
    # need to create a "single" destination type.
    server_destination = RNS.Destination(
        server_identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        DS.app_name,
        "identifyexample"
    )

    # We configure a function that will get called every time
    # a new client creates a link to this destination.
    server_destination.set_link_established_callback(client_connected)

    # Everything's ready!
    # Let's Wait for client requests or user input
    server_loop(server_destination)

def server_loop(destination):
    # Let the user know that everything is ready
    RNS.log(
        "Link identification example "+
        RNS.prettyhexrep(destination.hash)+
        " running, waiting for a connection."
    )

    RNS.log("Hit enter to manually send an announce (Ctrl-C to quit)")

    # We enter a loop that runs until the users exits.
    # If the user hits enter, we will announce our server
    # destination on the network, which will let clients
    # know how to create messages directed towards it.
    while True:
        entered = input()
        destination.announce()
        RNS.log("Sent announce from "+RNS.prettyhexrep(destination.hash))

# When a client establishes a link to our server
# destination, this function will be called with
# a reference to the link.
def client_connected(link):
    global latest_client_link

    RNS.log("Client connected")
    link.set_link_closed_callback(client_disconnected)
    link.set_packet_callback(server_packet_received)
    link.set_remote_identified_callback(remote_identified)
    latest_client_link = link

def client_disconnected(link):
    RNS.log("Client disconnected")

def remote_identified(link, identity):
    RNS.log("Remote identified as: "+str(identity))

def server_packet_received(message, packet):
    global latest_client_link

    # Get the originating identity for display
    remote_peer =  "unidentified peer"
    if packet.link.get_remote_identity() != None:
        remote_peer = str(packet.link.get_remote_identity())

    # When data is received over any active link,
    # it will all be directed to the last client
    # that connected.
    text = message.decode("utf-8")

    RNS.log("Received data from "+remote_peer+": "+text)
    
    reply_text = "I received \""+text+"\" over the link from "+remote_peer
    reply_data = reply_text.encode("utf-8")
    RNS.Packet(latest_client_link, reply_data).send()


##########################################################
#### Client Part #########################################
##########################################################

# A reference to the server link
server_link = None


# This initialisation is executed when the users chooses
# to run as a client
def client(destination_hexhash, configpath):

    DS.ICHash = destination_hexhash
    DS.config["UseCustomLogFile"] = True
    DS.record("System startup")
    # We must first initialise Reticulum
    reticulum = RNS.Reticulum(configpath)

    # Create a new client identity
    client_identity = DS.get_identity()
    DS.record("Identity is "+client_identity.hexhash)
    
    IC_identity = LB.set_endpoint(DS.ICHash)
    RNS.log("Establishing link with Incident Command...")
    DS.record("Establishing link with Incident Command ["+DS.ICHash+"]...")
    IC_destination = LB.set_destination(IC_identity, DS)
    IC_link = RNS.Link(IC_destination)
    IC_link.set_packet_callback(IC_packet_received)
    IC_link.set_link_established_callback(IC_link_established)
    IC_link.set_link_closed_callback(IC_link_closed)
    
    if DS.TLHash != None:
        RNS.log("Establishing link with Team Leader...")
        TL_identity = LB.set_endpoint(DS.TLHash)
        TL_destination = LB.set_destination(TL_identity, DS)
        TL_link = RNS.Link(TL_destination)
        TL_link.set_packet_callback(TL_packet_received)
        TL_link.set_link_established_callback(TL_link_established)
        TL_link.set_link_closed_callback(TL_link_closed)

    # Everything is set up, so let's enter a loop
    # for the user to interact with the example
    client_loop()

def client_loop():
    #global server_link

    # Wait for the link to become active
    while not server_link:
        time.sleep(0.1)

    should_quit = False
    while not should_quit:
        try:
            print("> ", end=" ")
            text = input()

            # Check if we should quit the example
            if text == "quit" or text == "q" or text == "exit":
                RNS.log("Quitting")
                DS.record("Application quitting due to user request.")
                should_quit = True
                server_link.teardown()
                RNS.Reticulum.exit_handler()
                time.sleep(1.5)
                os._exit(0)

            # If not, send the entered text over the link
            if text != "":
                data = text.encode("utf-8")
                if len(data) <= RNS.Link.MDU:
                    RNS.Packet(server_link, data).send()
                else:
                    DS.record("MDU error, sent "+str(len(data))+"/"+str(RNS.Link.MDU)+" bytes.")
                    RNS.log(
                        "Cannot send this packet, the data size of "+
                        str(len(data))+" bytes exceeds the link packet MDU of "+
                        str(RNS.Link.MDU)+" bytes",
                        RNS.LOG_ERROR
                    )

        except Exception as e:
            RNS.log("Error while sending data over the link: "+str(e))
            DS.record("Transmission error: "+str(e))
            should_quit = True
            server_link.teardown()
            
def IC_packet_received(message, packet):
    text = message.decode("utf-8")
    RSSI = str(packet.rssi)
    SNR = str(packet.snr)
    if packet.link.get_remote_identity() != None:
        remote_peer = str(packet.link.get_remote_identity())
        DS.record("Incident Command ["+remote_peer+" (VERIFIED)] RSSI:"+RSSI+" SNR:"+SNR+" -- "+text)
    else:
        DS.record("Incident Command ["+DS.ICHash+" (UNVERIFIED)] RSSI:"+RSSI+" SNR:"+SNR+" -- "+text)
    RNS.log("Received data on the link: "+text)
    print("> ", end=" ")
    sys.stdout.flush()
    
def IC_link_closed(link):
    if link.teardown_reason == RNS.Link.TIMEOUT:
        RNS.log("The link timed out")
        DS.record("Incident Command ["+DS.ICHash+"] uplink timed out.")
        
    elif link.teardown_reason == RNS.Link.DESTINATION_CLOSED:
        RNS.log("The link was closed by the server")
        DS.record("Incident Command ["+DS.ICHash+"] uplink closed by IC.")
    else:
        RNS.log("Link closed.")
        DS.record("Incident Command ["+DS.ICHash+"] uplink closed. NFI.")
        
def IC_link_established(link):
    global server_link
    server_link = link
    DS.record("Uplink to Incident Command ["+DS.ICHash+"] established.")
    RNS.log("Link established with server, identifying to remote peer...")
    link.identify(DS.identity)



##########################################################
#### Program Startup #####################################
##########################################################

# This part of the program runs at startup,
# and parses input of from the user, and then
# starts up the desired program mode.
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Simple link example")

        parser.add_argument(
            "-s",
            "--server",
            action="store_true",
            help="wait for incoming link requests from clients"
        )

        parser.add_argument(
            "--config",
            action="store",
            default=None,
            help="path to alternative Reticulum config directory",
            type=str
        )

        parser.add_argument(
            "destination",
            nargs="?",
            default=None,
            help="hexadecimal hash of the server destination",
            type=str
        )

        args = parser.parse_args()

        if args.config:
            configarg = args.config
        else:
            configarg = None

        if args.server:
            server(configarg)
        else:
            if (args.destination == None):
                print("")
                parser.print_help()
                print("")
            else:
                client(args.destination, configarg)

    except KeyboardInterrupt:
        print("")
        exit()