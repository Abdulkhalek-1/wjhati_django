# File: apis/route_optimizer.py
from math import asin, cos, radians, sin, sqrt
# File: apis/route_optimizer.py
def nearest_neighbor_route(locations):
    if len(locations) <= 2:
        return locations

    def haversine(a, b):
        lon1, lat1, lon2, lat2 = map(radians, [a[1], a[0], b[1], b[0]])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a2 = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a2))
        return 6371 * c

    unvisited = locations[:]
    route = [unvisited.pop(0)]

    while unvisited:
        last = route[-1]
        next_loc = min(unvisited, key=lambda loc: haversine(last, loc))
        route.append(next_loc)
        unvisited.remove(next_loc)

    return route

