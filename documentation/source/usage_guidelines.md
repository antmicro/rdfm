Usage
=====

Each user and device client is a separate process.

Running a server
----------------

python server.py

Running a client
----------------

Register a user:
``python client.py user username``

Register a device:
``python client.py device devicename``

Note that client names should not contain whitespaces.

Using a connected client
------------------------

List devices:
``LIST``

Send **proxy** request to a device:
``REQ devicename proxy``

Connecting to the device:

If proxy request was succesful, a message with port to connect to will be sent to the user. 
To connect just use netcat (or similiar program)
nc IP_ADDR PORT