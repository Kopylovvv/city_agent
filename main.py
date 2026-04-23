from core.agent import run_agent


def main():
    """
    точка входа в cli
    """
    print(f"привет! я твой гид")
    print("напиши где ты и куда хочешь сходить (или 'exit' для выхода)")

    while True:
        query = input("\nты: ")
        if query.lower() in ['exit', 'quit']:
            break

        print("агент думает...")
        response = run_agent(query)
        print(f"гид: {response}")


if __name__ == "__main__":
    main()