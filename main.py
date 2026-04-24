from core.agent import run_agent


def main():
    print("городской AI-гид запущен!")
    print("напиши где ты находишься и что хочешь посмотреть")
    print("например: 'я у гидропроекта в Москвк, найди 2 кафе и 1 парк'")
    print("для выхода напиши 'exit' или 'quit'\n")

    while True:
        try:
            query = input("Местоположение и предпочтения по маршруту: ")

            if not query.strip():
                continue

            if query.lower() in ['exit', 'quit', 'выход']:
                print("до встречи! удачного маршрута")
                break

            print("агент строит маршрут...\n")

            response = run_agent(query)

            print("==================== МАРШРУТ =====================")
            print(response)
            print("==================================================\n")

        except KeyboardInterrupt:
            print("\nвыход из программы...")
            break
        except Exception as e:
            print(f"\nошибка в главном цикле: {str(e)}")


if __name__ == "__main__":
    main()