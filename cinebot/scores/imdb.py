import json
import re

import requests
from bs4 import BeautifulSoup

URL = 'http://m.imdb.com/title/{id}/'
SUGGESTS_URL = 'https://v2.sg.media-imdb.com/suggests/'

def search(title):
    title = title.lower().replace(' ', '_')
    title = re.sub('([^a-z0-9_])', '', title)
    data = requests.get(SUGGESTS_URL +  '{}/{}.json'.format(title[0], title)).text
    data = json.loads(data.split('(', 1)[1][:-1])
    if not data.get('d'):
        return
    imdb_id = data['d'][0]['id']
    req = requests.get(URL.format(id=imdb_id))
    soup = BeautifulSoup(req.text, 'html.parser')
    return {
        'score': list(soup.select('#ratings-bar span.inline-block')[0].stripped_strings)[0]
    }
