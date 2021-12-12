import json
import math
import time
import uuid
from enum import Enum
from threading import Thread

import geopy
import geopy.distance
import paho.mqtt.client as mqtt

import plane
from aircraft import Aircraft
from geoUtils import get_bearing

abort = False
MQTT_TCAS_CHANNEL = "cedricpump.de/thluebeck/tcas"
meterstofeet = 3.28084

class MessageMode(Enum):
    ALLCALL = 0
    BROADCAST = 1
    SELECTIVE = 2
    INTEROGATE = 3

class Tcas(Thread):
    def __init__(self, ui):
        super().__init__()
        global abort
        abort = False
        self.myPlane = plane.PlaneDummy()
        self.myPlane.setPos(15000, 53.8036111, 10.7148917, 200, 200, 270)
        self.ui = ui
        self.client = None

        self.knownAircraft = {}
        self.TransponderMode = "Mode S"
        self.maxRange = 0  # nm
        self.transmitInterval = 1  # sec
        self.aircraftIdentification = f"{uuid.uuid4()}"

        # hight readout 25 ft increments
        # displayed to controller in 100 ft

        # modes:
        # AllCall (interogateion of Mode S)
        # Broadcast (no response)
        # Selective (selction by identification)
        # Interogate (Mode A and C respond with 4096 Codes)

        # Cathegories: OTHER, PROXIMATE, TA, RA
        # attribute of aircraft: vertical seperation, range, vertical rate, range rate

        # TAU = disance / v_own + v_intruder
        #

    @staticmethod
    def stop():
        global abort
        abort = True

    def run(self):
        global abort
        self.myPlane.connect()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect("mqtt.eclipseprojects.io", 1883, 60)
        self.client.loop_start()
        self.startAquisitionBroadcast()

    def detect(self):
        pass

    def track(self):
        pass

    def sendShortSquitter(self):
        self.myPlane.update()
        message = json.dumps({"mode": MessageMode.BROADCAST.name, "address": f"{self.aircraftIdentification}",
                              "data": self.myPlane.getAsDict()})
        self.client.publish(MQTT_TCAS_CHANNEL, payload=message, qos=0, retain=False)
        self.ui.updateLabel(
            f"GPS: {geopy.Point(latitude=self.myPlane.lat, longitude=self.myPlane.long)} ALT: {round(self.myPlane.alt)} ft VS: {round(self.myPlane.vs)} ft/min GS: {round(self.myPlane.gs)} knt")

    def startAquisitionBroadcast(self):
        while not abort:
            self.sendShortSquitter()
            time.sleep(1)

        self.client.disconnect()


    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe(MQTT_TCAS_CHANNEL)


    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        print(msg.topic + " " + str(msg.payload))

        message = json.loads(msg.payload)
        if message.get('address') != self.aircraftIdentification:

            if message.get('mode') == MessageMode.BROADCAST.name:
                self.listenToSquitter(message)






        #if(msg.payload.data)


    def listenToSquitter(self, message):
        address = message.get('address')
        lastPos = self.myPlane.point
        otherPlanePos = geopy.Point(message.get('data').get('lat'), message.get('data').get('long'))
        distance = geopy.distance.distance(lastPos, otherPlanePos)
        bearing = get_bearing(lastPos, otherPlanePos)
        verticalSeparation = self.myPlane.alt - message.get('data').get('alt')
        print(f"dist: {distance}, bear: {bearing}, vSep: {verticalSeparation}")

        if address not in self.knownAircraft.keys():
            self.knownAircraft[address] = Aircraft(address)

        aircraft = self.knownAircraft.get(address)
        aircraft.history += {"distance": distance, "bearing": bearing, "verticalSeparation": verticalSeparation}
        # next: calculate range rate and vertical rate