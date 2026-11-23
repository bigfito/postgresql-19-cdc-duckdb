# =============================================================================
# ElastiFlix: imagen del Event Simulator (diseño, secciones 9.8, 34 y 45.2)
# =============================================================================
# Dos etapas: la primera compila con Maven y deja instaladas las extensiones de
# DuckDB; la segunda solo lleva el JRE, el simulador y esas extensiones. Quien
# revisa el laboratorio no necesita JDK ni Maven en su máquina.
#
# Las dos imágenes base son las de la sección 3.2 del diseño, fijadas a una
# versión exacta.

# -----------------------------------------------------------------------------
# Etapa 1: compilación, pruebas e instalación de las extensiones de DuckDB
# -----------------------------------------------------------------------------
FROM maven:3.10.0-eclipse-temurin-25 AS build

WORKDIR /build

# Primero solo el pom: mientras no cambie, Docker reutiliza la capa con las
# dependencias descargadas.
COPY pom.xml .
RUN mvn -B -q dependency:go-offline

# Compila, pasa las pruebas unitarias y deja el JAR en target/ y sus
# dependencias en target/lib/. Si una prueba falla, la imagen no se construye.
COPY src ./src
RUN mvn -B -q verify

# Extensiones httpfs, iceberg y avro, instaladas con el propio driver JDBC del
# simulador, para que su versión y su plataforma coincidan con las que usará.
# Es el único paso que necesita Internet; al ejecutarse, el contenedor no
# descarga nada.
RUN java --enable-native-access=ALL-UNNAMED \
        -cp "target/event-simulator.jar:target/lib/*" \
        com.elastiflix.simulator.bronze.DuckDbExtensionInstaller /opt/duckdb_extensions

# -----------------------------------------------------------------------------
# Etapa 2: imagen de ejecución
# -----------------------------------------------------------------------------
FROM eclipse-temurin:25.0.5.1_2-jre

# Usuario sin privilegios (sección 45.2). No escribe en ningún directorio del
# host; dentro del contenedor solo usa /tmp, donde el driver de DuckDB extrae
# su librería nativa y donde queda la copia del log.
RUN groupadd --gid 10002 simulator \
    && useradd --uid 10002 --gid 10002 --no-create-home --home-dir /nonexistent \
               --shell /usr/sbin/nologin simulator

# Propiedad de root y solo lectura para el usuario simulator.
COPY --from=build /build/target/event-simulator.jar /opt/simulator/event-simulator.jar
COPY --from=build /build/target/lib/ /opt/simulator/lib/
COPY --from=build /opt/duckdb_extensions/ /opt/duckdb_extensions/

USER simulator
WORKDIR /opt/simulator

# Opciones de la JVM (sección 9.8):
#   -XX:MaxRAMPercentage=40   heap de unos 205 MB con el límite de 512 MB del
#                             contenedor. Deja sitio a los 128 MB de DuckDB y
#                             al resto de la memoria nativa. Por defecto la JVM
#                             tomaría la cuarta parte, que no alcanza para el
#                             dataset en memoria.
#   --enable-native-access    el driver de DuckDB carga una librería nativa.
#                             Sin la opción, Java 25 avisa en cada arranque.
# Forma exec: la JVM es el proceso 1 y recibe la señal de `docker compose stop`.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=40", "--enable-native-access=ALL-UNNAMED", "-jar", "/opt/simulator/event-simulator.jar"]
