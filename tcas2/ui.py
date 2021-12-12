import asyncio

from tkinter import *
from threading import Thread
import plane
from plane import *
from tcas import Tcas
from track import Tracker


class UI(Thread):

    def __init__(self):
        super().__init__()
        self.started = False
        self.tcas = None
        self.root = Tk()
        self.root.title("TCAS2")
        self.root.geometry("500x580")

        self.canvas = Canvas(self.root, width=500, height=500, bg="darkgrey")
        self.canvas.create_oval(0, 0, 500, 500, fill="black")
        self.label = Label(self.root, width=500, text="")
        self.startButton = Button(self.root, width=500, height=40, text="Start", command=self.onClick)

        self.canvas.pack()
        self.label.pack()
        self.startButton.pack()

    def onClick(self):
        print(f"on Click: {self.started}")
        if not self.started:
            self.tcas = Tcas(self)
            self.tcas.start()
            self.startButton["text"] = "Stop"
        else:
            Tcas.stop()
            self.tcas.join()
            self.startButton["text"] = "Start"
        self.started = not self.started

    def updateLabel(self, labelString):
        print("update")
        self.label["text"] = labelString

    def run(self):
        self.root.mainloop()
