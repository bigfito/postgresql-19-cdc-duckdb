# El problema

**¿Por qué no basta con consultar la base de datos de la operación?**

Toda empresa tiene un sistema donde registra su trabajo diario: ventas, pedidos, clientes o, en el caso de ElastiFlix, su catálogo de películas. Ese sistema está pensado para **registrar** bien y rápido. No está pensado para **responder preguntas** de negocio, y cuando se le pide las dos cosas aparecen tres problemas.

![Dos formas de responder una pregunta de negocio: preguntarle a la base de la operación o tener una copia pensada para el análisis](../lab-design/diagrams/wiki-el-problema.svg)

## Tres problemas de preguntarle a la operación

| Problema | Qué significa en la práctica |
|---|---|
| **Solo sabe cómo están las cosas hoy** | Si una película cambia de título o de recaudación, el valor anterior se sobrescribe. No se puede responder «¿qué decía este dato el mes pasado?». |
| **El análisis frena el trabajo** | Un informe pesado compite con quien está registrando. Cuanto más se analiza, más lenta va la operación. |
| **El dato está partido en piezas** | La información de una película vive repartida en 20 tablas. Sirve para registrar sin errores, pero cada pregunta obliga a recomponerla. |

## Lo que propone el laboratorio

Mantener **dos lugares distintos**, cada uno con su trabajo:

- **La operación** sigue igual. Nadie le pide informes y no se entera de que existe lo demás.
- **Un almacén para el análisis** recibe una copia de cada cambio, la ordena, le pone memoria y deja preparadas las respuestas.

Lo difícil de esta idea siempre ha sido mantener la copia al día. Si se copia una vez por noche, el negocio decide con datos de ayer. El laboratorio muestra que hoy se puede hacer de forma continua: cada cambio viaja en segundos y los resultados se renuevan cada 10 minutos.

## Qué se gana

- **Decisiones con datos recientes**, no con los de ayer.
- **Historia**: se puede saber qué cambió, cuándo y qué valor tenía antes.
- **Tranquilidad para la operación**: el análisis puede crecer sin frenar a nadie.

Siguiente página: [El recorrido de un cambio](El-recorrido-de-un-cambio.md).
