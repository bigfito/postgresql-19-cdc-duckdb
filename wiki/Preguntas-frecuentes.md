# Preguntas frecuentes

## Sobre los datos

**¿Los datos son reales?**
No. ElastiFlix es una empresa inventada y su catálogo de 6,899 películas también. Los títulos, las personas y las cifras se generaron para el laboratorio. Están hechos para parecerse a un catálogo de verdad, con sus huecos y sus irregularidades, pero no describen ninguna película real.

**¿Puedo conectar los datos de mi empresa?**
No tal como está. El laboratorio está construido alrededor del catálogo de ElastiFlix. Adaptarlo a otros datos es un proyecto aparte: el mecanismo sirve, pero las tablas y los resultados habría que diseñarlos de nuevo.

**¿Se pierde algo cuando se elimina un dato?**
En el tablero deja de verse. En el almacén queda registrado que existió y cuándo se eliminó. Está explicado en [La memoria del dato](La-memoria-del-dato.md).

## Sobre la rapidez

**¿Es tiempo real?**
La copia de la operación, sí: tarda segundos. Los resultados que ven los tableros se actualizan cada 10 minutos, así que un cambio tarda como mucho 15 en verse. Los detalles están en [Frescura y confianza](Frescura-y-confianza.md).

**¿Por qué cada 10 minutos y no al instante?**
Porque ordenar el dato y recalcular los resultados lleva entre 4 y 5 minutos, y hacerlo cada 10 deja margen. Para la mayoría de las decisiones de negocio, un dato de hace 15 minutos es más que suficiente; lo que cambia frente a un informe nocturno es no decidir con datos de ayer.

**¿Se podría hacer más rápido?**
Sí, con más recursos o con otro diseño de la parte que ordena y resume. No se probó.

## Sobre el uso

**¿Qué hace falta para ponerlo en marcha?**
Un equipo con 16 GB de memoria y una sola orden. La primera vez tarda unos minutos más, porque tiene que preparar las piezas; después arranca en menos de dos.

**¿Cuánto cuesta?**
Todas las herramientas son de código abierto y no hay licencias que pagar. El coste de usarlo es el equipo donde corre y el tiempo de quien lo maneja.

**¿Necesita Internet o la nube?**
Solo necesita Internet la primera vez, para descargar las piezas. Después funciona entero en el equipo, sin servicios externos.

**¿Qué pasa si se apaga el equipo?**
Se detiene. Al encenderlo hay que volver a ponerlo en marcha con una orden, y retoma donde estaba sin perder ni repetir datos.

**¿Trae tableros ya hechos?**
No. Entrega siete tablas de resultados listas para consultar, descritas en [Qué preguntas responde](Qué-preguntas-responde.md). Los gráficos los arma quien lo usa.

## Sobre llevarlo más lejos

**¿Esto escala a una empresa grande?**
El mecanismo, sí: las herramientas que usa son las mismas que emplean organizaciones con muchos más datos. Este laboratorio en concreto, no: corre en un solo equipo y solo se probó con un catálogo pequeño.

**¿Qué haría falta para usarlo en producción?**
Lo que no tiene: respaldo si un equipo falla, usuarios y permisos, avisos de fallos, copias de seguridad y pruebas con el volumen real. Está detallado en [Alcance y límites](Alcance-y-límites.md).

**¿Sirve como punto de partida para un proyecto real?**
Como referencia de cómo encajan las piezas y de qué decisiones hay que tomar, sí. Las decisiones del laboratorio y sus motivos están en el [documento de decisiones](../lab-design/DECISIONS-AND-VALIDATIONS.md), que es técnico. Como base de código para copiar y desplegar, no.

Siguiente página: [Glosario](Glosario.md).
