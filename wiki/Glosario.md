# Glosario

Los términos que aparecen en este wiki y los que se oyen al hablar del laboratorio, explicados sin tecnicismos. Entre paréntesis, el nombre que usan los documentos técnicos cuando es distinto.

| Término | Qué significa |
|---|---|
| **Actualización** (corrida) | Cada vez que el laboratorio ordena el dato en Plata y recalcula Oro. Ocurre sola cada 10 minutos. |
| **Almacén analítico** (lakehouse) | El lugar donde se guarda la copia de los datos pensada para el análisis, separada del sistema de la operación. |
| **Alta, cambio y baja** (INSERT, UPDATE, DELETE) | Los tres movimientos que puede tener un dato: aparece, se modifica o se elimina. |
| **Bronce** (Bronze) | Primera etapa del almacén: la copia exacta de la operación, sin tocar nada. |
| **Captura de cambios** (CDC) | Técnica que copia cada cambio de una base de datos en cuanto ocurre, leyendo el registro interno de la propia base. No obliga a modificar el sistema de origen. |
| **Catálogo** | En este wiki, el conjunto de películas de ElastiFlix. En los documentos técnicos, la misma palabra nombra también el índice que dice qué tablas hay en el almacén. |
| **Código abierto** | Programas que cualquiera puede usar y revisar sin pagar licencia. |
| **Copia fiel** | Otra forma de llamar a Bronce. |
| **Etapas** (capas, arquitectura medallion) | Bronce, Plata y Oro: los tres pasos por los que pasa el dato dentro del almacén. |
| **Foto** (snapshot) | El valor de las cifras de una película en un momento dado. Cada vez que cambian se guarda una foto nueva. |
| **Historia** (historial, SCD tipo 2) | La forma de guardar un dato de modo que, cuando cambia, se conserva también el valor anterior con sus fechas. |
| **Operación** (sistema operacional, transaccional) | El sistema donde la empresa registra su trabajo diario. En el laboratorio, la base que guarda el catálogo. |
| **Orden** (comando) | La instrucción que se escribe para poner en marcha o detener el laboratorio. |
| **Oro** (Gold) | Tercera etapa del almacén: siete tablas de resultados, cada una preparada para un tipo de pregunta. |
| **Plata** (Silver) | Segunda etapa del almacén: el dato limpio, ordenado y con historia. |
| **Reloj del proceso** (orquestador) | La pieza que lanza cada actualización a su hora, encadena sus pasos y deja constancia de cómo terminó. |
| **Retorno** (ROI) | Lo que se ganó con una película en relación con lo que costó. |
| **Revisión** (validación) | Comprobación automática que se hace sobre cada etapa antes de pasar a la siguiente. |
| **Simulador** | El programa que hace de empresa en funcionamiento, generando altas, cambios y bajas sin parar. |
| **Tabla de resultados** (producto Gold) | Cada una de las siete tablas de Oro. |
| **Tablero** (dashboard) | Pantalla con uno o varios gráficos, que se actualiza sola a medida que cambian los datos. |
| **Versión vigente** | La versión de un dato que vale ahora. Las anteriores quedan guardadas como cerradas. |

Volver al [inicio](Home.md).
