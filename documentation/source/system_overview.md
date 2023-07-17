# System overview

System enables to execute parts of the architecture on distributed systems
and communicate on various devices due to standarised communication protocol.

Connection can be encrypted with TLS by using certificates on server
and clients.

## Supported devices

* devices running Linux and ``python3``

## System architecture

The system architecture consists of:

``rdfm_mgmt_communication`` - Communication protocol used in comunication between
server and client instances.

``rdfm_mgmt_server`` - Used as a service provider for accessing connected devices
informations and estabilish proxy connection with available device services.

``rdfm_mgmt_client`` - Used as a shell user client for server communication.

``rdfm_mgmt_device`` - Client for device.

``rdfm_schema_generator`` - Schema generator for server-device communication.

``json_schemas`` - Directory containing valid communication requests. \
Server validates incoming requests with this schema. \
All new instructions definitions should be put here. \
Device requests can be automatically generated using device client.

:::{figure-md} summary
![Architecture summary](images/summary.png)

Summary of the system architecture
:::