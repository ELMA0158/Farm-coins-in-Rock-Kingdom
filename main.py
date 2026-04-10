from bot_core import RocoAutoBot

if __name__ == "__main__":
    bot = RocoAutoBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        pass