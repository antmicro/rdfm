from flask import Blueprint

import api.v1.devices
import api.v1.packages

def create_routes() -> Blueprint:
    api_routes: Blueprint = Blueprint("rdfm-server-api-v1", __name__)
    api_routes.register_blueprint(api.v1.devices.devices_blueprint)
    api_routes.register_blueprint(api.v1.packages.packages_blueprint)
    return api_routes
