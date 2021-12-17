import collections
import json
import time
import uuid
from enum import Enum
from threading import Thread
import geopy
import geopy.distance
import paho.mqtt.client as mqtt
import plane
from aircraft import Aircraft, AircraftCategory, Advisory
from geoUtils import getBearing

abort = False
MQTT_TCAS_HOST = "localhost"
MQTT_TCAS_CHANNEL = "cedricpump.de/thluebeck/tcas"
METERS_TO_FEET = 3.28084
NM_TO_METERS = 1852
METERS_TO_NM = 1 / NM_TO_METERS
TCAS_MAX_DISTANCE = 30 * NM_TO_METERS  # 10 NM
TCAS_MAX_VERTICAL_SEPARATION = 9900  # ft
TCAS_PROXIMATE_LIMIT = 6 * NM_TO_METERS  # 6NM
TCAS_PROXIMATE_VS_LIMIT = 1200  # ft
TCAS_AIRCRAFT_TIMEOUT = 30  # sec
VS_MIN = -10000
VS_MAX = 10000


class MessageMode(Enum):
    ALLCALL = 0
    BROADCAST = 1
    SELECTIVE = 2
    INTEROGATE = 3


class MessageType(Enum):
    SHORT_SQUITTER = 0
    LONG_SQUITTER = 1
    INTEROGATION = 2
    RESOLUTION_REQUEST = 3
    RESOLUTION_RESPONSE = 4


class AdvisoryType(Enum):
    NONE = 0
    TA = 1
    CC = 2
    RA = 3


TcasThresholds = {
    2350: {"TA_SensitivityLevel": 3, "TA_TAU": 25, "TA_DMOD": 0.33, "TA_ZTHR": 850,
           "RA_SensitivityLevel": 3, "RA_TAU": 15, "RA_DMOD": 0.2, "RA_ZTHR": 600},
    5000: {"TA_SensitivityLevel": 4, "TA_TAU": 30, "TA_DMOD": 0.48, "TA_ZTHR": 850,
           "RA_SensitivityLevel": 4, "RA_TAU": 20, "RA_DMOD": 0.35, "RA_ZTHR": 600},
    10000: {"TA_SensitivityLevel": 5, "TA_TAU": 40, "TA_DMOD": 0.75, "TA_ZTHR": 850,
            "RA_SensitivityLevel": 5, "RA_TAU": 25, "RA_DMOD": 0.55, "RA_ZTHR": 600},
    20000: {"TA_SensitivityLevel": 6, "TA_TAU": 45, "TA_DMOD": 1.0, "TA_ZTHR": 850,
            "RA_SensitivityLevel": 6, "RA_TAU": 30, "RA_DMOD": 0.8, "RA_ZTHR": 600},
    42000: {"TA_SensitivityLevel": 7, "TA_TAU": 48, "TA_DMOD": 1.3, "TA_ZTHR": 850,
            "RA_SensitivityLevel": 7, "RA_TAU": 35, "RA_DMOD": 0.1, "RA_ZTHR": 700},
    999999: {"TA_SensitivityLevel": 7, "TA_TAU": 48, "TA_DMOD": 1.3, "TA_ZTHR": 1200,
             "RA_SensitivityLevel": 7, "RA_TAU": 35, "RA_DMOD": 0.1, "RA_ZTHR": 800}
}


