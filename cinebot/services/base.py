import datetime
import re
from collections import defaultdict

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from requests import Session


FILM_OPTIONS = {
    '3D': '3D',
    'UHD': '4K',
    'VOSE': 'SUB',
}
MIN_FUZZY_RATIO = 90

def remove_words(text, words):
    pattern = re.compile("(" + '|'.join([re.escape(word) for word in words]) + ")", re.I)
    return pattern.sub("", text)


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

    def __init__(self, location, date, name, film_options=None):
        self.location = location
        self.date = date
        self.name = name
        self.film_options = film_options

    def get_cover(self):
        raise NotImplementedError

    def get_times(self):
        times = [self.film_time_class(self, self.date, time['time'], time.get('options'), time.get('booking'))
                for time in self.get_times_data()]
        return TimesList(times)

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

    def get_films(self, date=None):
        if date is None and datetime.datetime.now().time() < datetime.time(1, 30):
            # Consideramos que es el mismo día hasta las 01:30 de la mañana
            date = datetime.date.today() - datetime.timedelta(1)
        date = date or datetime.date.today()
        billboard_data = self.get_films_data(date)
        return [self.film_class(self, date, data['name'], data.get('film_options', [])) for data in billboard_data]

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

    def __init__(self):
        self.session = self.get_session()
        self.locations = self.get_locations()

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

    def get_locations(self):
        return [self.location_class(self, data['id'], data['name']) for data in self.get_locations_data()]

    def get_locations_data(self):
        raise NotImplementedError
