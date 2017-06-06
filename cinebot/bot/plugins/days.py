import time

from telebot.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from cinebot.bot.multicine import Multicine
from cinebot.services.cinesur import CinesurService
from cinebot.services.yelmo import YelmoService
from telegram_bot.plugins.base import PluginBase, button_target
from telegram_bot.types.keyboard import InlineKeyboard
from telegram_bot.utils.telegram import escape_items, username_id_code
from expiringdict import ExpiringDict

# La url debe ser válida para colocarla como una url oculta en el mensaje
HIDDEN_URL = 'http://example.com'

i_memory = 0
memory_film_groups = ExpiringDict(max_len=300, max_age_seconds=60 * 60 * 24)
uptime_time = time.time()


class SessionExpired(Exception):
    pass


def save_film_to_memory(group):
    """Guardar una película a memoria para reutilizarla en un callback.
    Devolverá un id corto con el que recuperarla.
    """
    global i_memory
    global memory_film_groups
    i = i_memory
    memory_film_groups[i] = group
    i_memory += 1
    return i


def to_callback_int(value):
    """Crear una clave para callback con sesión que incluye la fecha para evitar fallos entre
    arranques del bot.
    """
    return '%x.%x' % (int(uptime_time), value)


def from_callback_int(value):
    """Crear una clave para callback con sesión que incluye la fecha para evitar fallos entre
    arranques del bot.
    """
    t, val = [int(x, 16) for x in value.split('.')]
    if t == uptime_time:
        raise SessionExpired
    return val


def set_hidden_data(key, value):
    return '<a href="{}/{}/{}">&#8205;</a>'.format(HIDDEN_URL, key, value)


def get_hidden_data(message, mkey):
    for entity in message.entities:
        if entity.type != 'text_link' or not entity.url.startswith('{}/'.format(HIDDEN_URL)):
            continue
        key, value = entity.url.replace('{}/'.format(HIDDEN_URL), '').split('/', 1)
        if key == mkey:
            return value


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
            YelmoService(self.db).find_by_name('Plaza Mayor'),
            CinesurService(self.db).find_by_name('Miramar'),
        ]).grouped_films()
        msg = message.response('Cartelera de hoy', parse_mode='html')
        inline = msg.inline_keyboard()
        self.billboard_markup(films_groups, inline)
        msg.send()

    def billboard_markup(self, films_groups, inline):
        for film_group in films_groups:
            i = save_film_to_memory({'film_group': film_group, 'film_groups': films_groups})
            inline.add_button(film_group[0].name, callback=self.film_times,
                              callback_kwargs={'i': to_callback_int(i)})

    @button_target
    def film_times(self, query, i):
        try:
            films_group_data = memory_film_groups[from_callback_int(i)]
        except (KeyError, SessionExpired):
            self.bot.send_message(query.message.chat.id, '¡Sesión caducada! Repita el comando, por favor.')
            return
        film_group = films_group_data['film_group']
        film = film_group[0]
        text = '<b>{name}</b>\nSesión del día: {date}\n{description}\n\n'.format(**escape_items(
            name=film.name,  date=str(film.date), description=film.get_description()))
        for film in film_group:
            text += '<b>{f}</b>\n{t}\n'.format(**escape_items(f=film.location.name,
                                                              t=' '.join(map(str, film.get_times()))))
        markup = InlineKeyboard(self.main)
        markup.add_button('Volver atrás', callback=self.back_billboard, callback_kwargs={'i': i})
        self.bot.delete_message(query.message.chat.id, query.message.message_id)
        image = film.get_image()
        if image is not None:
            msg = self.bot.send_photo(query.message.chat.id, open(image, 'rb'))
            # Establecer oculto id del poster
            text += set_hidden_data('message_id', msg.message_id)
        self.bot.send_message(query.message.chat.id, text, reply_markup=markup, parse_mode='html')

    @button_target
    def back_billboard(self, query, i):
        try:
            films_group_data = memory_film_groups[from_callback_int(i)]
        except (KeyError, SessionExpired):
            self.bot.edit_message_text('¡Sesión caducada! Repita el comando, por favor.',
                                       query.message.chat.id, message_id=query.message.message_id)
            return
        markup = InlineKeyboard(self.main)
        self.billboard_markup(films_group_data['film_groups'], markup)
        message_id = get_hidden_data(query.message, 'message_id')  # Id del mensaje del poster
        if message_id:
            self.bot.delete_message(query.message.chat.id, int(message_id))  # Borrar poster
        self.bot.edit_message_text('Cartelera de hoy', query.message.chat.id, message_id=query.message.message_id,
                                   parse_mode='html', reply_markup=markup)

