# File: apis/driver_selector.py
from math import radians, sin, cos, sqrt, asin
from .models import Driver

def haversine_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def select_best_driver(requests, drivers):
    scored = []
    for driver in drivers:
        try:
            d_lat, d_lon = map(float, driver.where_location.split(','))
            total_dist = 0.0
            count = 0
            for req in requests:
                p_lat, p_lon = map(float, req.from_location.split(','))
                d2_lat, d2_lon = map(float, req.to_location.split(','))
                total_dist += haversine_distance(d_lat, d_lon, p_lat, p_lon)
                total_dist += haversine_distance(d_lat, d_lon, d2_lat, d2_lon)
                count += 2
            avg_dist = total_dist / count if count > 0 else float('inf')
        except Exception:
            avg_dist = float('inf')
        scored.append((avg_dist, driver))
    scored.sort(key=lambda x: x[0])
    return scored[0][1] if scored and scored[0][0] != float('inf') else None


