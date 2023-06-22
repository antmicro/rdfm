# System overview

System enables to execute parts of the architecture on distributed systems
and communicate on various devices due to standarised communication protocol.

Connection can be encrypted with TLS by using certificates on server
and clients.

## Supported devices

* devices running Linux and ``python3``

## System architecture

The system architecture consists of:

``communication.py`` - Communication protocol used in comunication between
server and client instances.

``server.py`` - Used as a service provider for accessing connected devices
informations and estabilish connection with available device services.

``proxy.py`` - Used to manage TCP proxy connection forwarding between user
and device.

``client.py`` - Used as a shell user panel for server communication.

``rdfm-device-client`` - Client for device.

``rdfm-schema-generator`` - Schema generator for server-device communication.

``json_schemas`` - Directory containing valid communication requests. \
Server validates incoming requests with this schema. \
All new instructions definitions should be put here. \
Device requests can be automatically generated using device client.

:::{figure-md} summary
![Architecture summary](images/summary.png)

Summary of the system architecture
:::