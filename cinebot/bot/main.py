from cinebot.bot.plugins.cinemas import CinemasPlugin
from cinebot.bot.plugins.days import DaysPlugin, SearchPlugin
from telegram_bot.bot import BotBase


class CineBot(BotBase):
    commands = (DaysPlugin, CinemasPlugin, SearchPlugin)

    def query(self):
        pass
