# Ver una demostración

**¿Qué voy a ver en una demostración y en qué fijarme?**

La forma más convincente de entender el laboratorio es verlo funcionar. Una demostración completa lleva unos 25 minutos, y casi todo ese tiempo es esperar a dos actualizaciones. La conduce una persona técnica; esta página es para quien la mira.

![Una demostración en seis momentos, de la puesta en marcha a seguir un cambio hasta el gráfico](../lab-design/diagrams/wiki-demostracion.svg)

## Los seis momentos

| Momento | Qué se ve | En qué fijarse |
|---|---|---|
| **1. Todo arranca** | Con una sola orden se ponen en marcha todas las piezas. Tarda menos de dos minutos. | No hay pasos manuales entre una pieza y otra. |
| **2. La empresa trabaja** | Una lista que avanza sola: altas, cambios y bajas de películas, varias por segundo. | Es actividad real sobre una base de datos, no una animación. |
| **3. Los cambios llegan a la copia** | Junto a cada movimiento aparece una marca cuando ya está en la copia, con los segundos que tardó. | Nadie pidió esa copia: ocurre sola y de forma continua. |
| **4. El dato se ordena** | Un panel muestra la actualización de cada 10 minutos, paso a paso, con sus revisiones. | Arranca sola y deja constancia de si cada paso terminó bien. |
| **5. Se arma un gráfico** | En la herramienta de tableros se elige una tabla de resultados y se dibuja un gráfico en un par de minutos. | Quien lo arma no cruza datos: la tabla ya viene preparada. |
| **6. Se sigue un cambio** | Se elige un cambio recién hecho, por ejemplo un título, y se mira en cada etapa hasta verlo en el gráfico. | El dato nuevo aparece solo, y el anterior sigue guardado con su fecha. |

## El momento que importa

Es el sexto. Los cinco anteriores preparan el terreno; el sexto es la prueba: algo cambia en la operación y, minutos después, cambia en el gráfico sin que nadie haga nada entre medias.

## Preguntas que vale la pena hacer durante la demostración

- ¿Cuánto tardó este cambio en llegar a la copia? ¿Y al gráfico?
- ¿Qué pasa si elimino esta película? ¿Desaparece también del almacén?
- ¿Qué decía este dato antes del cambio? ¿Dónde está guardado?
- ¿Qué ocurre si una revisión falla?

## Para quien la conduce

Los pasos exactos, con sus órdenes, están en la [guía de la demostración](../lab-design/LAB-DESIGN.md#guía-de-la-demostración) del documento de diseño.

Siguiente página: [Alcance y límites](Alcance-y-límites.md).
