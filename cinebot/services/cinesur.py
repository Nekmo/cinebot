import datetime
import re

from bs4 import BeautifulSoup

from cinebot.services.base import ServiceBase, LocationBase, FilmBase, remove_words

URL = 'https://www.cinesur.com/'
URL_LIST = '{}listado.php'.format(URL)
AJAX_COVERS = '{}cargador_ajax/peliculas2.php'.format(URL)

class CinesurFilm(FilmBase):

    def get_cover(self):
        film_option = {}
        for film_option in self.film_options:
            if not film_option['options']:
                # Es la versión sin modificaciones. Nos quedamos con esta.
                break
        # Nota: la imagen no puede descargarse si no tiene el referer.
        return film_option.get('cover')

    def get_description(self):
        url = self.film_options[0]['sheet_url']
        req, soup = self.location.service.soup_req(url)
        return soup.select('.sinopsis')[0].string

    def get_times_data(self):
        all_times = []
        for film_option in self.film_options:
            times = film_option['data'].select('.sin_estilo')
            all_times.extend([dict(booking=time.attrs['href'], time=time.string, options=film_option['options'])
                              for time in times])
        return all_times


class CinesurLocation(LocationBase):
    film_class = CinesurFilm

    def get_films_data(self, date):
        req = self.service.session.request('GET', URL_LIST, params=dict(
            id_cine=self.id, fecha_alta=date.strftime('%d/%m/%Y'), idp='',
        ))
        # Debo arreglar el html antes de pasárselo a BeautifulSoup porque es inválido
        text = remove_words(req.text, ['<p >', '<p>', '</p>', '</form>', '</option>'])
        text = re.sub('<(?:form|option)([^>]*)>', '', text)
        soup = BeautifulSoup(text, 'html.parser')
        films = soup.select('div.claro, div.oscuro')
        films = [dict(name=data.find('a', 'titulo_peli'), data=data) for data in films]
        films = [dict(film, name=film['name'].string, sheet_url=URL + film['name'].attrs['href'])
                 for film in films if film['name']]
        covers = self.covers_ajax(date)
        films = [dict(film, cover=covers.get(film['sheet_url'])) for film in films]
        films = self.join_films_options(films)
        return films

    def update_films(self, films, date):
        films = super(CinesurLocation, self).update_films(films, date)
        for film in films:
            # No se puede guardar en la db. Es un Node Tag Soup
            for option in film['film_options']:
                del option['data']
        return films

    def covers_ajax(self, date):
        """La página de las portadas se carga por Ajax, y encima tiene dependencia por
        Cookies. Por ello, creo una nueva sesión vacía y repito la petición. Tras ello,
        cargo la primera página, e itero entre las páginas. No sé el número de páginas,
        así que me limito a seguir mientras el botón "siguiente" esté habilitado. Para
        relacionar la imagen con la película, utilizo su enlace, que es el mismo.
        """
        session = self.service.get_session()
        session.get(URL_LIST,params=dict(
            id_cine=self.id, fecha_alta=date.strftime('%d/%m/%Y'), idp='',
        ))
        params = {'id_cine': self.id}
        covers = {}
        for i in range(1, 10):  # 10: máximo de páginas para evitar bucle
            req, soup = self.service.soup_req(AJAX_COVERS, params=params, session=session)
            page_covers = [a for a in soup.select('.peli a') if not a.attrs.get('class')]
            covers.update({URL + a.attrs['href']: URL + a.find('img').attrs['src'].replace('prev_', '')
                           for a in page_covers})
            if not soup.select('a.siguiente') or not soup.select('a.siguiente')[0].attrs.get('href'):
                # Última página
                break
            params = {'pagina': i + 1}
        return covers


class CinesurService(ServiceBase):
    location_class = CinesurLocation
    name = 'cinesur'
    url = URL

    def get_locations_data(self):
        req, soup = self.soup_req(URL)
        return [dict(id=a.attrs['href'].split('=')[1], name=a.string[2:]) for a in soup.select('.ciu a')]
