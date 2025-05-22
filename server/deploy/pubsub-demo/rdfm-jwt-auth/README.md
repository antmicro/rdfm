A custom `AuthenticateCallbackHandler` made to authenticate producers that have already been authenticated with the RDFM managmenet server. Authorization on principal/group basis should be handled using Kafka ACLs.

Build with

```
mvn package
```

Create a [Kafka image](../Dockerfile) with the package pulled into `/opt/kafka/libs`

```
docker build -t kafka-for-rdfm ..
```

After that, append this to `server.properties`:

```
listener.name.<name>.plain.sasl.server.callback.handler.class=com.antmicro.rdfm.DeviceAuthenticateCallbackHandler
```
