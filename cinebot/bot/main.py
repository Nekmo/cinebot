from cinebot.bot.plugins.days import DaysPlugin
from telegram_bot import BotBase


class CineBot(BotBase):
    commands = (DaysPlugin,)


    def query(self):
        pass