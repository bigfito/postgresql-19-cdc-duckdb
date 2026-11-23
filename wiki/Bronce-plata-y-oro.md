# Bronce, plata y oro

**¿Por qué el dato pasa por tres etapas y qué gana en cada una?**

El almacén para el análisis no es un solo lugar: son tres, uno detrás de otro. Los nombres vienen del oficio: el metal vale más cuanto más se trabaja. Cada etapa hace una sola cosa, y por eso es fácil saber dónde mirar cuando algo no cuadra.

![Bronce, plata y oro: qué gana el dato en cada etapa, desde la base del día a día hasta los tableros](../lab-design/diagrams/wiki-tres-capas.svg)

## Las tres etapas

| Etapa | Qué guarda | Para qué sirve |
|---|---|---|
| **Bronce** | Una copia exacta de la operación, sin tocar nada. Incluye lo que se eliminó, marcado como eliminado. | No perder nada. Es la red de seguridad: desde aquí se puede rehacer todo lo demás. |
| **Plata** | El mismo dato, limpio y ordenado para analizar, y con memoria: cada versión de cada dato, con sus fechas. | Entender el dato y su historia. |
| **Oro** | Siete tablas de resultados, cada una preparada para un tipo de pregunta. | Responder rápido. Es lo único que leen los tableros. |

## Una comparación que ayuda

Piensa en una cocina de restaurante:

- **Bronce es la despensa.** Los ingredientes entran tal como llegan del proveedor. No se tira nada.
- **Plata es la mesa de preparación.** Todo está lavado, cortado y etiquetado con su fecha.
- **Oro es el plato servido.** Listo para el comensal, que no necesita saber qué pasó antes.

## Por qué no ir directo al resultado

Hacerlo en un solo paso parece más simple, pero tiene un coste:

- **Si el resultado sale mal, no hay a dónde volver.** Con Bronce siempre se puede rehacer.
- **Cada pregunta nueva obligaría a empezar de cero.** Con Plata ya ordenada, una pregunta nueva es solo un resumen más.
- **Los errores se mezclan.** Con tres etapas, cada una se comprueba por separado antes de pasar a la siguiente.

## Comprobaciones entre etapas

Antes de dar por bueno cada paso, el laboratorio revisa el resultado. Si la revisión de Bronce o de Plata falla, el proceso se detiene y la etapa siguiente conserva lo último que estaba bien. Hay una excepción que conviene conocer: si falla la revisión de Oro, los tableros ya muestran esa carga hasta la actualización siguiente, y el fallo queda avisado.

Siguiente página: [Qué preguntas responde](Qué-preguntas-responde.md).
