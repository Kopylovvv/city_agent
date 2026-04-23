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

    # формируем запрос к api
    # ищем сразу по нескольким популярным категориям
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="{place_type}"](around:{radius},{lat},{lon});
      node["tourism"="{place_type}"](around:{radius},{lat},{lon});
      node["historic"="{place_type}"](around:{radius},{lat},{lon});
      node["leisure"="{place_type}"](around:{radius},{lat},{lon});
    );
    out 15;
    """

    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=10)
        response.raise_for_status()
        data = response.json()

        places = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            name = tags.get('name')

            # берем только точки у которых есть имя
            if name:
                places.append({
                    "name": name,
                    "lat": element.get('lat'),
                    "lon": element.get('lon'),
                    "type": place_type
                })

        if not places:
            return json.dumps({"error": f"не удалось найти {place_type} поблизости"})

        # возвращаем топ-5 мест чтобы не раздувать контекст нейросети
        return json.dumps(places[:5], ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"ошибка при поиске мест: {str(e)}"})
