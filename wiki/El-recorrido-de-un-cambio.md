# El recorrido de un cambio

**¿Qué pasa desde que alguien cambia un dato hasta que aparece en un tablero?**

La mejor forma de entender el laboratorio es seguir un solo cambio de principio a fin. Este es real: se siguió durante las pruebas del laboratorio.

![El recorrido de un cambio, de la operación al tablero, en seis pasos](../lab-design/diagrams/wiki-recorrido-de-un-cambio.svg)

## Un ejemplo real: una película cambia de título

A las 22:05:25, la película «Trial 6: Across the Untold Finale» pasó a llamarse «Trial 6: Across the Untold Finale: Extended Edition».

| Momento | Qué ocurrió |
|---|---|
| 22:05:25 | El cambio se registra en el sistema de la operación. |
| Segundos después | La copia fiel del almacén (Bronce) ya tiene el título nuevo. |
| 22:06:50 | Arranca la actualización programada, la que corre cada 10 minutos. |
| Durante esa actualización | El almacén ordenado (Plata) guarda el título nuevo como vigente y **conserva el anterior**, con la hora exacta en que dejó de valer. |
| Al terminar, unos 5 minutos después | Los resultados (Oro) y el tablero muestran el título nuevo. |

Nadie lanzó nada a mano en ningún paso.

## Lo que conviene retener

- **Dos velocidades.** La copia es inmediata: tarda segundos. Ordenar y resumir espera su turno, que llega cada 10 minutos.
- **Quince minutos como mucho.** En el peor caso el cambio espera casi 10 minutos a la siguiente actualización, que tarda unos 5.
- **El dato anterior sigue ahí.** El tablero muestra lo vigente, pero el almacén recuerda lo que había antes. Eso permite responder preguntas sobre el pasado.

## No solo cambios: también altas y bajas

Durante las pruebas se siguieron los tres tipos de movimiento, y los tres llegaron al tablero:

| Movimiento | Qué se vio en el tablero después |
|---|---|
| Una película nueva | Aparece, y el total de películas sube. |
| Un cambio en sus cifras | La popularidad de una película pasó de 83.513 a 76.012. |
| Una película eliminada | Desaparece del tablero, pero el almacén conserva que existió y cuándo se eliminó. |

Siguiente página: [Bronce, plata y oro](Bronce-plata-y-oro.md).
