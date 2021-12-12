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
from aircraft import Aircraft, AircraftCategory
from geoUtils import get_bearing

abort = False
MQTT_TCAS_CHANNEL = "cedricpump.de/thluebeck/tcas"
METERS_TO_FEET = 3.28084
NM_TO_METERS = 1852
METERS_TO_NM = 1 / NM_TO_METERS
TCAS_MAX_DISTANCE = 100 * NM_TO_METERS  # 50 NM
TCAS_MAX_VERTICAL_SEPARATION = 9900  # ft
TCAS_PROXIMATE_LIMIT = 6 * NM_TO_METERS  # 6NM
TCAS_PROXIMATE_VS_LIMIT = 1200  # ft


class MessageMode(Enum):
    ALLCALL = 0
    BROADCAST = 1
    SELECTIVE = 2
    INTEROGATE = 3


class MessageType(Enum):
    SHORT_SQUITTER = 0
    LONG_SQUITTER = 1
    INTEROGATION = 2


TcasThresholds = {
    2350:   {"TA_SensitivityLevel": 3, "TA_TAU": 25, "TA_DMOD": 0.33, "TA_ZTHR": 850,
             "RA_SensitivityLevel": 3, "RA_TAU": 15, "RA_DMOD": 0.2,  "RA_ZTHR": 600},
    5000:   {"TA_SensitivityLevel": 4, "TA_TAU": 30, "TA_DMOD": 0.48, "TA_ZTHR": 850,
             "RA_SensitivityLevel": 4, "RA_TAU": 20, "RA_DMOD": 0.35, "RA_ZTHR": 600},
    10000:  {"TA_SensitivityLevel": 5, "TA_TAU": 40, "TA_DMOD": 0.75, "TA_ZTHR": 850,
             "RA_SensitivityLevel": 5, "RA_TAU": 25, "RA_DMOD": 0.55, "RA_ZTHR": 600},
    20000:  {"TA_SensitivityLevel": 6, "TA_TAU": 45, "TA_DMOD": 1.0,  "TA_ZTHR": 850,
             "RA_SensitivityLevel": 6, "RA_TAU": 30, "RA_DMOD": 0.8,  "RA_ZTHR": 600},
    42000:  {"TA_SensitivityLevel": 7, "TA_TAU": 48, "TA_DMOD": 1.3,  "TA_ZTHR": 850,
             "RA_SensitivityLevel": 7, "RA_TAU": 35, "RA_DMOD": 0.1,  "RA_ZTHR": 700},
    999999: {"TA_SensitivityLevel": 7, "TA_TAU": 48, "TA_DMOD": 1.3,  "TA_ZTHR": 1200,
             "RA_SensitivityLevel": 7, "RA_TAU": 35, "RA_DMOD": 0.1,  "RA_ZTHR": 800}
}


