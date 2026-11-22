# Datos sintéticos de entrada de ElastiFlix

Estos archivos son **sintéticos**. No proceden del catálogo original, no usan
títulos de películas reales, nombres de personas reales ni nombres de compañías
reales, y las sinopsis están generadas. Los catálogos cerrados (estado, rating,
idiomas, países, géneros, idiomas hablados y campos de enrichment) sí usan los
valores exactos del contrato.

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
python3 raw_data/generate_raw_data.py --validate
```

El primer comando reescribe los 20 CSV en este directorio. `--validate` los
genera dos veces, comprueba el contrato y vuelve a escribir este README.
`created_at` y `updated_at` no están en los archivos: los asigna PostgreSQL.

## Archivos

| Archivo | Filas | Bytes | SHA-256 |
|---|---:|---:|---|
| `movie_status.csv` | 1 | 21 | `689021fa0ea87ca899d6b44d52bc6e32b24a8d959b846fbb09da4b073b7167e2` |
| `content_rating.csv` | 7 | 40 | `8d28437a358e245d546ded5b4b0a7eaf673fda1f9350c776152519ea6c24c1ea` |
| `original_language.csv` | 43 | 198 | `e6a3b129b4c31bc207490b5e3cefcbd24769e7b40126347524e93ce88ad68394` |
| `enrichment_field.csv` | 21 | 243 | `17f440ef86aec3dc22c038a8c5c24cfc27aed03b8526fd2af97fb819e7240206` |
| `genre.csv` | 19 | 218 | `42d43328c7db198e7fd34e02dc6091fdf94c96945225f933689258182d35dd3a` |
| `keyword.csv` | 11762 | 139745 | `63d27367d457b21930acd32e4854e3e44acff3e27e9d377b623ea9077627a8e2` |
| `person.csv` | 95050 | 2136683 | `5bb0bc73818624ee970ee8b3f8d23c91185dbd569f23d8f4e0a38a0eb8bdc975` |
| `production_company.csv` | 8061 | 103188 | `29a9dd0058243fa06084314b17f5804ffd12cacdd1406ec0c1be7fbea5d1628c` |
| `production_country.csv` | 98 | 1217 | `9e3ef769875510f343544cefc1eebb41b6eac2a929df66f75034817ad3137c94` |
| `spoken_language.csv` | 68 | 1001 | `75e28e01c7e570224d07c5a70ce337660d369497ecd02b5e6b0f07988ad99129` |
| `collection.csv` | 1039 | 17616 | `68611ad9f2f1d76c28467ca4d7bc148413edcc64207a54086306f1c67c57bd08` |
| `movie.csv` | 6899 | 18208776 | `91c6e135b064fe90563e3edc14f8770a36f00706d088ec1bc3d98dbdd4fb494b` |
| `movie_collection.csv` | 1934 | 154626 | `0621c13bc3ba847e90b408d0d2d16a0ebf793a74c80bc0ec0182e094d772247c` |
| `movie_genre.csv` | 18604 | 206738 | `a1fe67ecb3521c0d6d053fef38efafc2736e9ef853c62faf0c3b1c9085dbeb2d` |
| `movie_keyword.csv` | 53857 | 812153 | `ef5cc93c8ad3c6a194d20350b80db7e93028a388dfba2b84bb6cfe152ac2f2f3` |
| `movie_cast.csv` | 178939 | 2765956 | `96d497039e98948903f1acc5dc0f04d25d7c244e643a4e909ca9ffb87fca7e98` |
| `movie_production_company.csv` | 23971 | 320549 | `b583bd44e1c2649cc6fc21a9eea7eb761a7a317f04367e0e349f1114123d81b1` |
| `movie_production_country.csv` | 10091 | 109994 | `e142f8fb99cfbb8ab973bb5fc5e748cb8a61f196ca2cf6bfbabd7c2026cf6962` |
| `movie_spoken_language.csv` | 9855 | 106093 | `bf6140f5578fc8cd61cd1963880b82a947f9b287cd9d5676a86821a6498d3fd3` |
| `movie_enrichment.csv` | 18606 | 655475 | `a727d54d0ad8f50ad9d563291fb0662733e4bc7063d2971381f741f792982959` |

Las filas no incluyen la cabecera. Orden de carga sin violar claves foráneas:
`movie_status`, `content_rating`, `original_language`, `enrichment_field`,
`genre`, `keyword`, `person`, `production_company`, `production_country`,
`spoken_language`, `collection`, `movie`, `movie_collection`, `movie_genre`,
`movie_keyword`, `movie_cast`, `movie_production_company`,
`movie_production_country`, `movie_spoken_language`, `movie_enrichment`.

## Validaciones

Resultado de `python3 raw_data/generate_raw_data.py --validate`:

```text
1. PASS. Existen los 20 archivos, con la cabecera de la sección 6 y menos de 50 MB.
2. PASS. UTF-8 sin BOM, sin CR, y todas las filas tienen los mismos campos al leerlas como RFC 4180.
3. PASS. Claves primarias y restricciones UNIQUE sin duplicados.
4. PASS. Claves foráneas íntegras y ninguna entidad huérfana.
5. PASS. Restricciones de la sección 6, posiciones consecutivas desde 1 y orden de la sección 7.
6. PASS. Columnas obligatorias sin nulos y ningún texto vacío: el campo vacío y sin comillas es NULL.
7. PASS. Catálogos y frecuencias de la sección 8 exactos; el resto del perfil, dentro de ±3 %.
8. PASS. Están los defectos de la sección 10 y no hay repeticiones dentro de una película ni un keyword_id con dos nombres.
9. PASS. Cada fila de movie_enrichment corresponde a un dato presente, y los códigos fx cuadran con el estreno.
10. PASS. SHA-256 idéntico en dos ejecuciones.
```
