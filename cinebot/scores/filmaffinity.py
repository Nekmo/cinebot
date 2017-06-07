from bs4 import BeautifulSoup
from requests import Session

URL = 'https://www.filmaffinity.com/'
AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'

def search(term):
    s = Session()
    s.headers.update({'referer': URL, 'User-Agent': AGENT})
    data = s.post(URL + 'es/search-ac.ajax.php?action=searchTerm', data={'term': term}).json()
    if not data.get('results'):
        return
    req = s.post(URL + 'es/film{}.html'.format(data['results'][0]['id']), data={'term': term})
    req.encoding = 'UTF-8'
    soup = BeautifulSoup(req.text, 'html.parser')
    info = dict(zip(soup.select('dl.movie-info > dt'), soup.select('dl.movie-info > dd')))
    info = {key.string.strip(): value.string.strip() for key, value in info.items() if key.string and value.string}
    return {
        'score': soup.select('#movie-rat-avg')[0].attrs['content'],
        'original_title': info.get('Título original'),
        'info': info,
    }
