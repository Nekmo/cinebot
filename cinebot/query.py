from cinebot.services.cinesur import CinesurService
from cinebot.services.yelmo import YelmoService

SERVICES = [
    CinesurService, YelmoService,
]


def get_service(name):
    for service in SERVICES:
        if service.name == name:
            return service
