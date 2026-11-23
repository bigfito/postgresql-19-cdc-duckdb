# =============================================================================
# ElastiFlix: imagen de Spark con Iceberg y Python 3.12 (diseño, secciones 3 y 18)
# =============================================================================
# La usan dos servicios del Compose: spark-master y spark-worker. También sirve
# para lanzar un job a mano, en un contenedor temporal que hace de driver.
#
# Añade a la imagen oficial de Spark dos cosas:
#   - los JAR de Iceberg, para leer Bronze y escribir Silver y Gold a través del
#     catálogo REST, con S3FileIO sobre RustFS;
#   - Python 3.12, la misma versión menor que Airflow. En modo cliente el driver
#     corre en Airflow y los ejecutores aquí; si sus versiones menores difieren,
#     PySpark aborta el job (validación 8).
#
# Cada descarga se comprueba contra la suma que publica su origen.

FROM apache/spark:4.1.4-scala2.13-java21-python3-ubuntu

ARG ICEBERG_VERSION=1.12.0
ARG SPARK_RUNTIME_FLAVOR=4.1_2.13
# uv es solo la herramienta que instala Python; se fija igualmente, con la suma
# SHA-256 que PyPI publica para el wheel de cada arquitectura.
ARG UV_VERSION=0.13.9
ARG UV_SHA256_AMD64=d7f459fe4fd247d830351c75686d3996ace3c6f3f728eb0e85a30b7ada0cef19
ARG UV_SHA256_ARM64=ecb6028d79dc96fbeafffe5c8af62a7099487ebc05a701e76714eebcffd06375
ARG PYTHON_VERSION=3.12.16

USER root

# JAR de Iceberg: van en la carpeta jars de Spark, la que ven el master, el
# worker, los ejecutores y el driver.
RUN set -eu; \
    maven=https://repo.maven.apache.org/maven2; \
    # Descarga un artefacto de Maven Central y comprueba su SHA-1.
    fetch_maven() { \
        url="$maven/$1"; dest="$2/${1##*/}"; \
        curl -fsSL --retry 3 -o "$dest" "$url"; \
        echo "$(curl -fsSL --retry 3 "$url.sha1" | cut -d' ' -f1)  $dest" | sha1sum -c -; \
    }; \
    fetch_maven "org/apache/iceberg/iceberg-spark-runtime-${SPARK_RUNTIME_FLAVOR}/${ICEBERG_VERSION}/iceberg-spark-runtime-${SPARK_RUNTIME_FLAVOR}-${ICEBERG_VERSION}.jar" "$SPARK_HOME/jars"; \
    fetch_maven "org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar" "$SPARK_HOME/jars"; \
    chown spark:spark "$SPARK_HOME"/jars/iceberg-*.jar

# Python 3.12 con uv (sección 18). No toca el Python 3.10 del sistema ni añade
# repositorios de paquetes. pip comprueba el wheel de uv contra las sumas de
# arriba, y uv comprueba el intérprete que descarga contra las sumas que lleva
# incorporadas. Al terminar se retira uv: en ejecución no hace falta.
RUN set -eu; \
    printf 'uv==%s --hash=sha256:%s --hash=sha256:%s\n' \
        "$UV_VERSION" "$UV_SHA256_AMD64" "$UV_SHA256_ARM64" > /tmp/uv-requirements.txt; \
    pip3 install --no-cache-dir --require-hashes -r /tmp/uv-requirements.txt; \
    UV_PYTHON_INSTALL_DIR=/opt/python uv python install --no-cache --no-bin "$PYTHON_VERSION"; \
    ln -s /opt/python/cpython-"$PYTHON_VERSION"-*/bin/python3.12 /usr/local/bin/python3.12; \
    python3.12 --version; \
    pip3 uninstall -y uv; \
    rm /tmp/uv-requirements.txt

# Puntos de montaje. En el Compose se montan encima, en solo lectura,
# pyspark/conf, pyspark/jobs y pyspark/reference.
RUN mkdir -p "$SPARK_HOME/conf" "$SPARK_HOME/jobs" "$SPARK_HOME/reference" \
    && chown spark:spark "$SPARK_HOME/conf" "$SPARK_HOME/jobs" "$SPARK_HOME/reference"

# El driver comunica a los ejecutores el nombre del intérprete y cada lado lo
# resuelve en su PATH; la imagen de Airflow declara el mismo valor.
ENV PYSPARK_PYTHON=python3.12
# spark-submit y spark-sql, sin escribir la ruta completa.
ENV PATH="${SPARK_HOME}/bin:${PATH}"

USER spark
