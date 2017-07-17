================================  ================================  ================================
.. image:: https://goo.gl/KD3rVN  .. image:: https://goo.gl/N4JM92  .. image:: https://goo.gl/vQAz9h
.. image:: https://goo.gl/uSY5oi  .. image:: https://goo.gl/kD2mp9  .. image:: https://goo.gl/Nqd83Y
================================  ================================  ================================

CineBot
#######
CineBot es un bot para **Telegram** que te permite obtener la cartelera de tus cines favoritos de forma unificada y
fácil. Con un solo comando verás en una **imagen toda la cartelera** del día para todos tus cines, y pulsando sobre una
película, su nota en **Filmaffinity**, **IMDB**, **Rotten Tomatoes**, su **descripción**, y sus **horarios**.

Para gestionar tus cines favoritos, ejecuta el comando ``/cinemas``. Tras ello podrás ejecutar los comandos ``/today``
*(cartelera de hoy)*, ``/tomorrow`` *(mañana)*, ``/next2days`` *(pasado mañana)* y ``/next3days`` *(dentro de 3 días)*.
Se intentará unificar las películas de todos tus cines según su nombre.

Si deseas ver la cartelera de un cine sin necesidad de añadirlo a tus favoritos, usa el comando ``/search``. Además,
se mostrará el historial de los últimos cines buscados.

Aunque puedes montar tu propia versión de CineBot, hay una versión oficial para probar: ``@horascinebot``.


Comandos
========

==============  ===========================================================
Comando         Descripción
--------------  -----------------------------------------------------------
``/cinemas``    Añadir o borrar tus cines favoritos
``/today``      Ver la cartelera de hoy de tus cines favoritos
``/tomorrow``   Ver la cartelera de mañana de tus cines favoritos
``/next2days``  Ver la cartelera de pasado mañana de tus cines favoritos
``/next3days``  Ver la cartelera de dentro de 3 días de tus cines favoritos
``/search``     Buscar un cine y ver su cartelera
``/help``       Mostrar la ayuda sobre el uso de este bot
``/about``      Acerca de este bot y su desarrollador
==============  ===========================================================

Con la primera ejecución del bot, se te pedirá añadir cines favoritos. Puedes gestionarlos más adelante con
``/cinemas``. Cuando un cine está en favoritos, puedes usar los comandos ``/today``, ``/tomorrow``, ``/next2days``
y ``/next3days`` para ver su cartelera de forma rápida. Si añades varios cines favoritos, su cartelera se unificará.
En futuras versiones además, periódicamente recibirás un informe de los cambios en cartelera de los cines definidos
como favoritos.

El comando ``/search`` te permite buscar un cine sin añadirlo a favoritos, y ver su cartelera. Además, podrás ver
el histórico de los últimos cines de los que viste cartelera por este método, sin necesidad de volver a escribir
su nombre.

Cines soportados
================
En estos momentos este bot sólo está orientado al mercado español, con soporte para los cines:

- Yelmo
- Cinesur

Este proyecto está abierto a PR para recibir soporte a nuevos cines. También se busca en un futuro añadir soporte
internacional para incluir cines de otros países, además de la traducción del propio bot, que a día de hoy sólo
se encuentra en español.
