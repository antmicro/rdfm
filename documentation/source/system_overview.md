# System overview

System enables to execute parts of the architecture on distributed systems and communicate on various devices due to standarised communication protocol.

## Supported devices

* devices running Linux and ``python3``

## System architecture

The system architecture consists of:

``communication.py`` - Communication protocol used in comunication between server and client instances.

``server.py`` - Used as a service provider for accessing connected devices informations and estabilish connection with available device services.

``proxy.py`` - Used to manage TCP proxy connection forwarding between user and device.

``client.py`` - Used to communicate with the server, available for devices and users. For users also acting as a shell panel.

``request_schema.json`` - Contains valid communication requests. Server validates incoming requests with this schema.
All new instructions definitions should be put here.

:::{figure-md} summary
![Architecture summary](images/summary.png)

Summary of the system architecture
:::