import math
import requests


def calculate_distance_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    расстояние по прямой

    используется только для оптимизации маршрута
    """
    r = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_real_walking_distance(places: list) -> float:
    """
    реальное расстояние пешком по дорогам через osrm для подсчета дистанции итогого маршрута

    если api недоступно, то рассчет идет по прямым
    """
    if len(places) < 2:
        return 0.0

    # координаты в формате lon,lat;lon,lat для osrm
    coords_string = ";".join([f"{p['lon']},{p['lat']}" for p in places])
    osrm_url = f"http://router.project-osrm.org/route/v1/foot/{coords_string}?overview=false"

    try:
        response = requests.get(osrm_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # перевод в километры
            return round(data['routes'][0]['distance'] / 1000.0, 2)
    except Exception:
        pass  # если api недоступен то рассчет по прямым вместо дорог

    # запасной план (рассчет по прямой)
    fallback_dist = 0.0
    for i in range(len(places) - 1):
        fallback_dist += calculate_distance_haversine(
            places[i]['lat'], places[i]['lon'],
            places[i + 1]['lat'], places[i + 1]['lon']
        )
    return round(fallback_dist, 2)


def optimize_route(places: list) -> dict:
    """
    строит маршрут сравнивая порядок, полученный от пользователя, с оптимальным

    использует реальные дороги для финальных результатов,
    но для рассчета оптимального маршрута используется расстояние по прямой,
    чтобы время ожидания было минимальным

    для оптимизации маршрута используется жадная сортировка,
    поэтому итоговая длина может быть не минимальной
    """
    if not places or len(places) < 2:
        return {"optimized_route": places, "baseline_km": 0.0, "optimized_km": 0.0, "saved_km": 0.0}

    # длмна неоптимизированного маршрута
    baseline_km = get_real_walking_distance(places)

    # жадная сортировка
    unvisited = places.copy()
    optimized_route = [unvisited.pop(0)]

    while unvisited:
        current_place = optimized_route[-1]

        # поиск ближайшей точки по прямой
        closest_place = min(
            unvisited,
            key=lambda p: calculate_distance_haversine(
                current_place['lat'], current_place['lon'],
                p['lat'], p['lon']
            )
        )

        optimized_route.append(closest_place)
        unvisited.remove(closest_place)

    # реальная длина уже отсортированного маршрута
    optimized_km = get_real_walking_distance(optimized_route)

    saved = round(baseline_km - optimized_km, 2)

    return {
        "optimized_route": optimized_route,
        "baseline_km": baseline_km,
        "optimized_km": optimized_km,
        "saved_km": max(0.0, saved)
        # так как используется жадная сортировка,
        # то расстояние итогого маршрута
        # может быть больше, чем изначальное
    }