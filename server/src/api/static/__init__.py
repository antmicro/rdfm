from flask import Blueprint

import api.static.frontend


def create_routes() -> Blueprint:
    api_routes: Blueprint = Blueprint("rdfm-server-api-static", __name__)
    api_routes.register_blueprint(api.static.frontend.frontend_blueprint)
    return api_routes
