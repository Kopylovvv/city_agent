import requests
import json

def get_nearby_places(lat: float, lon: float, place_type: str, radius: int = 2000) -> str:
    """
    парсит места через бесплатный overpass api
    возвращает json строку с результатами чтобы скормить ее агенту
    """
    # TODO: написать запрос к openstreetmap
    return json.dumps([{"name": "test", "lat": 0.0, "lon": 0.0}])