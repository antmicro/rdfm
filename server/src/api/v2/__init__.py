from flask import Blueprint

import api.v2.devices
import api.v2.groups


def create_routes() -> Blueprint:
    api_routes: Blueprint = Blueprint("rdfm-server-api-v2", __name__)
    api_routes.register_blueprint(api.v2.devices.devices_blueprint)
    api_routes.register_blueprint(api.v2.groups.groups_blueprint)
    return api_routes
