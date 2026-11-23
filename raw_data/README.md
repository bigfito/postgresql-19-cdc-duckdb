# Datos sintéticos de entrada de ElastiFlix

Estos archivos son **sintéticos**. No proceden del catálogo original, no usan
títulos de películas reales, nombres de personas reales ni nombres de compañías
reales, y las sinopsis están generadas. Los catálogos cerrados (estado, rating,
idiomas, países, géneros, idiomas hablados y campos de enrichment) sí usan los
valores exactos del contrato (secciones 8.2 y 8.5 del diseño).

## Semilla

```python
SEED = 20261113
```

El generador solo usa la biblioteca estándar de Python 3.12. Cada subsistema
toma su propia secuencia a partir de esa semilla; no interviene la fecha, la
hora, el orden de un `set` ni la red.

## Regenerar

Desde la raíz del repositorio:

```bash
python3 raw_data/generate_raw_data.py
python3 raw_data/generate_raw_data.py --out /tmp/raw_data_check
python3 raw_data/generate_raw_data.py --validate
```

Sin `--out`, reescribe los 20 CSV en este directorio. Con `--out <dir>`, escribe
ahí. `--validate` genera dos veces, comprueba el contrato (secciones 8.2, 8.3,
8.4 y 8.6 del diseño, más las correlaciones y la variedad de la tarea de
regeneración) y vuelve a escribir este README. `created_at` y `updated_at` no
están en los archivos: los asigna PostgreSQL.

## Excepciones documentadas

- **Longitud mínima de `homepage`:** 16 caracteres (no 15). Las URL con dominio
  reservado `.example` no pueden ser más cortas que `http://a.example`.
- **`original_title` en alfabeto no latino:** 666 películas (todas las de idiomas
  con script propio bajo las frecuencias congeladas de `LANGS`). El objetivo
  informal de ~770 era incompatible con esas frecuencias; el total de títulos
  que difieren del `title` se mantiene en 1,091 (666 no latinos + 425 latinos
  en otro idioma). Los 425 latinos se eligen entre idiomas con léxico propio
  en el generador (fr, es, it, de, pt, sv, da, no, nb, nl, pl); en el resto de
  idiomas latinos `original_title` coincide con `title`.
- **Longitudes de `tagline`:** se conservan mínimo (3), mediana (32), P95 (70) y
  máximo (248), pero la cola baja se ha desplazado: ninguna tagline mide entre 4
  y 13 caracteres, porque con frases reales no caben ~900 taglines distintas tan
  cortas (la tarea exige al menos un 99 % distintas).

## Cómo se generan los textos

- **Títulos:** palabras inglesas reales de listas curadas en el generador
  (`TITLE_WORDS`), combinadas con una gramática de plantillas (adjetivo + nombre,
  «The … of the …», «Nombre: subtítulo», números, etc.). La longitud se alcanza
  eligiendo palabras y estructuras, nunca recortando ni rellenando. Una lista de
  bloqueo (`TITLE_BLOCK`) descarta títulos de películas reales conocidas.
- **`original_title`:** palabras reales del idioma (japonés, coreano, chino,
  ruso, hindi, árabe, tailandés…, y francés, español, italiano, alemán… para los
  latinos), con longitud cercana a la del título.
- **Prosa (`tagline`, `overview`, `plot`):** frases completas generadas con
  plantillas y huecos tipados (personajes con pronombres coherentes, oficios,
  lugares, objetos, sucesos, objetivos, ciudades). Las comillas solo rodean una
  línea de diálogo completa y los saltos de línea solo separan frases. Las 416
  tramas cortadas en 3,000 caracteres terminan en un límite de palabra.
- **Personas:** nombres y apellidos reales de muchas culturas combinados al azar
  (`PERSON_BLOCK` evita combinaciones que coinciden con personas famosas); un 5 %
  usa nombres o apellidos con diacríticos.
