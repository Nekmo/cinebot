from cinebot.bot.plugins.cinemas import CinemasPlugin
from cinebot.bot.plugins.days import DaysPlugin
from telegram_bot import BotBase


class CineBot(BotBase):
    commands = (DaysPlugin, CinemasPlugin)

    def query(self):
        pass
