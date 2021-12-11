from threading import Thread
from PyAstronomy import pyasl
import time
import plane

abort = False


class Tracker(Thread):
    def __init__(self, ui):
        global abort
        abort = False
        super().__init__()
        self.myPlane = plane.Plane()
        self.ui = ui

    @staticmethod
    def stop():
        global abort
        abort = True

    def run(self):
        global abort
        self.myPlane.connect()
        while not abort:
            self.myPlane.update()
            # sexa = pyasl.coordsDegToSexa(self.myPlane.long, self.myPlane.lat, True)
            self.ui.updateLabel(f"LAT: {round(self.myPlane.lat*10000)/10000} LONG: {round(self.myPlane.long*10000)/10000} ALT: {round(self.myPlane.alt)} ft VS: {round(self.myPlane.vs)} ft/min GS: {round(self.myPlane.gs)} knt")
            time.sleep(0.050)