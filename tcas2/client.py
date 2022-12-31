import plane
from ui import UI
import argparse

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('dummy', type=bool, nargs='?', help='simulate dummy plane', default=False)
    parser.add_argument('lat', type=float, nargs='?', help='dummy plane latitude in deg', default=0.0)
    parser.add_argument('long', type=float, nargs='?', help='dummy plane longitude in deg', default=0.0)
    parser.add_argument('alt', type=float, nargs='?', help='dummy plane altitude in ft', default=0.0)
    parser.add_argument('vs', type=float, nargs='?', help='dummy plane vertical speed in ft / min', default=0.0)
    parser.add_argument('gs', type=float, nargs='?', help='dummy plane ground speed in knots', default=0.0)
    parser.add_argument('hdg', type=float, nargs='?', help='dummy plane hdg in deg', default=0.0)

    args = parser.parse_args()

    ui = UI()

    if args.dummy is not None:
        ui.useDummy = args.dummy
        if args.dummy:
            ui.dummyPlane = plane.PlaneDummy()
            ui.dummyPlane.setPos(alt=args.alt, lat=args.lat, long=args.long, vs=args.vs, gs=args.gs, hdg=args.hdg)

    ui.run()
