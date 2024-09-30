from flask import current_app

from api.v1.middleware import public_api
from flask import Blueprint, send_from_directory


frontend_blueprint: Blueprint = Blueprint("rdfm-server-frontend", __name__)


@frontend_blueprint.route("/api/static/frontend", defaults={'path': ''})
@frontend_blueprint.route("/api/static/frontend/", defaults={'path': ''})
@frontend_blueprint.route("/api/static/frontend/<path:path>")
@public_api
def get_frontend(path):
    """
    Serve built frontend application from template folder.
    """
    return send_from_directory(current_app.template_folder, "index.html")
