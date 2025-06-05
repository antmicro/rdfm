### Generate root of trust and cert for RDFM management server

Use RDFM's [certgen script](../../../tests/certgen.sh)
```
../../../tests/certgen.sh ../server IP:127.0.0.1,DNS:localhost,DNS:rdfm-server
```

### Generate keystore and truststore for test SSL deployment

This creates files in a format that's accepted by the Kafka broker.
```
./storegen.sh --cn broker --san IP:127.0.0.1,DNS:localhost,DNS:broker --password 123123 --destination ../broker --cacert ../server/CA.crt --cakey ../server/CA.key
```

### Generate certs for other miscellaneous services

This example generates a cert-key pair for a service reachable through DNS via "keycloak".
```
./key4service.sh --cn keycloak --san IP:127.0.0.1,DNS:keycloak --cacert ../server/CA.crt --cakey ../server/CA.key
```

### Pull token from Keycloak

This examples contacts a Keycloak instance and pulls a token for a specified client ID.

```
CLIENTID=test-client
SECRET=RnXXukKNSOj2JVNpJnyey6xGGIQQImVi
SERVER=http://keycloak:8080/realms/master/protocol/openid-connect/token
curl -s -X POST -d "grant_type=urn:ietf:params:oauth:grant-type:uma-ticket&client_id=$CLIENTID&client_secret=$SECRET&audience=kafka-broker-introspection" $SERVER | jq -r .access_token
```

### Generate test device JWT

This example creates a device token using [jwt tool](https://github.com/mike-engel/jwt-cli).

```
jwt encode -A HS256 -S $RDFM_JWT_SECRET -P device_id='00:00:00:00:00:00' -P created_at=$(date +%s) -P expires=300
```
