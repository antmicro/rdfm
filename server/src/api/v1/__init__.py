from flask import Blueprint

import api.v1.devices
import api.v1.packages
import api.v1.groups
import api.v1.update
import api.v1.auth
import api.v1.ws.device


def create_routes() -> Blueprint:
    api_routes: Blueprint = Blueprint("rdfm-server-api-v1", __name__)
    api_routes.register_blueprint(api.v1.devices.devices_blueprint)
    api_routes.register_blueprint(api.v1.packages.packages_blueprint)
    api_routes.register_blueprint(api.v1.groups.groups_blueprint)
    api_routes.register_blueprint(api.v1.update.update_blueprint)
    api_routes.register_blueprint(api.v1.auth.auth_blueprint)
    api_routes.register_blueprint(api.v1.ws.device.device_ws_blueprint)
    return api_routes
