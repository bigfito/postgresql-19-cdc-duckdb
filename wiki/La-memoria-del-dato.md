# La memoria del dato

**¿Cómo sabemos qué decía un dato antes y cuándo cambió?**

El sistema de la operación solo guarda cómo están las cosas hoy. Cuando un dato cambia, el valor anterior se sobrescribe y desaparece. El laboratorio hace lo contrario en su etapa Plata: cada cambio deja una versión nueva y conserva la anterior, con la fecha y la hora en que dejó de valer.

![La memoria del dato: el tablero muestra el título nuevo, y Plata guarda las dos versiones con sus fechas](../lab-design/diagrams/wiki-memoria-del-dato.svg)

## Cómo funciona, con un ejemplo real

Durante las pruebas, una película cambió de título a las 22:05:25. Así quedó guardada en Plata:

| Versión | Título | Vigente desde | Vigente hasta |
|---|---|---|---|
| 1 | Trial 6: Across the Untold Finale | 21:43:48 | 22:05:25 |
| 2 | Trial 6: Across the Untold Finale: Extended Edition | 22:05:25 | sigue vigente |

El tablero muestra solo la versión 2. Pero la 1 sigue ahí, y con ella se puede responder «¿cómo se llamaba esta película a las diez de la noche?».

## Qué recuerda el laboratorio

| Qué cambia | Qué se guarda |
|---|---|
| **El título, la sinopsis o el lema de una película** | Una versión nueva; la anterior se cierra con su fecha. |
| **El nombre de una saga o de una palabra clave** | Lo mismo: versión nueva y versión anterior cerrada. |
| **Las cifras de una película**, como su popularidad o su recaudación | Una foto nueva de las cifras cada vez que cambian. Las fotos anteriores se conservan. |
| **Una película eliminada** | Su versión se cierra con la fecha de la baja, y queda anotado que se eliminó. No se borra del almacén. |
| **Una película que vuelve después de eliminarse** | Una versión nueva, a continuación de la última que tuvo. |

## Para qué sirve

- **Explicar una cifra del pasado.** Un informe de hace un mes se puede reconstruir con los datos tal como eran entonces.
- **Auditar.** Queda registrado qué cambió y cuándo.
- **Ver evolución.** Las fotos de las cifras permiten dibujar cómo subió o bajó la popularidad de una película.

## Dos límites que conviene conocer

- **No todo guarda historia.** Los catálogos pequeños y estables, como la lista de idiomas o de clasificaciones por edad, guardan solo el valor actual.
- **Los cambios muy seguidos se resumen.** Plata se actualiza cada 10 minutos. Si un dato cambia tres veces dentro de ese intervalo, se guarda el último valor, no los tres. La copia fiel de Bronce tampoco guarda los pasos intermedios.

Siguiente página: [Frescura y confianza](Frescura-y-confianza.md).
