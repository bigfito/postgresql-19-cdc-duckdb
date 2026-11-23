# =============================================================================
# ElastiFlix: imagen de Airflow capaz de lanzar los jobs de Spark (diseño,
# sección 18)
# =============================================================================
# La usan los tres servicios de Airflow del Compose (airflow-apiserver,
# airflow-scheduler y airflow-dag-processor) y el job airflow-init.
#
# Airflow lanza cada job con spark-submit en modo cliente: el driver corre
# aquí, dentro del scheduler, y los ejecutores en spark-worker. Por eso la
# imagen oficial de Airflow necesita cuatro cosas más:
#   - Java 21, el mismo que usa la imagen de Spark, para el driver;
#   - PySpark 4.1.4, la misma versión que el clúster, que además aporta el
#     comando spark-submit;
#   - el proveedor de Spark de Airflow, que trae SparkSubmitOperator;
#   - los JAR de Iceberg, para que el driver hable con el catálogo REST y
#     con RustFS.
#
# La variante -python3.12 trae la misma versión menor de Python que
# pyspark/Dockerfile instala en la imagen de Spark. Si difirieran, PySpark
# abortaría el job (validación 8).

FROM apache/airflow:3.4.0-python3.12

ARG SPARK_PROVIDER_VERSION=6.3.4
ARG PYSPARK_VERSION=4.1.4
ARG ICEBERG_VERSION=1.12.0
ARG SPARK_RUNTIME_FLAVOR=4.1_2.13

USER root

# Java 21 sin entorno gráfico. El directorio que instala lleva la arquitectura
# en el nombre (java-21-openjdk-amd64 o -arm64); el enlace deja una ruta fija
# para JAVA_HOME en las dos.
RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends openjdk-21-jre-headless; \
    apt-get autoremove -yqq --purge; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*; \
    ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")" /usr/lib/jvm/java-21-openjdk; \
    # Puntos de montaje. En el Compose se montan encima, en solo lectura,
    # pyspark/conf, pyspark/jobs y pyspark/reference, en las mismas rutas que
    # en la imagen de Spark.
    mkdir -p /opt/spark/conf /opt/spark/jobs /opt/spark/reference; \
    chown -R airflow:root /opt/spark

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk

USER airflow

# PySpark y el proveedor de Spark. El proveedor depende de pyspark-client sin
# tope de versión y por sí solo instalaría una más nueva que el clúster; se
# fijan pyspark y pyspark-client a la misma. Se repite la versión de Airflow
# para que pip no la cambie al resolver las dependencias.
RUN pip install --no-cache-dir \
        "apache-airflow==${AIRFLOW_VERSION}" \
        "apache-airflow-providers-apache-spark==${SPARK_PROVIDER_VERSION}" \
        "pyspark==${PYSPARK_VERSION}" \
        "pyspark-client==${PYSPARK_VERSION}"

# JAR de Iceberg, los mismos que lleva la imagen de Spark. Van en la carpeta
# jars del paquete pyspark, que es la que lee el spark-submit de este paquete.
# Cada descarga se comprueba contra el SHA-1 que publica Maven Central.
RUN set -eu; \
    maven=https://repo.maven.apache.org/maven2; \
    jars="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent / "jars")')"; \
    fetch_maven() { \
        url="$maven/$1"; dest="$jars/${1##*/}"; \
        curl -fsSL --retry 3 -o "$dest" "$url"; \
        echo "$(curl -fsSL --retry 3 "$url.sha1" | cut -d' ' -f1)  $dest" | sha1sum -c -; \
    }; \
    fetch_maven "org/apache/iceberg/iceberg-spark-runtime-${SPARK_RUNTIME_FLAVOR}/${ICEBERG_VERSION}/iceberg-spark-runtime-${SPARK_RUNTIME_FLAVOR}-${ICEBERG_VERSION}.jar"; \
    fetch_maven "org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar"; \
    java -version; \
    spark-submit --version

# El driver comunica a los ejecutores el nombre del intérprete y cada lado lo
# resuelve en su PATH; la imagen de Spark declara el mismo valor.
ENV PYSPARK_PYTHON=python3.12
# Configuración del catálogo Iceberg y de la memoria de cada job: la misma
# carpeta pyspark/conf que usan spark-master y spark-worker.
ENV SPARK_CONF_DIR=/opt/spark/conf
