import asyncio
import datetime
import json
import threading

import geopy
import geopy.distance
import time



from SimConnect import *

ALTITUDE_KEY = "PLANE_ALTITUDE"
LATITUDE_KEY = "PLANE_LATITUDE"
LONGITUDE_KEY = "PLANE_LONGITUDE"
VERTICAL_SPEED_KEY = "VERTICAL_SPEED"
GROUND_SPEED_KEY = "GROUND_VELOCITY"
HEADING_KEY = "PLANE_HEADING_DEGREES_TRUE"

feettometers = 0.3048

class Plane:

    def __init__(self):
        self.sm = None
        self.aq = None
        self._isTracking = False
        self.alt = 0.0
        self.lat = 0.0
        self.long = 0.0
        self.hdg = 0.0
        self.vs = 0.0
        self.gs = 0.0
        self.point = geopy.Point(0, 0, 0)

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
        self.hdg = self.aq.get(HEADING_KEY)
        self.point = geopy.Point(self.lat, self.long)
        #print(f"alt: {self.alt}, lat: {self.lat}, long: {self.long}, vs: {self.vs}, gs: {self.gs}")

    def getAsDict(self):
        return {"alt": self.alt, "lat": self.lat, "long": self.long, "vs": self.vs, "gs": self.gs}




class PlaneDummy(Plane):
    def __init__(self):
        super().__init__()
        self.lastTime = time.monotonic()

    def setPos(self, alt, lat, long, vs, gs, hdg):
        self.alt = alt
        self.lat = lat
        self.long = long
        self.hdg = hdg
        self.vs = vs
        self.gs = gs
        self.lastTime = time.monotonic()

    def connect(self):
        pass

    def update(self):
        # calculate position from time
        # time passed in sec
        dtime = time.monotonic() - self.lastTime
        self.lastTime = time.monotonic()
        # altitude
        self.alt = self.alt + self.vs * dtime / 60                                              # ft + ft/min * sec / 60
        # new position
        knttoms = 0.514444
        range = self.gs * knttoms * dtime / 1000                                  # gs in knots to m/s * time in s to km
        self.point = geopy.distance.distance(kilometers=range).destination(point=geopy.Point(latitude=self.lat, longitude=self.long), bearing=self.hdg)
        self.lat = self.point.latitude
        self.long = self.point.longitude
        # self.hdg = (self.hdg + 10) % 360

        # print(f"alt: {self.alt}, lat: {self.lat}, long: {self.long}, vs: {self.vs}, gs: {self.gs}")




