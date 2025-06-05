### Demo Kafka deployment

#### Docker image setup

Slight modifications to the Kafka docker image are required for it to work nicely with RDFM's authentication scheme. We'll make use of `strmzi-kafka-oauth` and `rdfm-jwt-auth` to authenticate management clients and device clients respectively. Additionally, `strimzi-kafka-oauth` is also capable of authorization.

Before building the docker image, package `rdfm-jwt-auth`:

```sh
pushd rdfm-jwt-auth
mvn package
```

After that, build the image:

```sh
popd
DOCKER_BUILDKIT=1 docker build -t kafka-for-rdfm .
```

#### Keystore setup

Keystore is the means of storage of cryptographic credentials for a Kafka broker. It should have two of them, ours are:

* `KEYSTORE.p12` - for holding its own key-cert pair
* `TRUSTSTORE.p12` - for holding the root certificate

They can be password protected. To generate valid keystores for this demo deployment, first run [RDFM's certgen script](../../tests/certgen.sh):

```sh
../../tests/certgen.sh server IP:127.0.0.1,DNS:localhost,DNS:rdfm-server
```

It generates a `server` directory in which, alongside the key-cert pair that could be used for a RDFM server, lie `CA.crt` and `CA.key`. They are essential for generating keystores:

```sh
scripts/storegen.sh --cn broker --san IP:127.0.0.1,DNS:localhost,DNS:broker --password 123123 --destination broker --cacert server/CA.crt --cakey server/CA.key
```

The most imporant argument here is the `--cn`, which stands for Common Name. This demo cluster makes use of certificate Common Names to identify brokers during inter-broker communication. The above is reflected in the way we declare super users inside compose:

```yml
KAFKA_SUPER_USERS: User:broker;User:00:00:00:00:00:00
```

Aside from the mock device that should not be a super user in production, the brokers must have super user access to other brokers for replication of data and such. Without defining this, the cluster will fail to start.

#### Run

The following starts the Kafka broker alongside Keycloak:

```sh
docker compose -f docker-compose.kafka.yml up
```

If you've named your destination folders differenly with `storegen.sh`, adjust the volume mount in `docker-compose.kafka.yml` accordingly.

#### Keycloak setup

If you don't want to configure this manually, head to [import](#keycloak-import) section.

Management listener does authentication as well as authorization using Keycloak. To configure that behavior we first need to create a client for the broker to introspect tokens with:

1. Log into Keycloak with default credentials(`admin:admin`)
2. Head to the clients tab
3. Click on create client
4. In general settings, choose an ID, e.g.: `kafka-broker-introspection`
5. In capability config, set client authentication and authorization to on
6. Save
7. Copy the client secret from the credentials tab for your client and paste it into `server.properites` `oauth.client.secret` field
8. Copy the client ID and paste it into `server.properties` `oauth.client.id` field

After creating the client and pasting all the necessary fields into `server.properties`, configure authorization scopes, which define the possible actions that can be done on a cluster:

1. Head to clients tab
2. Click on the previously created introspection client
3. Under that client, head to the authorization tab
4. Under the authorization tab, head to the settings tab
5. Click the import button and import the settings from `authorization-scopes.json`
6. Confirm that the changes have taken place by heading to the scopes tab

Next configure the resources which define where the authorization rules should apply. For this simple demo the resource is going to be a single topic:

1. Head to clients tab
2. Click on the intropsection client previusly created
3. Under that client, head to the authorization tab
4. Under the authorization tab, head to the resources tab
5. Create new resource with name and display name of `Topic:quickstart-events`, optionally you can also declare it to be of type `Topic`
6. Define a list of possible authorization scopes that make sense for that resource, for this example `Read`, `Write`, `Create` and `Describe` are enough
7. Remove the `Default Resource`, if present

After that create a client policy:

1. Head to clients tab
2. Create client
3. Choose a client ID, e.g.: `test-client`
4. In capability config, set client authentication to on and tick off `Service account roles` checkbox
5. After creating the new client head back to the authorization tab of the introspection client
6. Under the authorization tab, head to the policies tab
7. Create a policy of type client and add the new client to it

Finally create a permission that ties it all together:

1. Head to clients clients tab
2. Click on the intropsection client previusly created
3. Under that client, head to the authorization tab
4. Under the authorization tab, head to the permissions tab
5. Click on create scoped-based permission
6. Choose an arbitrary name for the permission
7. For the resource choose the `Topic:quickstart-events`
8. Choose a set of required authorization scopes. You can choose `Read` or `Write`, but `Describe` must always stay since a client needs to first fetch metadata about a topic. Whether `Create` is required depends on if the topic already exists.

### Keycloak import

1. Go to clients
2. Import both [kafka-broker-introspection.json](kafka-broker-introspection.json) and [test-client.json](test-client.json)
3. Go to kafka-broker-introspection client authorization tab
4. Under settings, import [kafka-broker-introspection-test-authz-config.json](kafka-broker-introspection-test-authz-config.json)
5. Remove `Default Resource` from resources under the authorization tab

With the premade config, OAUTH [client scripts](scripts/client) will work straight away with no need to modify credentials.
