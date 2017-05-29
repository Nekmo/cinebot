from cinebot.bot.multicine import Multicine
from cinebot.services.cinesur import CinesurService
from cinebot.services.yelmo import YelmoService
from telegram_bot.plugins.base import PluginBase, button_target
from telegram_bot.utils.telegram import escape_items

memory_films = set()


def save_film_to_memory(film):
    """Guardar una película a memoria para reutilizarla en un callback.
    Devolverá un id corto con el que recuperarla.
    """
    pass


class DaysPlugin(PluginBase):
    def set_handlers(self):
        self.main.set_message_handler(self.today, commands=['today'])

    # def today(self, message):
    #     from cinebot.services.cinesur import CinesurService
    #     films = CinesurService().find_by_name('Miramar').get_films()
    #     body = []
    #     for film in films:
    #         body.append('<b>{name}</b>: {times}'.format(**escape_items(
    #             name=film.name, times=', '.join([str(time) for time in film.get_times()])
    #         )))
    #     message.response('\n'.join(body), parse_mode='html').send()

    def today(self, message):
        films_groups = Multicine([
            YelmoService().find_by_name('Plaza Mayor'),
            CinesurService().find_by_name('Miramar'),
        ]).grouped_films()
        msg = message.response('Cartelera de hoy', parse_mode='html')
        inline = msg.inline_keyboard()
        for film_group in films_groups:
            inline.add_button(film_group[0].name, callback=self.film_times, callback_kwargs={'f': id(film_group[0])})
            films_set.add(film_group[0])
        msg.send()

    @button_target
    def film_times(self, film_memory_id):
        pass