- **Compañías, keywords y colecciones:** raíces y sufijos curados, apellidos,
  sustantivos ingleses comunes en minúsculas y ciudades reales; lista de bloqueo
  de compañías reales (`REAL_COMPANY_BLOCK`).

## Archivos

| Archivo | Filas | Bytes | SHA-256 |
|---|---:|---:|---|
| `movie_status.csv` | 1 | 21 | `689021fa0ea87ca899d6b44d52bc6e32b24a8d959b846fbb09da4b073b7167e2` |
| `content_rating.csv` | 7 | 40 | `8d28437a358e245d546ded5b4b0a7eaf673fda1f9350c776152519ea6c24c1ea` |
| `original_language.csv` | 43 | 198 | `e6a3b129b4c31bc207490b5e3cefcbd24769e7b40126347524e93ce88ad68394` |
| `enrichment_field.csv` | 21 | 243 | `17f440ef86aec3dc22c038a8c5c24cfc27aed03b8526fd2af97fb819e7240206` |
| `genre.csv` | 19 | 218 | `42d43328c7db198e7fd34e02dc6091fdf94c96945225f933689258182d35dd3a` |
| `keyword.csv` | 11762 | 224003 | `e26c00588e64b5ea957ded62aed445a25a170687a0d9d567653c7bd91298ac0a` |
| `person.csv` | 95050 | 1916275 | `28f9c2eb8cbe216e5129d3eccde9ea066b2e78a6c3b00e49bfe6be2a205438a9` |
| `production_company.csv` | 8061 | 211644 | `9e74b5967a7004cc60b39720d396bdebc022874bdf42d63cd7226f0afb1a9369` |
| `production_country.csv` | 98 | 1217 | `9e3ef769875510f343544cefc1eebb41b6eac2a929df66f75034817ad3137c94` |
| `spoken_language.csv` | 68 | 1001 | `75e28e01c7e570224d07c5a70ce337660d369497ecd02b5e6b0f07988ad99129` |
| `collection.csv` | 1039 | 28987 | `c1ca084395c3e018d3975029637a1d6a58e7d82026741bd37cf420966c310175` |
| `movie.csv` | 6899 | 18255005 | `afd374a574f61b981a595ea80500d2b3d00f705e7aba8a2ff067c6c0193fe08d` |
| `movie_collection.csv` | 1934 | 154626 | `0621c13bc3ba847e90b408d0d2d16a0ebf793a74c80bc0ec0182e094d772247c` |
| `movie_genre.csv` | 18604 | 206738 | `a1fe67ecb3521c0d6d053fef38efafc2736e9ef853c62faf0c3b1c9085dbeb2d` |
| `movie_keyword.csv` | 53857 | 790985 | `d00b86fe67b814bb42d03df2fafb189ca4ec13446e505f3b22a4c852c1b563d3` |
| `movie_cast.csv` | 178939 | 2753315 | `5ff6073a4492ba9a103cfdb74e9c32fc87e0a483efdb6217ebbf05f1d9e3ea65` |
| `movie_production_company.csv` | 23971 | 320549 | `b583bd44e1c2649cc6fc21a9eea7eb761a7a317f04367e0e349f1114123d81b1` |
| `movie_production_country.csv` | 10091 | 109994 | `e142f8fb99cfbb8ab973bb5fc5e748cb8a61f196ca2cf6bfbabd7c2026cf6962` |
| `movie_spoken_language.csv` | 9855 | 106093 | `bf6140f5578fc8cd61cd1963880b82a947f9b287cd9d5676a86821a6498d3fd3` |
| `movie_enrichment.csv` | 18606 | 655410 | `837c7c14a7e00fe3d8d6179e61b5840e33277431568ca9f6320bfb5764d526a5` |

Las filas no incluyen la cabecera. Columnas y claves: sección 8.2. Formato:
sección 8.3. Orden e identificadores: sección 8.4. Defectos intencionales:
sección 8.6. Orden de carga sin violar claves foráneas:
`movie_status`, `content_rating`, `original_language`, `enrichment_field`,
`genre`, `keyword`, `person`, `production_company`, `production_country`,
`spoken_language`, `collection`, `movie`, `movie_collection`, `movie_genre`,
`movie_keyword`, `movie_cast`, `movie_production_company`,
`movie_production_country`, `movie_spoken_language`, `movie_enrichment`.

