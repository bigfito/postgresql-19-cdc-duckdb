# Alcance y límites

**¿Qué demuestra el laboratorio y qué no?**

El laboratorio es una demostración, no un producto listo para usar en una empresa. Sirve para entender un mecanismo y para ver que funciona. Esta página dice hasta dónde llega, para que nadie saque de él una conclusión que no sostiene.

![Qué demuestra el laboratorio y qué no: cuatro cosas comprobadas y cuatro fuera de su alcance](../lab-design/diagrams/wiki-alcance-y-limites.svg)

## Lo que sí demuestra

| Afirmación | Cómo se comprobó |
|---|---|
| **El recorrido completo funciona.** | Se siguieron una alta, un cambio y una baja desde la operación hasta un gráfico. |
| **El dato llega fresco.** | La copia tarda entre 11 y 50 segundos, y el tablero se pone al día en 15 minutos como mucho. |
| **La historia se conserva.** | Tras un cambio de título, el almacén guardó la versión anterior con la hora exacta en que dejó de valer. |
| **Se repite igual.** | Se borró todo y se volvió a levantar desde cero con una sola orden, también desde una copia nueva del proyecto. |
| **Aguanta una parada.** | Se detuvo y se volvió a encender en plena actividad, también en mitad de una actualización, y no quedó nada a medias ni duplicado. |

## Lo que no demuestra

| Límite | Qué significa |
|---|---|
| **Los datos no son reales.** | Las películas, las personas y las cifras son inventadas. No se puede concluir nada sobre cine. |
| **El volumen es pequeño.** | Son 6,899 películas y unas 440,000 filas en total. No se probó con millones. |
| **Corre en un solo equipo.** | Si ese equipo falla, todo se detiene. No hay equipos de respaldo ni reparto de carga. |
| **No vuelve a arrancar solo.** | Tras una caída o un reinicio hay que ponerlo en marcha con una orden. |
| **La seguridad es de laboratorio.** | Usa claves de ejemplo y solo es accesible desde el propio equipo. No hay usuarios con permisos distintos. |
| **No avisa de los fallos.** | Un fallo queda registrado, pero no se envía ningún aviso. |
| **No trae tableros hechos.** | Entrega las tablas de resultados; los gráficos los arma quien lo usa. |
| **Solo se probó en dos tipos de equipo.** | Se construyó en un equipo con Windows y se comprobó también en otro con Linux. En equipos Mac y en procesadores ARM debería funcionar, pero no se verificó. |

## Qué haría falta para un uso real

El mecanismo es el mismo que usaría una empresa. Lo que cambia es todo lo que lo rodea:

- Repartir las piezas en varios equipos, con respaldo si uno falla.
- Usuarios, permisos y claves de verdad.
- Avisos cuando algo falla y alguien que los atienda.
- Copias de seguridad del almacén.
- Pruebas con el volumen real de datos.

Nada de eso es exótico, pero es trabajo que el laboratorio no hace ni pretende hacer.

Siguiente página: [Preguntas frecuentes](Preguntas-frecuentes.md).
