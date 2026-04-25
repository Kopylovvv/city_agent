import os
import json
from groq import Groq
from dotenv import load_dotenv

from core.tools import get_nearby_places, geocode_place
from core.optimizer import optimize_route

load_dotenv()

# описание тулзов при помощи json schema
# чтобы groq понимал как и когда их вызывать
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode_place",
            "description": "ищет gps координаты по текстовому названию места или адресу",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {"type": "string",
                                   "description": "название места и город, например 'эрмитаж спб' или 'галерея аэропорт москва'"}
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nearby_places",
            "description": "ищет интересные места (кафе, музеи, парки) вокруг заданных координат",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "широта"},
                    "lon": {"type": "number", "description": "долгота"},
                    "place_type": {
                        "type": "string",
                        "description": "строгий тип места на английском. другие слова использовать запрещено",
                        "enum": ["cafe", "restaurant", "fast_food", "museum", "monument", "park", "attraction"]
                    },
                    "radius": {"type": "integer", "description": "радиус поиска в метрах, обычно 2000"}
                },
                "required": ["lat", "lon", "place_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_route",
            "description": "принимает список мест и выстраивает их в оптимальный пеший маршрут, экономя время",
            "parameters": {
                "type": "object",
                "properties": {
                    "places": {
                        "type": "array",
                        "description": "список словарей с ключами name, lat, lon, полученный из get_nearby_places",
                        "items": {"type": "object"}
                    }
                },
                "required": ["places"]
            }
        }
    }
]

SYSTEM_PROMPT = """
Ты — точный и строгий AI-логист. 
Твоя единственная задача — строить оптимальные маршруты ИСКЛЮЧИТЕЛЬНО на основе данных от твоих инструментов.

АБСОЛЮТНЫЕ ПРАВИЛА (ЗАПРЕТ НА ГАЛЛЮЦИНАЦИИ):
1. Запрещено выдумывать названия мест, адреса или координаты. 
2. Используй только те локации, которые вернул инструмент `get_nearby_places`.
3. Если места не найдены, прямо скажи об этом и не пытайся ничего сочинять.
4. Если указано конкретное число локаций то столько и выводи

АЛГОРИТМ РАБОТЫ (ЦЕПОЧКА ВЫЗОВОВ):
Шаг 1. Если пользователь назвал место без координат, СНАЧАЛА вызови `geocode_place`. Дождись результата.
Шаг 2. Получив координаты, вызови `get_nearby_places` для поиска нужных объектов. Дождись результата.
Шаг 3. Как только получишь JSON со списком реальных мест, СРАЗУ передай их в `optimize_route`.
Шаг 4. Сформируй финальный ответ по шаблону ниже.

ШАБЛОН ФИНАЛЬНОГО ОТВЕТА (ОТВЕЧАЙ СТРОГО ТАК):
Привет! Я составил для вас оптимальный маршрут:
1. [Название места] - [координаты места]
2. [Название места] - [координаты места]
... и так далее.

Статистика маршрута:
- Если идти случайно (baseline): [baseline_km] км
- Оптимизированный путь: [optimized_km] км
Вы сэкономите: [saved_km] км!
"""


def run_agent(user_query: str) -> str:
    """
    основной цикл работы агента
    общается с llm, вызывает локальные функции и возвращает финальный текст
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "ошибка: не найден GROQ_API_KEY в файле .env"

    client = Groq(api_key=api_key)
    model_name = "llama-3.3-70b-versatile"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    # даем агенту 5 шагов чтобы он успел сходить в геокодер, потом за местами, потом в оптимизатор
    for iteration in range(5):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.0 # чтобы не придумывал места и улицы
            )

            response_message = response.choices[0].message

            # если модель решила что инструментов больше не надо и выдала текст
            if not response_message.tool_calls:
                return response_message.content

            # запоминаем вызов в истории
            messages.append(response_message)

            # обрабатываем запросы к питоновским функциям
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"[Агент вызывает: {function_name}]")

                if function_name == "geocode_place":
                    result = geocode_place(place_name=function_args.get("place_name"))

                elif function_name == "get_nearby_places":
                    result = get_nearby_places(
                        lat=function_args.get("lat"),
                        lon=function_args.get("lon"),
                        place_type=function_args.get("place_type"),
                        radius=function_args.get("radius", 2000)
                    )

                elif function_name == "optimize_route":
                    raw_result = optimize_route(places=function_args.get("places"))
                    result = json.dumps(raw_result, ensure_ascii=False)

                else:
                    result = json.dumps({"error": "неизвестный инструмент"})

                # скармливаем результат обратно модели
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result
                })

        except Exception as e:
            return f"ошибка в мозгах агента: {str(e)}"

    return "Агент превысил лимит раздумий. Попробуй задать вопрос проще."
