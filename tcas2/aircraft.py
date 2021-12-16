from enum import Enum


class AircraftCategory(Enum):
    OTHER = 0
    PROXIMATE = 1
    TA = 2
    RA = 3


class Advisory:
    def __init__(self, advType):
        self.type = advType
        self.minimalVerticalSpeed = 0
        self.maximalVerticalSpeed = 0
        self.alert = "RA"
        self.opponentSolution = {}
        self.isAccepted = False
        self.isSend = False


class Aircraft:

    def __init__(self, identification):
        self.identification = identification
        self.history = []
        self.type = AircraftCategory.PROXIMATE.name
        self.rangeRate = None
        self.verticalRate = None
        self.lastMessage = None
        self.lasUpdate = 0
        self.advisory = None

    def saveEntry(self, entry):
        self.history.append(entry)
        self.lasUpdate = entry.get("time")
        if len(self.history) > 2:
            self.history.pop(0)
            self.calcRates()

    def calcRates(self):
        if len(self.history) < 2:
            return
        lastRecord = self.history[1]
        prevRecord = self.history[0]
        dt = prevRecord.get("time") - lastRecord.get("time")
        if dt != 0:
            self.rangeRate = (prevRecord.get("distance") - lastRecord.get("distance")) / dt
            self.verticalRate = (prevRecord.get("verticalSeparation") - lastRecord.get("verticalSeparation")) / dt

    def getLastDistance(self):
        return self.history[len(self.history)-1].get("distance")

    def getLastBearing(self):
        return self.history[len(self.history)-1].get("bearing")

    def getLatvSep(self):
        return self.history[len(self.history)-1].get("verticalSeparation")
