from fuzzywuzzy import process
from telebot.types import ReplyKeyboardRemove

from telegram_bot.types.message import Message
from cinebot.query import SERVICES
from telegram_bot.plugins.base import PluginBase, button_target


class CinemasPlugin(PluginBase):

    @property
    def user_cinemas(self):
        return self.db['user_cinemas']

    @property
    def locations(self):
        return self.db['user_cinemas']

    def set_handlers(self):
        self.main.set_message_handler(self.cinemas, commands=['cinemas'])

    def options(self, message):
        msg = message.response('Seleccione la opción deseada')
        inline = msg.inline_keyboard()
        inline.add_button('Añadir cines', callback=self.add_cinema)

    def add_cinema(self, message):

        msg = message.response('Escriba el nombre del cine. Los cines soportados son {}'.format(
            ', '.join([service.name for service in SERVICES])
        ))
        msg.force_reply(self.search, True)
        msg.send()

    def search(self, message):
        msg = message.response('Éstas son las opciones disponibles. Elija el que crea correcta.')
        all_cinemas = self.db['locations'].find({})
        results = process.extract(message.text, [cinema['name'] for cinema in all_cinemas], limit=4)
        markup = msg.reply_keyboard(self.add_cinema_selected)
        for result in results:
            markup.add_button(result[0])
        msg.send()

    def cinema_query(self, message, on_error):
        cinema = self.db['locations'].find_one({'name': message.text})
        if not cinema:
            message.response('No se ha encontrado ningún resultado. Vuelva a intentarlo.')
            on_error(message)
            return
        return {
            'cinema_id': cinema['_id'],
            'user_id': message.chat.id,
        }

    def add_cinema_selected(self, message):
        query = self.cinema_query(message, self.add_cinema)
        markup = ReplyKeyboardRemove(selective=False)
        if self.user_cinemas.find(query).count():
            body = 'Este cine ya se encontraba en sus favoritos, así que no se ha vuelto a añadir.'
        else:
            self.user_cinemas.insert_one(query)
            body = 'Se ha añadido este cine a sus favoritos.'
        message.response(body, reply_markup=markup).send()
        msg = message.response('Ahora tienes la posibilidad de añadir otro cine si lo deseas.')
        inline = msg.inline_keyboard()
        inline.add_button('Añadir otro cine', callback=self.add_cinema_button)
        msg.send()

    def delete_cinema(self, message):
        msg = message.response('Elije los cines que desees borrar de tus favoritos.')
        inline = msg.inline_keyboard()
        for user_cinema in self.user_cinemas.find({'user_id': message.chat.id}):
            cinema = self.db['locations'].find_one({'_id': user_cinema['cinema_id']})
            inline.add_button(cinema['name'], callback=self.delete_cinema_selected)
        msg.send()

    def delete_cinema_selected(self, message):
        query = self.cinema_query(message, self.add_cinema)
        markup = ReplyKeyboardRemove(selective=False)
        self.user_cinemas.insert_one(query)
        message.response('Eliminado el cine seleccionado de tus favoritos.', reply_markup=markup).send()
        msg = message.response('Ahora tienes la posibilidad de eliminar otro cine si lo deseas.')
        inline = msg.inline_keyboard()
        inline.add_button('Borrar otro cine', callback=self.delete_cinema_button)
        msg.send()

    @button_target
    def add_cinema_button(self, query):
        self.bot.delete_message(query.message.chat.id, query.message.message_id)
        self.add_cinema(Message.from_telebot_message(self.main, query.message))

    @button_target
    def delete_cinema_button(self, query):
        self.bot.delete_message(query.message.chat.id, query.message.message_id)
        self.delete_cinema(Message.from_telebot_message(self.main, query.message))

    def cinemas(self, message):
        my_cinemas = self.user_cinemas.find({'user_id': message.chat.id})
        if not my_cinemas.count():
            message.response('No tienes tienes ningún cine como favorito. Por favor, introduzca uno.')
            self.add_cinema(message)
            return
        msg = message.response('Tienes los siguientes cines como favoritos:\n{}'.format(
            '\n'.join(['• {}'.format(self.db['locations'].find_one({'_id': cinema['cinema_id']})['name'])
                       for cinema in my_cinemas])
        ))
        inline = msg.inline_keyboard()
        inline.add_button('Añadir cines', callback=self.add_cinema_button)
        # TODO: este botón no está funcionando. Tal vez fallo bibilioteca. Sólo mete primero?
        inline.add_button('Borrar cines', callback=self.delete_cinema_button)
        msg.send()