## Validaciones

Resultado de `python3 raw_data/generate_raw_data.py --validate`:

```text
1. PASS. Existen los 20 archivos, con la cabecera de la sección 8.2 y menos de 50 MB.
2. PASS. UTF-8 sin BOM, sin CR, y todas las filas tienen los mismos campos al leerlas como RFC 4180 (sección 8.3).
3. PASS. Claves primarias y restricciones UNIQUE sin duplicados.
4. PASS. Claves foráneas íntegras y ninguna entidad huérfana.
5. PASS. Restricciones de la sección 12, posiciones consecutivas desde 1 y orden de la sección 8.4.
6. PASS. Columnas obligatorias sin nulos y ningún texto vacío: el campo vacío y sin comillas es NULL (sección 8.3).
7. PASS. Catálogos y frecuencias exactos; el resto del perfil, dentro de ±3 %.
8. PASS. Están los defectos de la sección 8.6 y no hay repeticiones dentro de una película ni un keyword_id con dos nombres.
9. PASS. Cada fila de movie_enrichment corresponde a un dato presente, y los códigos fx cuadran con el estreno.
11. PASS. Ninguna película tiene dos keywords del mismo nombre.
12. PASS. Correlaciones de Spearman (tarea §4.1 y §4.2) dentro de ±0.15; ningún par en ±1.00.
13. PASS. Variedad de títulos, tagline, overview, plot y homepage (tarea §4.3, §4.4, §4.8).
14. PASS. Contenido de celdas (comas, comillas, saltos) según la tarea §4.5 (±5 %).
15. PASS. Todos los nombres de persona están en alfabeto latino; un 5 % lleva diacríticos.
16. PASS. imdb_id no secuenciales (rango tt0000417..tt35725827) y homepage solo con dominios .example.
17. PASS. Cada palabra de los títulos (salvo números) está en la lista de palabras del generador.
18. PASS. Prosa sin comillas ni saltos de línea pegados a letras por ambos lados, y comillas emparejadas.
10. PASS. SHA-256 idéntico en dos ejecuciones.
```

## Correlaciones de Spearman observadas

| Par | Objetivo | Observado |
|---|---:|---:|
| `id` ~ `rel` | +0.96 | +0.962 |
| `id` ~ `vc` | -0.42 | -0.414 |
| `id` ~ `kw` | -0.39 | -0.382 |
| `id` ~ `rev` | -0.35 | -0.350 |
| `id` ~ `bud` | -0.16 | -0.160 |
| `id` ~ `plot` | -0.15 | -0.154 |
| `id` ~ `ov` | -0.14 | -0.142 |
| `id` ~ `rt` | -0.12 | -0.117 |
| `id` ~ `cast` | -0.09 | -0.075 |
| `id` ~ `pop` | +0.09 | +0.093 |
| `id` ~ `us` | -0.04 | +0.020 |
| `id` ~ `va` | +0.02 | +0.031 |
| `id` ~ `tl` | +0.01 | +0.021 |
| `va` ~ `us` | +0.97 | +0.992 |
| `bud` ~ `rev` | +0.70 | +0.694 |
| `rev` ~ `vc` | +0.70 | +0.695 |
| `pop` ~ `vc` | +0.44 | +0.433 |
| `bud` ~ `pop` | +0.42 | +0.417 |
| `plot` ~ `vc` | +0.34 | +0.340 |
| `rt` ~ `bud` | +0.32 | +0.304 |
| `cast` ~ `bud` | +0.28 | +0.249 |
| `va` ~ `vc` | +0.24 | +0.237 |
| `va` ~ `pop` | +0.21 | +0.209 |
| `rel` ~ `bud` | -0.05 | -0.057 |

