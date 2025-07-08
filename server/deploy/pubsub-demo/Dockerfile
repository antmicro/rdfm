FROM maven:3.9-eclipse-temurin-17-alpine

COPY ./rdfm-jwt-auth /data/rdfm-jwt-auth
WORKDIR /data/rdfm-jwt-auth
RUN mvn package

FROM apache/kafka:4.0.0

COPY --from=0 --chown=appuser:appuser /data/rdfm-jwt-auth/target/rdfm-jwt-auth-*.jar /opt/kafka/libs

# Strimzi OAuth JARs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-common/0.16.2/kafka-oauth-common-0.16.2.jar /opt/kafka/libs 
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-server/0.16.2/kafka-oauth-server-0.16.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-client/0.16.2/kafka-oauth-client-0.16.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-keycloak-authorizer/0.16.2/kafka-oauth-keycloak-authorizer-0.16.2.jar /opt/kafka/libs

# Other dependencies
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/com/nimbusds/nimbus-jose-jwt/9.37.2/nimbus-jose-jwt-9.37.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/com/auth0/java-jwt/4.5.0/java-jwt-4.5.0.jar /opt/kafka/libs
