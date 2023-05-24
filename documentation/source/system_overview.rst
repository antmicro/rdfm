System overview
===============

System enables to execute parts of the architecture on distributed systems and communicate on various devices due to standarised communication protocol.

Supported devices
-----------------

* devices running Linux and ``python3``

System architecture
-------------------

The system architecture consists of three main parts:

``communication.py`` - Communication protocol used in comunication between server and client instances.

``server.py`` - Used as a service provider for accessing connected devices informations and estabilish connection with available device services.

``client.py`` - Used to communicate with the server, available for devices and users. For users also acting as a shell panel.

.. image::
    images/summary.png
    :alt: Summary of the system architecture
    :align: center
