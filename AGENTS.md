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
