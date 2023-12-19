
RDFM Server API Reference
-------------------------

API Authentication
~~~~~~~~~~~~~~~~~~

By default, the RDFM server expects all API requests to be authenticated.
Depending on the type of the API, this can be either:

* Device Token
* Management Token

In either case, the server expects the token to be passed as part of the request, in the HTTP Authorization header.
An example authenticated request is shown below:

.. sourcecode:: http

   GET /api/v1/groups HTTP/1.1
   Host: rdfm-server:5000
   User-Agent: python-requests/2.31.0
   Accept-Encoding: gzip, deflate
   Accept: */*
   Connection: keep-alive
   Authorization: Bearer token=eyJhbGciOiJSUzI1NiIsInR5cC<...truncated...>RpPonb7-IAsk89YpGayxg

Any request that was not successfully authenticated (because of a missing or otherwise invalid token) will return the 401 Unauthorized status code.
Additionally, in the case of management tokens, if the given token does not provide sufficient access to the requested resource, the request will be rejected with a 403 Forbidden status code.
This can happen if the token does not claim all scopes required by the target endpoint (for example: trying to upload a package using a read-only token).

Error Handling
~~~~~~~~~~~~~~

Should an error occur during the handling of an API request, either because of incorrect request data or other endpoint-specific scenarios, the server will return an error structure containing a user-friendly description of the error.
An example error response is shown below:

.. sourcecode:: json

   {
      "error": "delete failed, the package is assigned to at least one group"
   }


Packages API
~~~~~~~~~~~~

.. autoflask:: rdfm_mgmt_server:create_docs_app()
   :modules: api.v1.packages
   :undoc-static:
   :order: path

Group API
~~~~~~~~~

.. autoflask:: rdfm_mgmt_server:create_docs_app()
   :modules: api.v1.groups
   :undoc-static:
   :order: path

Update API
~~~~~~~~~~

.. autoflask:: rdfm_mgmt_server:create_docs_app()
   :modules: api.v1.update
   :undoc-static:
   :order: path

Device Management API
~~~~~~~~~~~~~~~~~~~~~

.. autoflask:: rdfm_mgmt_server:create_docs_app()
   :modules: api.v1.devices
   :undoc-static:
   :order: path

Device Authorization API
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoflask:: rdfm_mgmt_server:create_docs_app()
   :modules: api.v1.auth
   :undoc-static:
   :order: path
