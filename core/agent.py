import os
from groq import Groq


def run_agent(user_query: str) -> str:
    """
    главная функция агента
    принимает запрос юзера и решает какие тулзы вызывать
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # TODO: написать логику вызова llm и обработки tools
    return "тут будет ответ агента"