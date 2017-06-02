

def group_cine_cines(cine_films, other_cines_films):
    # Listado de todas las películas iguales en este cine respecto a otros cines
    same_films = []
    for cine_film in cine_films:
        # Por cada película de este cine, comparo con las de otros cines
        same_film = [cine_film]
        same_films.append(same_film)
        for other_cine_films in other_cines_films:
            # Por cada cine, comparo con sus películas
            for other_film in other_cine_films:
                if cine_film.is_almost_equal(other_film):
                    # Como es la misma película, la añado a la lista de películas que son
                    # iguales a esta, la borro del listado del propio cine, porque ya
                    # no se debe buscar, y paro de buscar en este cine.
                    same_film.append(other_film)
                    other_cine_films.remove(other_film)
                    break
    # Como ya he comparado lo de este cine con otros y lo he añadido a same_films,
    # elimino sus películas
    cine_films.clear()
    return same_films


class Multicine(object):
    """Permite obtener la cartelera de múltiples cines, de forma conjunta y con
    las películas sin repetir.
    """

    def __init__(self, cinemas):
        self.cinemas = cinemas

    def all_cines_films(self, date):
        """Obtiene listado de las películas por cada cine
        """
        cine_films = {}
        for cinema in self.cinemas:
            cine_films[cinema] = cinema.films(date)
        return list(cine_films.values())

    def grouped_films(self, date=None):
        cine_films = self.all_cines_films(date)
        grouped_films = []
        for i, films in enumerate(cine_films):
            grouped_films.extend(group_cine_cines(films, cine_films[i+1:]))
        return grouped_films
