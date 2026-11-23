# Frescura y confianza

**¿Qué tan al día está lo que veo y cómo sé que es correcto?**

Un tablero sirve para decidir solo si se cumplen dos cosas: que el dato sea reciente y que sea fiable. El laboratorio atiende las dos por separado.

![Qué pasa en cada actualización: tres revisiones intercaladas con el trabajo sobre el dato, y un aviso si algo falla](../lab-design/diagrams/wiki-frescura-y-confianza.svg)

## Qué tan al día está

| Etapa | Cada cuánto se actualiza | Retraso respecto a la operación |
|---|---|---|
| Bronce, la copia fiel | De forma continua | Entre 11 y 50 segundos |
| Plata y Oro | Cada 10 minutos | 15 minutos como mucho |
| El tablero | Al recargarlo | El de Oro |

La actualización de cada 10 minutos arranca sola y tarda entre 4 y 5 minutos. Por eso el peor caso son 15: casi 10 de espera más 5 de trabajo.

## Cómo se comprueba que es correcto

Cada actualización incluye tres revisiones. Ninguna depende de que alguien se acuerde de hacerla.

| Revisión | Qué comprueba | Si falla |
|---|---|---|
| **De Bronce** | Que están todas las tablas y que la copia continua sigue funcionando. | No se toca Plata. Los tableros siguen con lo último que estaba bien. |
| **De Plata** | Que cada dato tiene una sola versión vigente, que las fechas de las versiones no se pisan y que no hay referencias sueltas. Son 24 comprobaciones. | No se toca Oro. Los tableros siguen con lo último que estaba bien. |
| **De Oro** | Que las siete tablas de resultados existen, tienen contenido y no traen identificadores vacíos ni repetidos. | La actualización queda marcada como fallida. Los tableros ya muestran esa carga hasta la siguiente. |

Además, una de las siete tablas de Oro mide qué tan completos están los datos, de modo que la calidad se puede mirar en un gráfico como cualquier otro indicador.

## Qué pasa cuando algo se detiene

- **Si el equipo se apaga o el laboratorio se detiene**, al volver a encenderlo retoma donde estaba. En las pruebas se detuvo y se volvió a levantar con todo en marcha, y la copia coincidió con la operación en las 20 tablas, sin perder ni repetir nada.
- **Si una actualización falla**, queda marcada como fallida y la siguiente lo vuelve a intentar a los 10 minutos.

## Lo que el laboratorio no hace

- **No avisa a nadie.** Un fallo queda visible en la herramienta que lleva el reloj del proceso, pero no se envía un correo ni un mensaje. En un uso real habría que añadirlo.
- **No vuelve a arrancar solo.** Si un componente se cae, hay que volver a levantarlo con una orden.

Siguiente página: [Las piezas y por qué se eligieron](Las-piezas-y-por-qué-se-eligieron.md).
