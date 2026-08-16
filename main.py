from runtime.dispatcher import Dispatcher
from runtime.intent_hybrid import HybridIntentClassifier
from config.logger import logger


def main():
    logger.info("Starting Nexa application...")
    # Hybrid router: keyword router first, same-model LLM fallback second.
    # The pipeline, skills, memory, and safety gate are unchanged.
    dispatcher = Dispatcher(router=HybridIntentClassifier())
    dispatcher.initialize()
    print("Nexa is running. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nNexa: See you later.\n")
            logger.info("Nexa application shut down via interrupt.")
            break

        if user_input.lower().strip() in ("exit", "quit", "bye"):
            print("Nexa: See you later.\n")
            logger.info("Nexa application shut down via exit command.")
            break

        if not user_input.strip():
            continue

        try:
            dispatcher.process(user_input)
        except Exception as e:
            logger.exception(f"Unhandled exception while processing input '{user_input}': {e}")
            print(f"Nexa: An error occurred: {e}\n")


if __name__ == "__main__":
    main()