FROM apache/kafka:4.0.0

# Strimzi OAuth JARs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-common/0.16.2/kafka-oauth-common-0.16.2.jar /opt/kafka/libs 
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-server/0.16.2/kafka-oauth-server-0.16.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-client/0.16.2/kafka-oauth-client-0.16.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/io/strimzi/kafka-oauth-keycloak-authorizer/0.16.2/kafka-oauth-keycloak-authorizer-0.16.2.jar /opt/kafka/libs

# Other dependencies
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/com/nimbusds/nimbus-jose-jwt/9.37.2/nimbus-jose-jwt-9.37.2.jar /opt/kafka/libs
ADD --chown=appuser:appuser https://repo1.maven.org/maven2/com/auth0/java-jwt/4.5.0/java-jwt-4.5.0.jar /opt/kafka/libs

# Our callback (package with `mvn package`)
COPY --chown=appuser:appuser ./rdfm-jwt-auth/target/rdfm-jwt-auth-0.1.jar /opt/kafka/libs
