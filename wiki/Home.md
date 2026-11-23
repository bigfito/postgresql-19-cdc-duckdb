# ElastiFlix: del dato de la operación al tablero, en minutos

Este laboratorio muestra, con un ejemplo que funciona de verdad, cómo un cambio hecho en el sistema del día a día de una empresa llega solo a un tablero de análisis en menos de 15 minutos, sin perder por el camino lo que el dato decía antes.

**ElastiFlix** es una empresa ficticia con un catálogo de 6,899 películas. Sus datos son inventados, pero el recorrido que hacen es el mismo que haría el catálogo de un negocio real.

![El laboratorio en una imagen: la operación, la captura de cambios, las capas Bronce, Plata y Oro, y los tableros](../lab-design/diagrams/wiki-vista-general.svg)

## Qué demuestra

- **El análisis no estorba a la operación.** Las consultas de negocio trabajan sobre una copia, no sobre el sistema donde se registra el trabajo diario.
- **El dato llega fresco y sin que nadie lo pida.** Cada cambio se copia en segundos, y los resultados se actualizan cada 10 minutos.
- **La historia no se pierde.** Si un dato cambia, el laboratorio guarda el valor anterior y la fecha del cambio.

## Para quién es este wiki

Para quien necesita entender qué hace el laboratorio y qué valor tiene, sin entrar en cómo está construido. No hay comandos ni código. Quien quiera el detalle técnico lo tiene en el [README del repositorio](../README.md) y en el [documento de diseño](../lab-design/LAB-DESIGN.md).

## Las páginas

| Página | Pregunta que responde |
|---|---|
| [El problema](El-problema.md) | ¿Por qué no basta con consultar la base de datos de la operación? |
| [El recorrido de un cambio](El-recorrido-de-un-cambio.md) | ¿Qué pasa desde que alguien cambia un dato hasta que aparece en un tablero? |
| [Bronce, plata y oro](Bronce-plata-y-oro.md) | ¿Por qué el dato pasa por tres etapas y qué gana en cada una? |
| [Qué preguntas responde](Qué-preguntas-responde.md) | ¿Qué se puede saber del catálogo con lo que el laboratorio prepara? |
| [La memoria del dato](La-memoria-del-dato.md) | ¿Cómo sabemos qué decía un dato antes y cuándo cambió? |
| [Frescura y confianza](Frescura-y-confianza.md) | ¿Qué tan al día está lo que veo y cómo sé que es correcto? |
| [Las piezas y por qué se eligieron](Las-piezas-y-por-qué-se-eligieron.md) | ¿Qué hace cada herramienta, en una línea, y por qué esa? |
| [Ver una demostración](Ver-una-demostración.md) | ¿Qué voy a ver en una demostración y en qué fijarme? |
| [Alcance y límites](Alcance-y-límites.md) | ¿Qué demuestra el laboratorio y qué no? |
| [Preguntas frecuentes](Preguntas-frecuentes.md) | Las dudas más habituales, en corto. |
| [Glosario](Glosario.md) | ¿Qué significa cada término? |

Las cinco primeras cuentan la historia completa y conviene leerlas en orden. Las demás se pueden consultar sueltas.

## El laboratorio en cifras

| Dato | Valor |
|---|---|
| Películas del catálogo | 6,899, todas inventadas |
| Tiempo para que un cambio se copie | Entre 11 y 50 segundos |
| Cada cuánto se actualizan los resultados | Cada 10 minutos |
| Tiempo máximo hasta verlo en un tablero | 15 minutos |
| Tablas de resultados listas para consultar | 7 |
| Qué hace falta para ponerlo en marcha | Un equipo con 16 GB de memoria y un solo comando |

Las cifras de tiempo son mediciones hechas en el laboratorio; su origen está en el [documento de diseño](../lab-design/LAB-DESIGN.md).
