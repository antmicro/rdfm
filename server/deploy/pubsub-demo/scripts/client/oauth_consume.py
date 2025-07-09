from kafka import KafkaConsumer
from provider import KeycloakTokenProvider

consumer_config = {
    "bootstrap_servers": "127.0.0.1:9094",
    "security_protocol": "SASL_SSL",
    "ssl_cafile": "../../server/CA.crt",
    "sasl_mechanism": "OAUTHBEARER",
}
topics = ["RDFM"]
keycloak_token_provider = KeycloakTokenProvider("test-client", "RnXXukKNSOj2JVNpJnyey6xGGIQQImVi")

consumer = KafkaConsumer(*topics, sasl_oauth_token_provider=keycloak_token_provider, **consumer_config)
for message in consumer:
    print(message)
