import os
import json
from groq import Groq
from dotenv import load_dotenv

from core.tools import get_nearby_places
from core.optimizer import optimize_route

load_dotenv()

# описание тулзов при помощи json schema
# чтобы groq понимал как и когда их вызывать
TOOLS = [
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
                    "place_type": {"type": "string",
                                   "description": "тип места на английском, например 'cafe', 'museum', 'monument'"},
                    "radius": {"type": "integer", "description": "радиус поиска в метрах, по умолчанию 2000"}
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
                        "description": "список словарей с ключами name, lat, lon",
                        "items": {"type": "object"}
                    }
                },
                "required": ["places"]
            }
        }
    }
]

SYSTEM_PROMPT = """
ты умный туристический гид
твоя цель - помочь пользователю составить идеальный пеший маршрут
ты должен использовать доступные инструменты для поиска реальных мест и оптимизации пути

правила:
1. если пользователь не дал координаты, попроси его уточнить где он находится
2. используй get_nearby_places чтобы найти нужные локации
3. обязательно пропусти найденные места через optimize_route
4. в финальном ответе красиво распиши маршрут по шагам
5. обязательно укажи сколько километров удалось сэкономить (сравни baseline_km и optimized_km и выведи saved_km)
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

    # модель llama 3 на 8 миллиардов параметров
    # можно поменять на {llama3-70b-8192}, если нужна модель поумнее и есть подходящее железо)))
    model_name = "llama3-8b-8192"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    try:
        # первый запрос к модели
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2048
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # если модель решила, что инструменты не нужны (например просто здоровается)
        if not tool_calls:
            return response_message.content

        # если модель решила вызвать инструменты
        messages.append(response_message)

        # обрабатываем каждый вызов инструмента
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "get_nearby_places":
                result = get_nearby_places(
                    lat=function_args.get("lat"),
                    lon=function_args.get("lon"),
                    place_type=function_args.get("place_type"),
                    radius=function_args.get("radius", 2000)
                )
            elif function_name == "optimize_route":
                # перевод optimize_route в строку из словаря
                raw_result = optimize_route(places=function_args.get("places"))
                result = json.dumps(raw_result, ensure_ascii=False)
            else:
                result = f"ошибка: неизвестный инструмент {function_name}"

            # отправляем результат работы функции обратно модели
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result
            })

        # второй запрос к модели - финальный ответ с учетом данных от функций
        final_response = client.chat.completions.create(
            model=model_name,
            messages=messages
        )

        return final_response.choices[0].message.content

    except Exception as e:
        return f"ошибка агента: {str(e)}"
