import datetime
import re
from collections import defaultdict

import tempfile

import os
from urllib.parse import quote

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from requests import Session


FILM_OPTIONS = {
    '3D': '3D',
    'UHD': '4K',
    'VOSE': 'SUB',
}
MIN_FUZZY_RATIO = 90
TEMP_DIR = tempfile.tempdir or '/tmp'


def remove_words(text, words):
    pattern = re.compile("(" + '|'.join([re.escape(word) for word in words]) + ")", re.I)
    return pattern.sub("", text)


def get_date(date):
    if date is None and datetime.datetime.now().time() < datetime.time(1, 30):
        # Consideramos que es el mismo día hasta las 01:30 de la mañana
        date = datetime.date.today() - datetime.timedelta(1)
    return date or datetime.date.today()


def file_makedirs(path):
    """Crear directorios intermedios hasta el archivo, pero sin crear el archivo.
    """
    os.makedirs(os.path.split(path)[0], exist_ok=True)


def download_file(req, local_filename=None):
    local_filename = local_filename or tempfile.NamedTemporaryFile().name
    file_makedirs(local_filename)
    with open(local_filename, 'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                #f.flush() commented by recommendation from J.F.Sebastian
    return local_filename


class TimesList(list):
    def __init__(self, times):
        times = sorted(times, key=lambda x: x.time)
        super(TimesList, self).__init__(times)


class FilmTimeBase(object):
    def __init__(self, film, date, time, options=None, booking=None):
        if isinstance(time, str):
            time = datetime.datetime.strptime(time, '%H:%M').time()
        self.film = film
        self.date = date
        self.time = time
        self.options = options
        self.booking = booking

    def __str__(self):
        text = self.time.strftime('%H:%M')
        if self.options:
            text += ' ({})'.format(', '.join(self.options))
        return text

    def __repr__(self):
        return '<Time {}>'.format(self)


class FilmBase(object):
    film_time_class = FilmTimeBase

    def __init__(self, location, date, name, film_options=None, _id=None):
        self.location = location
        self.date = date
        self.name = name
        self.film_options = film_options
        self._id = _id  # db id

    def get_image(self):
        name = '{}/cinebot/{}/{}'.format(TEMP_DIR, self.location.service.name, quote(self.name, ' '))
        if os.path.lexists(name):
            return name
        cover = self.get_cover()
        if cover is None:
            return
        req = self.location.service.session.get(cover, stream=True, headers={'referer': self.location.service.url})
        return download_file(req, name)

    def get_cover(self):
        raise NotImplementedError

    def get_times(self):
        times = [self.film_time_class(self, self.date, time['time'], time.get('options'), time.get('booking'))
                for time in self.get_times_data()]
        return TimesList(times)

    def get_description(self):
        return ''

    def get_times_data(self):
        raise NotImplementedError

    def is_almost_equal(self, other):
        name1 = self.name.lower()
        name2 = other.name.lower()
        return fuzz.ratio(name1, name2) >= MIN_FUZZY_RATIO

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Film {}>'.format(self)


class LocationBase(object):
    film_class = FilmBase

    def __init__(self, service: 'ServiceBase', location_id, name: str):
        self.service = service
        self.id = location_id
        self.name = name

    # def films(self, date):
    #     date = get_date(date)
    #     def create_films():
    #         return self.update_films(self.get_films_data(date), date)
    #     return self.get_films(date, self.service.db_get_or_create('films', create_films, dict(
    #         service=self.service.name, location=self.id, date=date.isoformat()
    #     )))

    def films(self, date):
        return self.get_films(date)

    def get_films(self, date=None, data=None):
        date = get_date(date)
        billboard_data = data or self.get_films_data(date)
        return [self.film_class(self, date, bdata['name'], bdata.get('film_options', []), bdata.get('_id'))
                for bdata in billboard_data]

    def update_films(self, films, date):
        # TODO: ¿Hacer mejor método que devuelva el diccionario preparado para la db?
        return [dict(film, service=self.service.name, location=self.id, date=date.isoformat()) for film in films]

    def get_films_data(self, date):
        raise NotImplementedError

    def join_films_options(self, data):
        """Muchos cines tienen sus películas separadas según sus opciones (VOSE, UHD, 3D...).
        Esta función se encarga de unir dichas películas.
        :param data:  
        :return: 
        """
        films = defaultdict(list)
        for film in data:
            film = self.set_film_options(film)
            films[film['name']].append(film)
        return [{'name': name, 'film_options': options} for name, options in films.items()]

    def set_film_options(self, film):
        film = dict(film)
        name = remove_words(film['name'], [' - '])
        options = []
        for option in FILM_OPTIONS:
            if option in name:
                options.append(option)
                name = name.replace(option, '')
        name = re.sub(' +', ' ', name)
        film['options'] = options
        film['name'] = name.strip()
        return film

    def match_name(self, other_name: str):
        return other_name.lower() in self.name.lower()

    def __str__(self):
        return '{} ({})'.format(self.name, self.id)

    def __repr__(self):
        return '<Location {}>'.format(self)


class ServiceBase(object):
    location_class = LocationBase
    name = None
    url = None

    def __init__(self, db=None):
        self.session = self.get_session()
        self.db = db

    def get_session(self):
        return Session()

    def find_by_name(self, name):
        for location in self.locations:
            if location.match_name(name):
                return location

    def soup_req(self, url, method='GET', params=None, data=None, session=None):
        session = session or self.session
        req = session.request(method, url, params, data)
        return req, BeautifulSoup(req.text, 'html.parser')

    def db_find(self, collection, query=None):
        if not self.db:
            return ()
        return self.db[collection].find(query or {})

    def db_save_many(self, collection, datas):
        if not self.db:
            return
        self.db[collection].insert_many(datas)

    def db_get_or_create(self, collection, creator, query=None):
        data = list(self.db_find(collection, query or {}))
        if not data:
            data = creator()
            self.db_save_many(collection, data)
        return data

    @property
    def locations(self):
        return self.get_locations(self.db_get_or_create('locations',
                                                        lambda: self.update_locations( self.get_locations_data()),
                                                        {'service': self.name}))

    def get_locations(self, locations_data=None):
        return [self.location_class(self, data['id'], data['name'])
                for data in locations_data or self.get_locations_data()]

    def update_locations(self, locations):
        return [dict(location, service=self.name) for location in locations]

    def get_locations_data(self):
        raise NotImplementedError
