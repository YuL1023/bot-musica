import threading
import keep_alive
import main

if __name__ == "__main__":
    threading.Thread(target=keep_alive.run).start()
    main.bot.run(main.TOKEN)
