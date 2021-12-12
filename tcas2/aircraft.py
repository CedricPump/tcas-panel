from enum import Enum


class AircraftCategory(Enum):
    OTHER = 0
    PROXIMATE = 1
    TA = 2
    RA = 3


class Aircraft:

    def __init__(self, identification):
        self.identification = identification
        self.history = []
        self.type = AircraftCategory.PROXIMATE.name
        self.rangeRate = None
        self.verticalRate = None
        self.lastMessage = None

    def saveEntry(self, entry):
        self.history.append(entry)
        if len(self.history) > 2:
            self.history.pop(0)
            self.calcRates()

    def calcRates(self):
        if len(self.history) < 2:
            return
        lastRecord = self.history[1]
        prevRecord = self.history[0]
        dt = prevRecord.get("time") - lastRecord.get("time")
        self.rangeRate = (prevRecord.get("distance") - lastRecord.get("distance")) / dt
        self.verticalRate = (prevRecord.get("verticalSeparation") - lastRecord.get("verticalSeparation")) / dt


    def getLastDistance(self):
        return self.history[len(self.history)-1].get("distance")

    def getLastBearing(self):
        return self.history[len(self.history)-1].get("bearing")