class Tcas(Thread):
    def __init__(self, ui, useDummy):
        super().__init__()
        global abort
        abort = False
        if useDummy:
            self.ownPlane = plane.PlaneDummy()
            self.ownPlane.setPos(15000, 53.8036111, 10.7148917, 200, 200, 270)
        else:
            self.ownPlane = plane.Plane()
        self.ui = ui
        self.client = None

        self.knownAircrafts = {}
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
        try:
            self.ownPlane.connect()
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect("mqtt.eclipseprojects.io", 1883, 60)
            self.client.loop_start()
            self.startAquisitionBroadcast()
        except ConnectionError:
            self.ui.popup("Sim not running")
            abort = True

    def detect(self):
        pass

    def track(self):
        pass

    def sendShortSquitter(self):
        self.ownPlane.update()
        message = json.dumps({"mode": MessageMode.BROADCAST.name, "address": f"{self.aircraftIdentification}", "type": MessageType.SHORT_SQUITTER.name,
                              "data": self.ownPlane.getAsDict()})
        self.client.publish(MQTT_TCAS_CHANNEL, payload=message, qos=0, retain=False)
        self.ui.updateLabel(
            f"GPS: {geopy.Point(latitude=self.ownPlane.lat, longitude=self.ownPlane.long)} ALT: {round(self.ownPlane.alt)} ft VS: {round(self.ownPlane.vs)} ft/min GS: {round(self.ownPlane.gs)} knt HDG: {round(self.ownPlane.hdg)}")

    def startAquisitionBroadcast(self):
        while not abort:
            self.ui.displayAircraft()
            self.sendShortSquitter()
            time.sleep(1)

        self.client.disconnect()

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe(MQTT_TCAS_CHANNEL)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        message = json.loads(msg.payload)
        if message.get('address') == self.aircraftIdentification:
            return

        # print(msg.topic + " " + str(msg.payload))

        if message.get('mode') == MessageMode.BROADCAST.name:
            self.listenToSquitter(message)

    def listenToSquitter(self, message):
        address = message.get('address')
        lastPos = self.ownPlane.point
        otherPlanePos = geopy.Point(message.get('data').get('lat'), message.get('data').get('long'))
        distance = geopy.distance.distance(lastPos, otherPlanePos).m
        bearing = get_bearing(lastPos, otherPlanePos)
        otherPlaneALt = message.get('data').get('alt')
        verticalSeparation = abs(self.ownPlane.alt - otherPlaneALt)
        # print(f"dist: {distance * METERS_TO_NM} NMi, bear: {bearing} deg, vSep: {verticalSeparation} ft")

        # check if out of range
        if distance > TCAS_MAX_DISTANCE or abs(verticalSeparation) > TCAS_MAX_VERTICAL_SEPARATION:
            if address in self.knownAircrafts.keys():
                self.knownAircrafts.pop(address)
            return

        # Save Entry to known Aircrafts
        if address not in self.knownAircrafts.keys():
            self.knownAircrafts[address] = Aircraft(address)

        aircraft = self.knownAircrafts.get(address) # type: Aircraft
        aircraft.lastMessage = message
        aircraft.saveEntry({"time": time.monotonic(), "distance": distance, "bearing": bearing, "verticalSeparation": verticalSeparation})
        self.knownAircrafts[address] = aircraft
        print(aircraft.history)

        tau = 0
        vSepMin = 0

        # If rates are known calculate TAU and CPA
        if aircraft.rangeRate is not None:

            print(f"rangeRate: {round(aircraft.rangeRate*100)/100} m/s, vert.Rate: {round(aircraft.verticalRate*100)/100} ft/s")
            if aircraft.rangeRate <= 0 and aircraft.verticalRate < 0:

                tau = distance / abs(aircraft.rangeRate)
                vSepMin = abs(verticalSeparation + aircraft.verticalRate * tau)

                tcasThreshold = None
                for k in TcasThresholds.keys():
                    if k > self.ownPlane.alt:
                        tcasThreshold = TcasThresholds.get(k)

                if abs(verticalSeparation) <= TCAS_PROXIMATE_VS_LIMIT and distance <= TCAS_PROXIMATE_LIMIT:
                    aircraft.type = AircraftCategory.PROXIMATE.name
                else:
                    aircraft.type = AircraftCategory.OTHER.name

                if (tau < tcasThreshold.get("TA_TAU") and vSepMin < tcasThreshold.get("TA_ZTHR")) or (abs(verticalSeparation) < tcasThreshold.get("TA_ZTHR") and distance < tcasThreshold.get("RA_DMOD")):
                    aircraft.type = AircraftCategory.TA.name

                if (tau < tcasThreshold.get("RA_TAU") and vSepMin < tcasThreshold.get("RA_ZTHR")) or (abs(verticalSeparation) < tcasThreshold.get("RA_ZTHR") and distance < tcasThreshold.get("RA_DMOD")):
                    aircraft.type = AircraftCategory.RA.name

                print(f"Pos: {otherPlanePos} Alt: {round(otherPlaneALt)} ft, Dist: {round(distance * METERS_TO_NM *100)/100}, Bearing: {round(bearing)} deg, vertSep: {round(verticalSeparation)} ft, rangeRate: {round(aircraft.rangeRate*100)/100} m/s, vert.Rate: {round(aircraft.verticalRate*100)/100} ft/s, tau: {round(tau*100)/100} s, vSepMin: {round(vSepMin)} ft")

                # TODO tau is 0 Why?




