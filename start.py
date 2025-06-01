import threading
import keep_alive
import main

if __name__ == "__main__":
    # Inicia el servidor Flask en un hilo separado
    t = threading.Thread(target=keep_alive.run)
    t.start()
    
    # Ejecuta el bot de Discord (bloqueante)
    main.bot.run(main.TOKEN)
