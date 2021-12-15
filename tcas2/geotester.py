import math

for i in [0, 45, 90, 135, 180, 270]:

    bear = i
    hdg = 90

    relBear = (360 + bear - hdg) % 360
    # relBear = i

    bearInRad = relBear * math.pi / 180

    x = (1 * math.sin(bearInRad))
    y = (1 * math.cos(bearInRad))

    print(f"{i} {relBear} {bearInRad} {x:2f} {y:2f}")


