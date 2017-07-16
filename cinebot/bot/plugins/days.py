import datetime
import tempfile
import time

import os

import traceback

import sys

import math
from typing import Union

from PIL import Image
from telebot.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from cinebot.bot.multicine import Multicine
from cinebot.bot.plugins.cinemas import search_cinema
from cinebot.query import get_service
from cinebot.scores import filmaffinity, imdb
from cinebot.services.cinesur import CinesurService
from cinebot.services.yelmo import YelmoService
from telegram_bot.plugins.base import PluginBase, button_target
from telegram_bot.types.keyboard import InlineKeyboard
from telegram_bot.types.message import Message
from telegram_bot.utils.telegram import escape_items, username_id_code
from expiringdict import ExpiringDict

# La url debe ser válida para colocarla como una url oculta en el mensaje
HIDDEN_URL = 'http://example.com'

i_memory = 0
memory_film_groups = ExpiringDict(max_len=300, max_age_seconds=60 * 60 * 24)
uptime_time = time.time()
DEFAULT_WIDTH = 139
DEFAULT_HEIGHT = 203
DAYS = [
    ('today', 'Hoy'), ('tomorrow', 'Mañana'), ('next2days', 'Pasado mañana'),
    ('next3days', 'Dentro de 3 días')
]

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


class BillboardBase(PluginBase):
    db = None

    @property
    def user_cinemas(self):
        return self.db['user_cinemas']

    @property
    def search_cinemas(self):
        return self.db['search_cinemas']

    @property
    def locations(self):
        return self.db['locations']


