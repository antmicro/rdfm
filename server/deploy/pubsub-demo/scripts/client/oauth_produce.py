from kafka import KafkaProducer
from provider import KeycloakTokenProvider

consumer_config = {
    "bootstrap_servers": "127.0.0.1:9094",
    "security_protocol": "SASL_SSL",
    "ssl_cafile": "../../server/CA.crt",
    "sasl_mechanism": "OAUTHBEARER",
}
keycloak_token_provider = KeycloakTokenProvider("test-client", "RnXXukKNSOj2JVNpJnyey6xGGIQQImVi")

producer = KafkaProducer(sasl_oauth_token_provider=keycloak_token_provider, **consumer_config)

future = producer.send("quickstart-events", b'test test test test')
record_metadata = future.get(timeout=3)
print(record_metadata.topic)
print(record_metadata.partition)
print(record_metadata.offset)
