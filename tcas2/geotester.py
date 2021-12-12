import geopy
import geopy.distance

from geoUtils import get_bearing

final = geopy.distance.distance(kilometers=5000).destination(point=geopy.Point(latitude=0, longitude=0), bearing=0)

print(get_bearing(geopy.Point(53.80501925899087, 10.717892280311442), geopy.Point(53.83249016362793, 10.704628778867734)))

print(final)