class DaysPlugin(BillboardBase):

    def set_handlers(self):
        self.main.set_message_handler(self.today, commands=['today'])
        self.main.set_message_handler(self.tomorrow, commands=['tomorrow'])
        self.main.set_message_handler(self.next2days, commands=['next2days'])
        self.main.set_message_handler(self.next3days, commands=['next3days'])

    # def today(self, message):
    #     from cinebot.services.cinesur import CinesurService
    #     films = CinesurService().find_by_name('Miramar').get_films()
    #     body = []
    #     for film in films:
    #         body.append('<b>{name}</b>: {times}'.format(**escape_items(
    #             name=film.name, times=', '.join([str(time) for time in film.get_times()])
    #         )))
    #     message.response('\n'.join(body), parse_mode='html').send()

    def today(self, message, films_groups=None):
        self._billboard_day(message, None, films_groups)

    def _next_days(self, message, days, films_groups=None):
        day = datetime.date.today() + datetime.timedelta(days=days)
        self._billboard_day(message, day, films_groups)

    def tomorrow(self, message, films_groups=None):
        self._next_days(message, 1, films_groups)

    def next2days(self, message, films_groups=None):
        self._next_days(message, 2, films_groups)

    def next3days(self, message, films_groups=None):
        self._next_days(message, 3, films_groups)

    def get_user_cinemas(self, chat_id):
        return [
            get_service(cinema['service'])(self.db).find_by_name(cinema['name'])
            for cinema in [self.locations.find_one({'_id': user_cinema['cinema_id']})
                           for user_cinema in self.user_cinemas.find({'user_id': chat_id})]
            if cinema
        ]

    def _billboard_day(self, message, day: Union[datetime.date, None], films_groups=None):
        day = day or datetime.date.today()
        human_day = {0: 'hoy', 1: 'mañana', 2: 'pasado mañana', 3: 'dentro de 3 días'}.get(
            (day - datetime.date.today()).days, '?'
        )
        cinemas = self.get_user_cinemas(message.chat.id)
        if films_groups is None:
            films_groups = Multicine(cinemas).grouped_films(day)
        if not cinemas:
            return message.response('No tienes cines añadidos. Añada cines con /cinemas').send()
        if not films_groups:
            return message.response('No hay cartelera. Comprueba los cines que tiene en favoritos con /cinemas').send()
        img_msg = self.send_collage(films_groups, message)
        msg = message.response('Cartelera de {}, día {}, en los cines {} {}'.format(
            human_day, day.strftime('%x'), ', '.join([cinema.name for cinema in cinemas]),
            set_hidden_data('message_id', img_msg.message_id)
        ), parse_mode='html')
        inline = msg.inline_keyboard()
        self.billboard_markup(films_groups, inline)
        msg.send()

    def get_collage(self, film_groups):
        columns = math.ceil(len(film_groups) ** (1 / 2))
        rows = round(len(film_groups) ** (1 / 2) + 0.00001)  # No redondea 0.5 a 1. Por eso añado 0.00001
        ims = Image.new('RGB', (DEFAULT_WIDTH * columns, DEFAULT_HEIGHT * rows), '#ffffff')
        for i, film_group in enumerate(film_groups):
            film = film_group[0]
            image = film.get_image()
            if image is None:
                continue
            im = Image.open(image)
            im.thumbnail((DEFAULT_WIDTH, DEFAULT_HEIGHT))
            ims.paste(im, ((i % columns) * DEFAULT_WIDTH, (i // columns) * DEFAULT_HEIGHT))
        name = tempfile.NamedTemporaryFile().name
        ims.save(name, "JPEG")
        return name

    def send_collage(self, film_groups, message):
        # TODO: debería en el futuro intentar cachearlo X tiempo
        image = self.get_collage(film_groups)
        msg = self.bot.send_photo(message.chat.id, open(image, 'rb'))
        os.remove(image)
        return msg

    def billboard_markup(self, films_groups, inline, **extra_data):
        for film_group in films_groups:
            i = save_film_to_memory(dict({'film_group': film_group, 'film_groups': films_groups}, **extra_data))
            inline.add_button(film_group[0].name, callback=self.film_times,
                              callback_kwargs={'i': to_callback_int(i)})

    def get_scores(self, film_name):
        data = {}
        try:
            data = filmaffinity.search(film_name) or {}
        except Exception:
            traceback.print_exc(file=sys.stdout)
        scores = [('Filmaffinity', data.get('score'))]
        if 'original_title' in data:
            ib = {}
            try:
                ib = imdb.search(data['original_title']) or {}
            except Exception:
                pass
            scores += [('IMDb', ib.get('score'))]
        return '\n'.join(['{}: {}'.format(key, value) for key, value in scores if value])

    @button_target
    def film_times(self, query, i):
        try:
            films_group_data = memory_film_groups[from_callback_int(i)]
        except (KeyError, SessionExpired):
            self.bot.send_message(query.message.chat.id, '¡Sesión caducada! Repita el comando, por favor.')
            return
        film_group = films_group_data['film_group']
        film = film_group[0]
        text = '<b>{name}</b>\nSesión del día: {date}\n{scores}\n{description}\n\n'.format(**escape_items(
            name=film.name, date=str(film.date), scores=self.get_scores(film.name),
            description=film.get_description()))
        for film in film_group:
            text += '<b>{f}</b>\n{t}\n'.format(**escape_items(f=film.location.name,
                                                              t=' '.join(map(str, film.get_times()))))
        markup = InlineKeyboard(self.main)
        markup.add_button('Volver atrás', callback=self.back_billboard, callback_kwargs={'i': i})
        # Borrar mensaje con los botones
        self.bot.delete_message(query.message.chat.id, query.message.message_id)
        # Borrar el poster con el collage
        message_id = get_hidden_data(query.message, 'message_id')  # Id del mensaje del poster
        if message_id:
            self.bot.delete_message(query.message.chat.id, int(message_id))  # Borrar poster
        # Enviar poster de la película solicitada
        image = film.get_image()
        if image is not None:
            msg = self.bot.send_photo(query.message.chat.id, open(image, 'rb'))
            # Establecer oculto id del poster
            text += set_hidden_data('message_id', msg.message_id)
        self.bot.send_message(query.message.chat.id, text, reply_markup=markup, parse_mode='html')

    @button_target
    def back_billboard(self, query, i):
        try:
            film_groups = memory_film_groups[from_callback_int(i)]['film_groups']
        except (KeyError, SessionExpired):
            self.bot.edit_message_text('¡Sesión caducada! Repita el comando, por favor.',
                                       query.message.chat.id, message_id=query.message.message_id)
            return
        message_id = get_hidden_data(query.message, 'message_id')  # Id del mensaje del poster
        if message_id:
            self.bot.delete_message(query.message.chat.id, int(message_id))  # Borrar poster
        self.bot.delete_message(query.message.chat.id, query.message.message_id)
        self.today(Message.from_telebot_message(self.main, query.message), film_groups)


class SearchPlugin(BillboardBase):
    def set_handlers(self):
        self.main.set_message_handler(self.search, commands=['search'])

    @property
    def locations(self):
        return self.db['locations']

    def search(self, message):
        user_cinemas = self.search_cinemas.find({'user_id': message.chat.id})
        if not user_cinemas.count():
            self.search_by_name(message)
        msg = message.response('Antes de buscar, aquí tienes los últimos cines que consultaste.')
        markup = msg.inline_keyboard()
        markup.add_button('* Iniciar búsqueda *', callback=self.search_by_name_selected)
        for i, user_cinema in enumerate(user_cinemas):
            cinema = self.locations.find_one({'_id': user_cinema['cinema_id']})
            markup.add_button(cinema['name'], callback=self.cinema_selected, callback_kwargs={'c': i})
        msg.send()
        # TODO:

    @button_target
    def cinema_selected(self, query, c):
        pass

    def search_by_name(self, message):
        msg = message.response('Escribe el nombre del cine del que obtener su cartelera')
        msg.force_reply(self.search_results)
        msg.send()

    @button_target
    def search_by_name_selected(self, query):
        self.search_by_name(Message.from_telebot_message(self.main, query.message))

    def search_results(self, message):
        msg = message.response('Estos son los resultados que se han encontrado')
        markup = msg.reply_keyboard(self.result_selected)
        for result in search_cinema(self.locations, message.text):
            markup.add_button(result[0])
        msg.send()

    def result_selected(self, message):
        cinema = self.locations.find_one({'name': message.text})
        if not cinema:
            message.response('No se ha encontrado ningún resultado. Vuelva a intentarlo.').send()
            self.search_results(message)
            return
        # TODO: incluir fecha última consulta
        q = {'user_id': message.chat.id, 'cinema_id': cinema['_id']}
        if not self.search_cinemas.find(q).count():
            self.search_cinemas.insert_one(q)
        self.cinema_billboard(message, cinema)

    def cinema_billboard(self, message, cinema):
        markup = ReplyKeyboardRemove(selective=False)
        films = get_service(cinema['service'])(self.db).find_by_name(cinema['name']).get_films()
        film_lines = []
        for film in films:
            film_lines.append('<b>{name}</b>\n{times}'.format(**escape_items(
                name=film.name, times=', '.join([str(time) for time in film.get_times()])
            )))
        message.response('\n'.join(film_lines), parse_mode='html', reply_markup=markup).send()
        body = 'Estos horarios son del día {} para el cine {}. Cambia de día usando los botones.'
        body += set_hidden_data('cinema_name', cinema['name'])
        # TODO: incluir como info oculta el cine y los mensajes a eliminar
        msg = message.response(body, reply_markup=markup)
        inline = msg.inline_keyboard(2)
        for day_key, name in DAYS:
            inline.add_button(name, callback=self.cinema_billboard_day, callback_kwargs={'d': day_key})
        msg.send()

    @button_target
    def cinema_billboard_day(self, query, d):
        pass