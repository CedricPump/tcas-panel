import math


def getBearing(point1, point2):
    p1Lat = math.radians(point1.latitude)
    p1Long = math.radians(point1.longitude)
    p2Lat = math.radians(point2.latitude)
    p2Long = math.radians(point2.longitude)

    dLong = p2Long - p1Long
    if abs(dLong) > math.pi:
        if dLong > 0.0:
            dLong = -(2.0 * math.pi - dLong)
        else:
            dLong = (2.0 * math.pi + dLong)

    tanP1 = math.tan(p1Lat / 2.0 + math.pi / 4.0)
    tanP2 = math.tan(p2Lat / 2.0 + math.pi / 4.0)
    dp = math.log(tanP2 / tanP1)
    return (math.degrees(math.atan2(dLong, dp)) + 360.0) % 360.0

