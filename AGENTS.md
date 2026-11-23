# AGENTS.md

Instrucciones para cualquier agente de programación que trabaje en este repositorio: Claude Code, Google Antigravity, GitHub Copilot, Cursor o Junie.

## Qué es este repositorio

Un laboratorio local de ingeniería de datos: PostgreSQL 19 → Flink CDC → Apache Iceberg (Bronze, Silver, Gold) → PySpark y Airflow → DuckDB → Superset, todo en contenedores con Docker Compose.

## Qué leer antes de trabajar

| Documento | Para qué |
|---|---|
| [planning/PLAN.md](planning/PLAN.md) | Qué hay que hacer y en qué orden. Es el único plan de actividades |
| [lab-design/LAB-DESIGN.md](lab-design/LAB-DESIGN.md) | Cómo debe quedar cada pieza. Es el diseño vigente |
| [lab-design/DECISIONS-AND-VALIDATIONS.md](lab-design/DECISIONS-AND-VALIDATIONS.md) | Por qué el diseño es así, qué se probó y qué decisiones siguen abiertas |

## Reglas

1. Sigue las reglas de la sección 2 de `planning/PLAN.md`. Son obligatorias.
2. Trabaja una actividad del plan a la vez y respeta sus dependencias.
3. Al terminar una actividad: márcala en el plan, ejecuta `python planning/update_progress.py` y añade una línea a la bitácora.
4. No cambies el diseño por tu cuenta. Si una actividad no se puede cumplir como está escrita, anótalo en la sección 6 del plan y detente.
5. No escribas contraseñas ni claves en ningún archivo versionado. Las credenciales salen de `.env`, que no se versiona.
6. Para dudas sobre una librería o herramienta, consulta su documentación vigente antes de escribir código; no te fíes de la memoria. Di de dónde salió cada dato.
7. Haz commit o push solo cuando la persona responsable lo pida.
8. Escribe la documentación y los mensajes de commit en español.
9. Los diagramas y los bocetos de pantalla se hacen con [Archify](https://github.com/tt-a1i/archify), no con Mermaid ni con dibujos en texto. Cada uno vive en `lab-design/diagrams/` con tres archivos: la fuente `.json`, la página interactiva `.html` y el `.svg` que se incrusta en la documentación. Si encuentras un diagrama Mermaid, un boceto dibujado con caracteres o un flujo escrito con flechas, conviértelo. Los árboles de directorios sí se quedan como texto, y las correspondencias simples entre dos columnas van en una tabla.
10. Antes de empezar una actividad, activa la skill que le corresponde (tabla siguiente) y trabaja con ella hasta terminarla.
11. El laboratorio se construye en un solo equipo. No dejes material del proyecto fuera del repositorio: cada servicio guarda su `Dockerfile` y sus archivos en su propio directorio, y `docker-compose.yml`, en la raíz, los integra a todos.

## Skills por tipo de actividad

Cada fase del plan indica su skill por defecto. Si una actividad concreta es de otro tipo, manda la tabla.

| La actividad consiste en | Skill |
|---|---|
| Código Java: el Event Simulator y su proyecto Maven | `/java-developer` |
| Código Python: jobs PySpark, DAG de Airflow, configuración de Superset y scripts escritos en Python | `/python-developer` |
| Todo lo demás: Compose, Dockerfile, SQL, YAML de Flink, scripts de shell de arranque y de operación, diagramas y cualquier duda o cambio de diseño | `/solution-architect` |

Cómo activarla:

- **Claude Code:** invoca la skill por su nombre (`/java-developer`, `/python-developer` o `/solution-architect`).
- **Google Antigravity, GitHub Copilot, Cursor y Junie:** no tienen esas skills instaladas. Lee el archivo `SKILL.md` de la skill y aplícalo como instrucciones durante la actividad. Están en la carpeta personal de quien trabaja en el equipo, en `~/.claude/skills/<skill>/SKILL.md`.

Si una skill y el diseño discrepan, manda el diseño. Las skills traen valores por defecto que aquí no aplican: el laboratorio usa Python 3.12, no usa Spring Boot ni ningún framework web, y sus versiones son las de la sección 3 del diseño.

## Cómo llega este archivo a cada agente

Los cinco agentes leen por sí solos el `AGENTS.md` de la raíz del repositorio; no hace falta ningún archivo propio de cada herramienta. Claude Code lo recibe a través de `CLAUDE.md`. Comprobado en la documentación de cada uno el 2026-11-22. Si Junie no lo aplicara, se le indica la ruta en *Settings | Tools | Junie | Project Settings*.
