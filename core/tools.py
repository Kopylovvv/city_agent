import requests
import json


def get_nearby_places(lat: float, lon: float, place_type: str, radius: int = 2000) -> str:
    """
    ищет места рядом с указанными координатами через openstreetmap
    args:
    - lat: широта
    - lon: долгота
    - place_type: тип места на английском (например 'cafe', 'museum', 'monument', 'park')
    - radius: радиус поиска в метрах
    """
    overpass_url = "http://overpass-api.de/api/interpreter"

    # используем nwr чтобы искать не только точки, но и здания/парки
    # out center заставит api вычислить центральную точку для больших объектов
    overpass_query = f"""
    [out:json];
    (
      nwr["amenity"="{place_type}"](around:{radius},{lat},{lon});
      nwr["tourism"="{place_type}"](around:{radius},{lat},{lon});
      nwr["historic"="{place_type}"](around:{radius},{lat},{lon});
      nwr["leisure"="{place_type}"](around:{radius},{lat},{lon});
    );
    out center 15;
    """

    headers = {
        'User-Agent': 'CityGuideAgent/1.0 (Hackathon Project)'
    }

    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        places = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            name = tags.get('name')

            # вытаскиваем координаты (для точек это lat/lon, для зданий они лежат в center)
            lat_val = element.get('lat') or (element.get('center', {})).get('lat')
            lon_val = element.get('lon') or (element.get('center', {})).get('lon')

            if name and lat_val and lon_val:
                places.append({
                    "name": name,
                    "lat": lat_val,
                    "lon": lon_val,
                    "type": place_type
                })

        print(f"->[OSM нашел {len(places)} мест типа '{place_type}']")

        if not places:
            return json.dumps({"error": f"не удалось найти {place_type} поблизости"})

        # возвращаем топ-3 мест чтобы не раздувать контекст нейросети
        return json.dumps(places[:3], ensure_ascii=False)

    except Exception as e:
        print(f"->[ОШИБКА OSM: {str(e)}]")
        return json.dumps({"error": f"ошибка api: {str(e)}"})


def geocode_place(place_name: str) -> str:
    """
    переводит текстовое название улицы или места в gps координаты через nominatim
    """
    url = "https://nominatim.openstreetmap.org/search"

    headers = {
        'User-Agent': 'CityGuideAgent/1.0 (Hackathon Project)'
    }

    params = {
        'q': place_name,
        'format': 'json',
        'limit': 1
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            print(f"->[геокодер нашел '{place_name}': {lat}, {lon}]")
            return json.dumps({"lat": lat, "lon": lon})

        print(f"->[геокодер не нашел: {place_name}]")
        return json.dumps({"error": f"координаты для '{place_name}' не найдены"})

    except Exception as e:
        return json.dumps({"error": str(e)})