TCAS_RA_CLIMB_INHIBITED_ALTITUDE = 4800
TCAS_RA_INC_DESC_INHIBITED_ALTITUDE = 1500
TCAS_RA_DESC_INHIBITED_ALTITUDE = 11000
TCAS_TA_ONLY_ALTITUDE = 1000
TCAS_TA_NO_AURAL = 500


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
            self.client.connect("localhost", 1883, 60)
            self.client.loop_start()
            self.startAquisitionBroadcastLoop()
        except ConnectionError:
            self.ui.popup("Sim not running")
            abort = True

    def detect(self):
        pass

    def track(self):
        pass

    def sendShortSquitter(self):
        self.ownPlane.update()
        message = json.dumps({"mode": MessageMode.BROADCAST.name, "address": f"{self.aircraftIdentification}",
                              "type": MessageType.SHORT_SQUITTER.name,
                              "data": self.ownPlane.getAsDict()})
        self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)
        self.ui.updateLabel(
            f"GPS: {geopy.Point(latitude=self.ownPlane.lat, longitude=self.ownPlane.long)} ALT: {round(self.ownPlane.alt)} ft VS: {round(self.ownPlane.vs)} ft/min GS: {round(self.ownPlane.gs)} knt HDG: {round(self.ownPlane.hdg)}")

    def sendLongSquitter(self, aircraft=None):
        self.ownPlane.update()
        if aircraft is None:
            self.ownPlane.update()
            message = json.dumps({"mode": MessageMode.BROADCAST.name, "address": f"{self.aircraftIdentification}",
                                  "type": MessageType.LONG_SQUITTER.name,
                                  "data": self.ownPlane.getAsDict()})
            self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)
        else:
            message = json.dumps({"mode": MessageMode.SELECTIVE.name, "address": f"{self.aircraftIdentification}",
                                  "receiver": f"{aircraft.identification}",
                                  "type": MessageType.LONG_SQUITTER.name,
                                  "data": self.ownPlane.getAsDict()})
            self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)

    def sendResolutionRequest(self, aircraft):
        message = json.dumps({"mode": MessageMode.SELECTIVE.name, "address": f"{self.aircraftIdentification}",
                              "receiver": f"{aircraft.identification}",
                              "type": MessageType.RESOLUTION_REQUEST.name,
                              "data": aircraft.advisory.opponentSolution})
        self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)
        print(f"Sent RESOLUTION_REQUEST to {aircraft.identification}: solution: {aircraft.advisory.opponentSolution}")

    def sendResolutionResponse(self, aircraft, accept):
        message = json.dumps({"mode": MessageMode.SELECTIVE.name, "address": f"{self.aircraftIdentification}",
                              "receiver": f"{aircraft.identification}",
                              "type": MessageType.RESOLUTION_RESPONSE.name,
                              "data": {"accept": accept}})
        self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)
        print(f"Sent RESOLUTION_RESPONSE to {aircraft.identification}: accept: {accept}")

    def startAquisitionBroadcastLoop(self):
        while not abort:
            self.ui.displayAircraft()
            self.ui.updateDisplay()
            self.sendShortSquitter()
            self.checkAircraftTimout()
            self.ui.checkAdvisoryLevel()
            self.interogate()
            time.sleep(1)

        self.client.disconnect()

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe(f"{MQTT_TCAS_CHANNEL}/#")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        message = json.loads(msg.payload)
        if message.get('address') == self.aircraftIdentification:
            return

        # print(msg.topic + " " + str(msg.payload))

        if message.get('mode') == MessageMode.BROADCAST.name:
            self.listenToSquitter(message)

        if message.get('mode') == MessageMode.SELECTIVE.name:
            if message.get("receiver") == self.aircraftIdentification:
                self.handleMessage(message)

    def listenToSquitter(self, message):
        address = message.get('address')
        lastPos = self.ownPlane.point
        otherPlanePos = geopy.Point(message.get('data').get('lat'), message.get('data').get('long'))
        distance = geopy.distance.distance(lastPos, otherPlanePos).m
        bearing = getBearing(lastPos, otherPlanePos)
        otherPlaneALt = message.get('data').get('alt')
        verticalSeparation = self.ownPlane.alt - otherPlaneALt
        # print(f"dist: {distance * METERS_TO_NM} NMi, bear: {bearing} deg, vSep: {verticalSeparation} ft")

        # check if out of range
        if distance > TCAS_MAX_DISTANCE or abs(verticalSeparation) > TCAS_MAX_VERTICAL_SEPARATION:
            if address in self.knownAircrafts.keys():
                self.knownAircrafts.pop(address)
            return

        # Save Entry to known Aircrafts
        if address not in self.knownAircrafts.keys():
            self.knownAircrafts[address] = Aircraft(address)

        aircraft = self.knownAircrafts.get(address)  # type: Aircraft
        aircraft.lastMessage = message
        aircraft.saveEntry({"time": time.monotonic(), "distance": distance, "bearing": bearing,
                            "verticalSeparation": verticalSeparation})
        self.knownAircrafts[address] = aircraft
        # print(aircraft.history)

        tau = 0
        vSepMin = 0

        # If rates are known calculate TAU and CPA
        if aircraft.rangeRate is not None:
            noRA = self.ownPlane.alt_agl < TCAS_TA_ONLY_ALTITUDE

            # print(f"rangeRate: {round(aircraft.rangeRate * 100) / 100} m/s, vert.Rate: {round(aircraft.verticalRate * 100) / 100} ft/s")

            tau = distance / abs(aircraft.rangeRate)
            vSepMin = abs(verticalSeparation + aircraft.verticalRate * tau)
            oldAircraftType = aircraft.type

            tcasThreshold = self.getTcasThreshold()

            if abs(verticalSeparation) <= TCAS_PROXIMATE_VS_LIMIT and distance <= TCAS_PROXIMATE_LIMIT:
                aircraft.type = AircraftCategory.PROXIMATE
            else:
                aircraft.type = AircraftCategory.OTHER

            if aircraft.rangeRate <= 0 and ((tau < tcasThreshold.get("TA_TAU") and vSepMin < tcasThreshold.get("TA_ZTHR")) or (
                    abs(verticalSeparation) < tcasThreshold.get("TA_ZTHR") and distance < tcasThreshold.get("RA_DMOD"))):
                aircraft.type = AircraftCategory.TA
                if aircraft.advisory is None:
                    aircraft.advisory = Advisory(AdvisoryType.TA)

            if not noRA:
                if aircraft.rangeRate <= 0 and (tau < tcasThreshold.get("RA_TAU") and vSepMin < tcasThreshold.get("RA_ZTHR")) or (
                        abs(verticalSeparation) < tcasThreshold.get("RA_ZTHR") and distance < tcasThreshold.get("RA_DMOD")):
                    aircraft.type = AircraftCategory.RA
                    if aircraft.advisory is None:
                        aircraft.advisory = Advisory(AdvisoryType.RA)
                    elif aircraft.advisory.type == AdvisoryType.TA:
                        aircraft.advisory = Advisory(AdvisoryType.RA)

            if aircraft.type == AircraftCategory.OTHER or aircraft.type == AircraftCategory.PROXIMATE:
                if oldAircraftType == AircraftCategory.RA or oldAircraftType == AircraftCategory.TA:
                    aircraft.advisory = Advisory(AdvisoryType.CC)
                else:
                    aircraft.advisory = None
            adv = None
            if aircraft.advisory is not None:
                adv = aircraft.advisory.type

            print(f"{aircraft.type}: old: {oldAircraftType} adv: {adv}, Dist: {round(distance * METERS_TO_NM * 100) / 100}, vertSep: {round(verticalSeparation)} ft, rangeRate: {round(aircraft.rangeRate * 100) / 100} m/s, vert.Rate: {round(aircraft.verticalRate * 100) / 100} ft/s, tau: {round(tau * 100) / 100} s, vSepMin: {round(vSepMin)} ft")

            if aircraft.type == AircraftCategory.RA:
                if aircraft.advisory is not None:
                    if not aircraft.advisory.isSend:
                        self.findResolution(aircraft)
            # TODO tau is 0 Why?

    def checkAircraftTimout(self):
        toBeDeleted = []
        for ac in self.knownAircrafts.values():
            ac = ac  # type: Aircraft
            dt = time.monotonic() - ac.lasUpdate

            if dt > TCAS_AIRCRAFT_TIMEOUT:
                toBeDeleted.append(ac.identification)
        for i in toBeDeleted:
            self.knownAircrafts.pop(i)

    def findResolution(self, aircraft):
        raNoClimb = self.ownPlane.alt > TCAS_RA_CLIMB_INHIBITED_ALTITUDE
        raNoIncDesc = self.ownPlane.alt_agl < TCAS_RA_INC_DESC_INHIBITED_ALTITUDE
        raNoDesc = self.ownPlane.alt_agl < TCAS_RA_DESC_INHIBITED_ALTITUDE

        vsPlus = 0  # in ft/min
        distance = aircraft.getLastDistance()
        verticalSeparation = aircraft.getLatvSep()
        tau = distance / abs(aircraft.rangeRate)
        tcasThreshold = self.getTcasThreshold()

        # check increase vs
        resultsUp = collections.OrderedDict()
        if not raNoClimb:
            for vsPlus in range(0, VS_MAX, 100):
                vSepMin = abs(verticalSeparation + (aircraft.verticalRate + vsPlus / 60) * tau)  # to ft/sec
                if vSepMin > tcasThreshold.get("TA_ZTHR"):
                    resultsUp[vSepMin] = vsPlus

        # check increase vs
        resultsDown = collections.OrderedDict()
        if not raNoDesc or not raNoIncDesc:
            for vsPlus in range(VS_MIN, 0, 100):
                vSepMin = abs(verticalSeparation + (aircraft.verticalRate + vsPlus / 60) * tau)  # to ft/sec
                if vSepMin > tcasThreshold.get("TA_ZTHR"):
                    resultsDown[vSepMin] = vsPlus

        # print(resultsUp)
        # print(resultsDown)

        if len(resultsUp) == 0:
            resultsUp[0] = 0

        if len(resultsDown) == 0:
            resultsDown[0] = 0

        if list(resultsUp.keys())[0] > list(resultsDown.keys())[0]:
            aircraft.advisory.minimalVerticalSpeed = resultsUp[list(resultsUp.keys())[len(resultsUp)-1]]
            aircraft.advisory.maximalVerticalSpeed = resultsUp[list(resultsUp.keys())[0]]
            opponentMaxVS = VS_MIN
            opponentMinVS = 0
            aircraft.advisory.alert = "CLIMB, CLIMB"
            opponentAlert = "DESCEND, DESCEND"
        else:
            aircraft.advisory.maximalVerticalSpeed = resultsDown[list(resultsDown.keys())[len(resultsDown)-1]]
            aircraft.advisory.minimalVerticalSpeed = resultsDown[list(resultsDown.keys())[0]]
            opponentMaxVS = 0
            opponentMinVS = VS_MAX
            aircraft.advisory.alert = "DESCEND, DESCEND"
            opponentAlert = "CLIMB, CLIMB"

        # print(tcasThreshold.get("TA_ZTHR"))
        # print(f"{aircraft.advisory.minimalVerticalSpeed}: {list(resultsUp.keys())[len(resultsUp)-1]}")
        # print(f"{aircraft.advisory.maximalVerticalSpeed}: {list(resultsUp.keys())[0]}")

        aircraft.advisory.opponentSolution = {"alert": opponentAlert, "minimalVerticalSpeed": opponentMinVS, "maximalVerticalSpeed": opponentMaxVS}
        self.sendResolutionRequest(aircraft)
        aircraft.advisory.isSend = True

    def handleMessage(self, message):
        if message.get("type") == MessageType.RESOLUTION_REQUEST.name:
            data = message.get("data")
            aircraft = self.knownAircrafts[message.get('address')]  # type: Aircraft
            # print(f"Received RESOLUTION_REQUEST from {aircraft.identification}: {data}")
            if aircraft.type is not AircraftCategory.RA:
                self.checkResolutionRequest(aircraft, data)
            else:
                if aircraft.advisory.isSend:
                    if aircraft.identification < self.aircraftIdentification:
                        return
                self.checkResolutionRequest(aircraft, data)
        elif message.get("type") == MessageType.RESOLUTION_RESPONSE.name:
            data = message.get("data")
            aircraft = self.knownAircrafts[message.get('address')]  # type: Aircraft
            # print(f"Received RESOLUTION_RESPONSE from {aircraft.identification}: {data}")
            if data["accept"] == True:
                aircraft.advisory.isAccepted = True
            else:
                pass
        elif message.get("type") == MessageType.INTEROGATION.name:
            aircraft = self.knownAircrafts[message.get('address')]  # type: Aircraft
            self.sendLongSquitter(aircraft)
        elif message.get("type") == MessageType.LONG_SQUITTER.name:
            self.listenToSquitter(message)

    def checkResolutionRequest(self, aircraft, data):
        aircraft.type = AircraftCategory.RA
        aircraft.advisory = Advisory(AdvisoryType.RA)
        aircraft.advisory.isSend = True
        aircraft.advisory.alert = data["alert"]
        aircraft.advisory.minimalVerticalSpeed = data["minimalVerticalSpeed"]
        aircraft.advisory.maximalVerticalSpeed = data["maximalVerticalSpeed"]
        self.sendResolutionResponse(aircraft, True)
        aircraft.advisory.isAccepted = True

    def getTcasThreshold(self):
        tcasThreshold = None
        for k in TcasThresholds.keys():
            if k > self.ownPlane.alt:
                tcasThreshold = TcasThresholds.get(k)
                return tcasThreshold

    def interogate(self):
        for ac in self.knownAircrafts.values():
            if time.monotonic() - ac.lasUpdate > 5:
                self.sendInterogation(ac)

    def sendInterogation(self, aircraft):
        message = json.dumps({"mode": MessageMode.SELECTIVE.name, "address": f"{self.aircraftIdentification}",
                              "receiver": f"{aircraft.identification}",
                              "type": MessageType.INTEROGATION.name,
                              "data": {}})
        self.client.publish(f"{MQTT_TCAS_CHANNEL}/{self.aircraftIdentification}", payload=message, qos=0, retain=False)
        print(f"Sent INTEROGATION to {aircraft.identification}")





