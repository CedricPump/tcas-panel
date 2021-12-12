import asyncio
import math

import tkinter as tk
from threading import Thread
import plane
import tcas
from aircraft import AircraftCategory
from plane import *
from tcas import Tcas
from track import Tracker

UI_SIZE = 500
UI_DISPLAY_RANGE = tcas.TCAS_MAX_DISTANCE  # km

class UI(Thread):

    def __init__(self):
        super().__init__()
        self.started = False
        self.tcas = None
        self.root = tk.Tk()
        self.root.title("TCAS2")
        self.root.geometry("500x580")
        self.useDummy = False
        self.dummyPlane = None
        self.aircraftIcons = []

        self.canvas = tk.Canvas(self.root, width=UI_SIZE, height=UI_SIZE, bg="darkgrey")
        self.canvas.create_oval(0, 0, UI_SIZE, UI_SIZE, fill="black")
        self.canvas.create_oval(UI_SIZE/2-2.5, UI_SIZE/2-2.5, UI_SIZE/2+5, UI_SIZE/2+5, fill="white")
        self.label = tk.Label(self.root, width=UI_SIZE, text="")
        self.startButton = tk.Button(self.root, width=UI_SIZE, height=40, text="Start", command=self.onClick)

        self.canvas.pack()
        self.label.pack()
        self.startButton.pack()

    def onClick(self):
        print(f"on Click: {self.started}")
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
        self.label["text"] = labelString

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
                centerpoint = [UI_SIZE / 2, UI_SIZE / 2]
                dist = aircraft.getLastDistance() / UI_DISPLAY_RANGE * UI_SIZE / 2
                bear = aircraft.getLastBearing()
                bearInRad = bear * math.pi / 180

                y = centerpoint[0] + (dist * math.cos(bearInRad))
                x = centerpoint[1] + (dist * math.sin(bearInRad))
                print(f"x: {x}, y: {y}")

                icon = None
                if aircraft.type == AircraftCategory.OTHER.name:
                    icon = self.canvas.create_polygon([x-5, y, x, y+7, x+5, y, x, y-7], fill="grey")
                elif aircraft.type == AircraftCategory.PROXIMATE.name:
                    icon = self.canvas.create_polygon([x-5, y, x, y+7, x+5, y, x, y-7], fill="white")
                elif aircraft.type == AircraftCategory.TA.name:
                    icon = self.canvas.create_oval(x-4, y-4, x+8, y+8, fill="orange")
                elif aircraft.type == AircraftCategory.RA.name:
                    icon = self.canvas.create_polygon([x-4, y-4, x+4, y-4, x+4, y+4, x-4, y+4], fill="red")
                self.aircraftIcons.append(icon)

    def clearAircraftDisplay(self):
        for icon in self.aircraftIcons:
            self.canvas.delete(icon)
