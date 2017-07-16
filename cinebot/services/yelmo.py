import datetime
import json
import re

from bs4 import BeautifulSoup

from cinebot.services.base import ServiceBase, LocationBase, FilmBase, remove_words, FILM_OPTIONS

URL = 'http://www.yelmocines.es/'
AJAX_URL = '{}now-playing.aspx/GetNowPlaying'.format(URL)


class YelmoFilm(FilmBase):

    def get_cover(self):
        return self.film_options['Poster']

    def get_description(self):
        return self.film_options['Synopsis']

    def get_times_data(self):
        all_times = []
        for format_ in self.film_options['Formats']:
            options = self._get_options(format_)
            all_times.extend([dict(time=time['Time'], options=options)
                              for time in format_['Showtimes']])
        return all_times

    def _get_options(self, time):
        options = [FILM_OPTIONS.get(time['Language']), FILM_OPTIONS.get(time['Name'])]
        return [option for option in options if option]


class YelmoLocation(LocationBase):
    film_class = YelmoFilm

    def get_films_data(self, date):
        req = self.service.session.request('POST', AJAX_URL, json={'cityKey': self.id['city']})
        data = req.json()['d']
        cinema = [cinema for cinema in data['Cinemas'] if cinema['Key'] == self.id['cinema']][0]
        movies = self._get_movies_by_date(cinema, date)
        return [dict(movie, name=movie['Title'], film_options=movie) for movie in (movies or [])]

    def _get_movies_by_date(self, cinema, date):
        for cinemaDate in cinema['Dates']:
            d = int(re.findall('\((.+)\)', cinemaDate['FilterDate'])[0]) / 1000
            d = datetime.date.fromtimestamp(d)
            if date == d:
                return cinemaDate['Movies']


class YelmoService(ServiceBase):
    location_class = YelmoLocation
    name = 'yelmo'
    url = URL

    def get_locations_data(self):
        req = self.session.request('GET', URL)
        cities = json.loads(re.findall('var cities=([^;]+);', req.text)[0])
        cinemas = []
        for city in cities:
            for cinema in city['cinemas']:
                cinemas.append({'id': {'city': city['key'], 'cinema': cinema['key']}, 'name': cinema['name']})
        return cinemas
