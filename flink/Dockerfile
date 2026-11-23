# =============================================================================
# ElastiFlix: imagen de Flink con Flink CDC (diseño, sección 14)
# =============================================================================
# La usan tres servicios del Compose: flink-jobmanager, flink-taskmanager y el
# job one-shot flink-cdc-submit.
#
# Dependencias: las que lista la guía oficial de Flink CDC «Real-time PostgreSQL
# Ingestion into Iceberg» para Flink 2.2.1, con dos diferencias decididas en el
# diseño: Iceberg 1.10.2, último parche de la línea contra la que compila Flink
# CDC 3.7.0, e iceberg-aws-bundle, que aporta S3FileIO para escribir en RustFS.
#
# Cada descarga se comprueba contra la suma que publica su origen.

FROM flink:2.2.1-java21

ARG FLINK_CDC_VERSION=3.7.0
ARG FLINK_CDC_FLAVOR=2.2
ARG ICEBERG_VERSION=1.10.2
ARG HADOOP_VERSION=3.3.6
ARG COMMONS_LOGGING_VERSION=1.2

ENV FLINK_CDC_HOME=/opt/flink-cdc

USER root

# jq: el script de envío lee con él las respuestas de la API REST de Flink y
# del catálogo Iceberg. curl y envsubst ya vienen en la imagen base.
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    maven=https://repo.maven.apache.org/maven2; \
    apache=https://archive.apache.org/dist/flink; \
    # Descarga un artefacto de Maven Central y comprueba su SHA-1.
    fetch_maven() { \
        url="$maven/$1"; dest="$2/${1##*/}"; \
        curl -fsSL --retry 3 -o "$dest" "$url"; \
        echo "$(curl -fsSL --retry 3 "$url.sha1" | cut -d' ' -f1)  $dest" | sha1sum -c -; \
    }; \
    \
    # Distribución de Flink CDC, con su SHA-512.
    cdc="flink-cdc-${FLINK_CDC_VERSION}-${FLINK_CDC_FLAVOR}-bin.tar.gz"; \
    curl -fsSL --retry 3 -o "/tmp/$cdc" "$apache/flink-cdc-${FLINK_CDC_VERSION}/$cdc"; \
    echo "$(curl -fsSL --retry 3 "$apache/flink-cdc-${FLINK_CDC_VERSION}/$cdc.sha512" | cut -d' ' -f1)  /tmp/$cdc" | sha512sum -c -; \
    mkdir -p "$FLINK_CDC_HOME"; \
    tar -xzf "/tmp/$cdc" -C "$FLINK_CDC_HOME" --strip-components=1; \
    rm "/tmp/$cdc"; \
    \
    # Conectores del pipeline: van en la carpeta lib de Flink CDC, no en la de Flink.
    v="${FLINK_CDC_VERSION}-${FLINK_CDC_FLAVOR}"; \
    fetch_maven "org/apache/flink/flink-cdc-pipeline-connector-postgres/$v/flink-cdc-pipeline-connector-postgres-$v.jar" "$FLINK_CDC_HOME/lib"; \
    fetch_maven "org/apache/flink/flink-cdc-pipeline-connector-iceberg/$v/flink-cdc-pipeline-connector-iceberg-$v.jar" "$FLINK_CDC_HOME/lib"; \
    \
    # Runtime de Iceberg, S3FileIO, cliente de Hadoop y Commons Logging: van en
    # la carpeta lib de Flink, para el JobManager y el TaskManager.
    fetch_maven "org/apache/iceberg/iceberg-flink-runtime-2.0/${ICEBERG_VERSION}/iceberg-flink-runtime-2.0-${ICEBERG_VERSION}.jar" "$FLINK_HOME/lib"; \
    fetch_maven "org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar" "$FLINK_HOME/lib"; \
    fetch_maven "org/apache/hadoop/hadoop-client-api/${HADOOP_VERSION}/hadoop-client-api-${HADOOP_VERSION}.jar" "$FLINK_HOME/lib"; \
    fetch_maven "org/apache/hadoop/hadoop-client-runtime/${HADOOP_VERSION}/hadoop-client-runtime-${HADOOP_VERSION}.jar" "$FLINK_HOME/lib"; \
    fetch_maven "commons-logging/commons-logging/${COMMONS_LOGGING_VERSION}/commons-logging-${COMMONS_LOGGING_VERSION}.jar" "$FLINK_HOME/lib"; \
    \
    # Directorio de checkpoints. En el Compose se monta encima flink/data/.
    mkdir -p "$FLINK_HOME/state"; \
    chown -R flink:flink "$FLINK_CDC_HOME" "$FLINK_HOME/lib" "$FLINK_HOME/state"

# Pipeline y scripts de operación.
COPY --chown=flink:flink jobs/ /opt/flink/jobs/

# Configuración propia del laboratorio (sección 14).
COPY --chown=flink:flink config/flink-properties.conf /opt/flink/conf/elastiflix-properties.conf

USER flink

# Aplica flink-properties.conf sobre la configuración por defecto de la imagen,
# con la misma herramienta que usa su script de arranque. Cada línea «clave:
# valor» pasa a ser una opción -Dclave=valor.
RUN set -eu; \
    while IFS= read -r line; do \
        line=$(printf '%s' "$line" | sed 's/#.*$//' | tr -d '[:space:]'); \
        [ -n "$line" ] || continue; \
        set -- "$@" "-D${line%%:*}=${line#*:}"; \
    done < "$FLINK_HOME/conf/elastiflix-properties.conf"; \
    "$FLINK_HOME/bin/config-parser-utils.sh" "$FLINK_HOME/conf" "$FLINK_HOME/bin" "$FLINK_HOME/lib" "$@"
