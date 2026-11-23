# Las piezas y por qué se eligieron

**¿Qué hace cada herramienta, en una línea, y por qué esa?**

El laboratorio combina varias herramientas, cada una con un solo trabajo. No hace falta conocerlas para entender lo que el laboratorio demuestra; esta página existe para quien oiga sus nombres en una reunión y quiera saber qué papel juega cada una.

![Las piezas del laboratorio y el trabajo de cada una, de quien registra los datos a quien los consulta](../lab-design/diagrams/wiki-las-piezas.svg)

## Cada pieza y su trabajo

| Pieza | Herramienta | Qué hace | Por qué esa |
|---|---|---|---|
| Simulador | Un programa propio, en Java | Hace de empresa en funcionamiento: da de alta, cambia y elimina películas sin parar. | Para que haya actividad real que observar, en lugar de una carga hecha de una vez. |
| Base de la operación | PostgreSQL | Guarda el catálogo como lo haría el sistema del día a día. | Es una base de datos muy extendida, y anota cada cambio en un registro del que se puede copiar. |
| Captura de cambios | Flink CDC | Lee ese registro y copia cada cambio al almacén, de forma continua. | No obliga a modificar la operación ni a escribir programas: se configura. |
| Almacén de tablas | Iceberg | Guarda Bronce, Plata y Oro como tablas ordenadas. | Permite corregir y actualizar datos sin romper lo que otros están leyendo. |
| Disco del almacén | RustFS | Es donde quedan físicamente los archivos. | Sustituye a un servicio de nube, para que todo corra en un solo equipo. |
| Motor de cálculo | Spark | Ordena el dato en Plata y lo resume en Oro. | Está pensado para transformar muchos datos de una vez. |
| Reloj y vigilante | Airflow | Lanza la actualización cada 10 minutos, encadena sus pasos y deja constancia de cada una. | Permite ver qué corrió, cuándo y si terminó bien. |
| Motor de consulta | DuckDB | Lee Oro cuando un tablero pregunta. | Es ligero: no hay que mantener un servidor más. |
| Tableros | Superset | Dibuja los gráficos. | Se usa desde el navegador, sin instalar nada en cada puesto. |

## Lo que tienen en común

- **Todas son de código abierto.** No hay licencias que pagar para usar el laboratorio.
- **Todas se pueden reemplazar.** Cada una hace un solo trabajo, así que cambiar los tableros o el motor de cálculo no obliga a rehacer lo demás.
- **Todas corren juntas en un solo equipo.** Se ponen en marcha con una orden y no dependen de servicios externos.

## Por qué tantas piezas

Parece mucho para un catálogo de películas, y lo es. El laboratorio no busca la solución más corta para este caso: busca enseñar, a escala pequeña, la misma división de trabajo que usa una empresa con muchos más datos. Lo que aquí cabe en un portátil es, pieza por pieza, lo que en un entorno real se reparte entre varios equipos y servidores.

Siguiente página: [Ver una demostración](Ver-una-demostración.md).
