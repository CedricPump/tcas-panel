import math
import tkinter as tk
from threading import Thread
import tcas
from aircraft import AircraftCategory, Advisory
from tcas import Tcas

UI_SIZE = 500
UI_DISPLAY_RANGE = tcas.TCAS_MAX_DISTANCE  # km

class UI(Thread):

    def __init__(self):
        super().__init__()
        self.showVSLimitIndicator = []
        self.vsScale = []
        self.started = False
        self.tcas = None
        self.root = tk.Tk()
        self.root.title("TCAS2")
        self.root.geometry("500x620")
        self.useDummy = False
        self.dummyPlane = None
        self.aircraftIcons = []
        self.compassIcons = []
        self.vsIndicator = []

        self.canvas = tk.Canvas(self.root, width=UI_SIZE, height=UI_SIZE, bg="darkgrey")
        self.canvas.create_oval(0, 0, UI_SIZE, UI_SIZE, fill="black")
        self.canvas.create_oval(UI_SIZE/2-2, UI_SIZE/2-2, UI_SIZE/2+4, UI_SIZE/2+4, fill="grey")
        self.canvas.create_oval(0 + UI_SIZE * 1 / 6, 0 + UI_SIZE * 1 / 6, 0 + UI_SIZE * 5 / 6, 0 + UI_SIZE * 5 / 6, outline="grey", width=1)
        self.canvas.create_oval(0 + UI_SIZE * 2 / 6, 0 + UI_SIZE * 2 / 6, 0 + UI_SIZE * 4 / 6, 0 + UI_SIZE * 4 / 6, outline="grey", width=1)
        self.gpsLabel = tk.Label(self.root, width=UI_SIZE, text="")
        self.taraLabel = tk.Label(self.root, width=UI_SIZE, text="", fg="black", font='Helvetica 18 bold')
        self.startButton = tk.Button(self.root, width=UI_SIZE, height=40, text="Start", command=self.onClick)
        self.updateDisplay()
        self.displayVSScale()

        self.canvas.pack()
        self.gpsLabel.pack()
        self.taraLabel.pack()
        self.startButton.pack()

    def onClick(self):
        if not self.started:
            self.tcas = Tcas(self, self.useDummy)
            if self.useDummy:
                self.tcas.ownPlane = self.dummyPlane
            self.tcas.start()
            self.startButton["text"] = "Stop"
        else:
            Tcas.stop()
            self.tcas.join()
            self.startButton["text"] = "Start"
            self.clearAircraftDisplay()
        self.started = not self.started

    def updateLabel(self, labelString):
        self.gpsLabel["text"] = labelString

    def run(self):
        self.root.mainloop()

    def popup(self, string):
        self.updateLabel(string)

        win = tk.Toplevel()
        win.wm_title("Window")

        l = tk.Label(win, text=string)
        l.grid(row=0, column=0)

        b = tk.Button(win, text="Okay", command=win.destroy)
        b.grid(row=1, column=0)

        Tcas.stop()
        self.startButton["text"] = "Start"
        self.started = False

    def displayAircraft(self):
        self.clearAircraftDisplay()

        for aircraft in self.tcas.knownAircrafts.values():
            if len(aircraft.history):
                labalcolor = ""
                dist = aircraft.getLastDistance()
                bear = aircraft.getLastBearing()
                xy = self.getPointDistAndBear(dist=dist, bear=bear)
                x = xy[0]
                y = xy[1]

                icon = None
                if aircraft.type == AircraftCategory.OTHER:
                    icon = self.canvas.create_polygon([x-5, y, x, y+7, x+5, y, x, y-7], fill="grey")
                    labalcolor = "grey"
                elif aircraft.type == AircraftCategory.PROXIMATE:
                    icon = self.canvas.create_polygon([x-5, y, x, y+7, x+5, y, x, y-7], fill="white")
                    labalcolor = "white"
                elif aircraft.type == AircraftCategory.TA:
                    icon = self.canvas.create_oval(x-4, y-4, x+8, y+8, fill="yellow")
                    labalcolor = "yellow"
                elif aircraft.type == AircraftCategory.RA:
                    icon = self.canvas.create_polygon([x-4, y-4, x+4, y-4, x+4, y+4, x-4, y+4], fill="red")
                    labalcolor = "red"
                self.aircraftIcons.append(icon)

                # add labels
                vSep = aircraft.getLatvSep()
                vs = aircraft.lastMessage.get('data').get('vs')
                offset = 15
                offsetFactor = 1
                sign = "+"
                if abs(vSep) < 100:
                    sign = ""
                    offsetFactor = -1
                elif vSep >= 0:
                    offsetFactor = -1
                    sign = "-"

                icon = nIcon = self.canvas.create_text(x, y + -offsetFactor * offset, fill=labalcolor, font="Times 10", text=f"{sign}{abs(round(vSep/100)):02d}")
                self.aircraftIcons.append(icon)

                if abs(vs) > 50:
                    if vs > 0:
                        arrow = tk.LAST
                    else:
                        arrow = tk.FIRST
                    icon = self.canvas.create_line(x+13, y+8, x+13, y-8, arrow=arrow, fill=labalcolor)
                    self.aircraftIcons.append(icon)

    def clearAircraftDisplay(self):
        for icon in self.aircraftIcons:
            self.canvas.delete(icon)
        self.aircraftIcons = []

    def displayTARA(self, adv):
        noTAAural = True
        if self.tcas is not None:
            noTAAural = self.tcas.ownPlane.alt_agl < tcas.TCAS_TA_NO_AURAL
        color = "black"
        text = ""
        if adv is not None:
            if adv.type == tcas.AdvisoryType.TA:
                if not noTAAural:
                    color = "orange"
                    text = "TRAFFIC TRAFFIC"
            if adv.type == tcas.AdvisoryType.RA:
                color = "red"
                text = adv.alert
            if adv.type == tcas.AdvisoryType.CC:
                color = "blue"
                text = "CLEAR OF CONFLICT"

        self.taraLabel["text"] = text
        self.taraLabel.configure(fg=color)

    def resetTARADisplay(self):
        self.taraLabel["text"] = "text"
        self.taraLabel.configure(fg="black")


    def getPointDistAndBear(self, dist, bear):
        dist = dist / UI_DISPLAY_RANGE * UI_SIZE / 2
        centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
        relBear = bear
        if self.tcas is not None:
            hdg = self.tcas.ownPlane.hdg
            relBear = (360 + bear - hdg) % 360
        bearInRad = relBear * math.pi / 180
        x = centerpoint[0] + (dist * (math.sin(bearInRad)))
        y = centerpoint[1] - (dist * (math.cos(bearInRad)))
        return [x, y]

    def updateDisplay(self):
        angle = 0
        if self.tcas is not None:
            angle = self.tcas.ownPlane.hdg
        for icon in self.compassIcons:
            self.canvas.delete(icon)
        self.compassIcons = []
        for i in range(0, 360, 30):
            point = self.getPointDistAndBear(tcas.TCAS_MAX_DISTANCE - 2000, i)
            icon = self.canvas.create_text(point[0], point[1], fill="grey", font="Times 10", text=f"{round(i/10)}")
            self.canvas.itemconfigure(icon, angle=((360+angle-i) % 360))
            self.compassIcons += [icon]

        point = self.getPointDistAndBear(tcas.TCAS_MAX_DISTANCE - 4500, 0)
        icon = self.canvas.create_text(point[0], point[1], fill="grey", font="Times 10", text=f"N")
        self.compassIcons += [icon]
        self.canvas.itemconfigure(icon, angle=angle)

        self.displayVSIndicator()
        #self.showVSLimits2(-20, 20)


    def checkAdvisoryLevel(self):
        mostSevereAdv = None
        mostSev = 0
        for ac in self.tcas.knownAircrafts.values():
            adv = ac.advisory  # type: Advisory
            if adv is not None:
                if adv.type.value > mostSev:
                    mostSev = adv.type.value
                    mostSevereAdv = adv
        self.displayTARA(mostSevereAdv)
        # if mostSevereAdv is not None:
            # self.showVSLimits(mostSevereAdv.minimalVerticalSpeed, mostSevereAdv.minimalVerticalSpeed)

    def displayVSIndicator(self):
        for i in self.vsIndicator:
            self.canvas.delete(i)

        centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
        vsNull = 270
        angle = 0
        if self.tcas is not None:
            angle = self.tcas.ownPlane.vs / 500 * 10
        offsetAngle = (270 + angle) % 360
        angleInRad = offsetAngle * math.pi / 180
        x = centerpoint[0] + (UI_SIZE / 2 * 0.99 * (math.sin(angleInRad)))
        y = centerpoint[1] - (UI_SIZE / 2 * 0.99 * (math.cos(angleInRad)))
        a = centerpoint[0] + (UI_SIZE / 2 * 1/2 * (math.sin(angleInRad)))
        b = centerpoint[1] - (UI_SIZE / 2 * 1/2 * (math.cos(angleInRad)))
        icon = self.canvas.create_line(a, b, x, y, arrow=tk.LAST, fill="white", width=3)
        self.vsIndicator += [icon]

    def displayVSScale(self):
        for i in range(-80, 90, 10):
            centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
            angle = i*100 / 500 * 10
            offsetAngle = (270 + angle) % 360
            angleInRad = offsetAngle * math.pi / 180
            x = centerpoint[0] + (UI_SIZE / 2 * (math.sin(angleInRad)))
            y = centerpoint[1] - (UI_SIZE / 2 * (math.cos(angleInRad)))
            a = centerpoint[0] + (UI_SIZE / 2 * 9.5 / 10 * (math.sin(angleInRad)))
            b = centerpoint[1] - (UI_SIZE / 2 * 9.5 / 10 * (math.cos(angleInRad)))
            icon = self.canvas.create_line(a, b, x, y, fill="white")
            self.vsScale += [icon]
            x = centerpoint[0] + (UI_SIZE / 2 * 9 / 10 * (math.sin(angleInRad)))
            y = centerpoint[1] - (UI_SIZE / 2 * 9 / 10 * (math.cos(angleInRad)))
            icon = self.canvas.create_text(x, y, fill="white", font="Times 10", text=f"{round(i)}")
            self.vsScale += [icon]
        for i in range(-25, 35, 10):
            centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
            angle = i*100 / 500 * 10
            offsetAngle = (270 + angle) % 360
            angleInRad = offsetAngle * math.pi / 180
            x = centerpoint[0] + (UI_SIZE / 2 * (math.sin(angleInRad)))
            y = centerpoint[1] - (UI_SIZE / 2 * (math.cos(angleInRad)))
            a = centerpoint[0] + (UI_SIZE / 2 * 9.75 / 10 * (math.sin(angleInRad)))
            b = centerpoint[1] - (UI_SIZE / 2 * 9.75 / 10 * (math.cos(angleInRad)))
            icon = self.canvas.create_line(a, b, x, y, fill="white")
            self.vsScale += [icon]


    def showVSLimits(self, min, max):
        if min == 0.0 and max == 0.0:
            for i in self.showVSLimitIndicator:
                self.canvas.delete(i)
            return
        for i in self.showVSLimitIndicator:
            self.canvas.delete(i)

        for i in range(-300, 300):
            centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
            angle = i*100 / 300
            offsetAngle = (270 + angle) % 360
            angleInRad = offsetAngle * math.pi / 180
            x = centerpoint[0] + (UI_SIZE / 2 * (math.sin(angleInRad)))
            y = centerpoint[1] - (UI_SIZE / 2 * (math.cos(angleInRad)))
            a = centerpoint[0] + (UI_SIZE / 2 * 0.97 * (math.sin(angleInRad)))
            b = centerpoint[1] - (UI_SIZE / 2 * 0.97 * (math.cos(angleInRad)))
            if i < min or i > max:
                color = "red"
            else:
                color = "green"
            icon = self.canvas.create_line(a, b, x, y, fill=color, width=9)
            self.showVSLimitIndicator += [icon]

    def showVSLimits2(self, min, max):
        if min == 0.0 and max == 0.0:
            for i in self.showVSLimitIndicator:
                self.canvas.delete(i)
            return
        redPart = self.canvas.create_arc(0+2, 0+2, UI_SIZE-2, UI_SIZE-2, start=0, extent=180, outline="red", width=4)
