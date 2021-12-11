import asyncio
import threading

from SimConnect import *

ALTITUDE_KEY = "PLANE_ALTITUDE"
LATITUDE_KEY = "PLANE_LATITUDE"
LONGITUDE_KEY = "PLANE_LONGITUDE"
VERTICAL_SPEED_KEY = "VERTICAL_SPEED"
GROUND_SPEED_KEY = "GROUND_VELOCITY"


class Plane:

    def __init__(self):
        self.sm = None
        self.aq = None
        self._isTracking = False
        self.alt = 0.0
        self.lat = 0.0
        self.long = 0.0
        self.vs = 0.0
        self.gs = 0.0

    def connect(self):
        self.sm = SimConnect()
        self.aq = AircraftRequests(self.sm, _time=500)

    def update(self):
        if self.aq is None:
            self.connect()

        self.alt = self.aq.get(ALTITUDE_KEY)
        self.lat = self.aq.get(LATITUDE_KEY)
        self.long = self.aq.get(LONGITUDE_KEY)
        self.vs = self.aq.get(VERTICAL_SPEED_KEY)
        self.gs = self.aq.get(GROUND_SPEED_KEY)
        print(f"alt: {self.alt}, lat: {self.lat}, long: {self.long}, vs: {self.vs}, gs: {self.gs}")


class PlaneDummy:
    def __init__(self, initAlt, initLat, initLong, hdg, gs, vs):
        self.sm = None
        self.aq = None
        self._isTracking = False
        self.alt = 0.0
        self.lat = 0.0
        self.long = 0.0
        self.vs = 0.0
        self.gs = 0.0

    def connect(self):
        pass

    def update(self):
        # calculate position from time
        print(f"alt: {self.alt}, lat: {self.lat}, long: {self.long}, vs: {self.vs}, gs: {self.gs}")