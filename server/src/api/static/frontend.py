from flask import current_app

from api.v1.middleware import management_read_only_api
from flask import Blueprint, send_from_directory


frontend_blueprint: Blueprint = Blueprint("rdfm-server-frontend", __name__)


@frontend_blueprint.route("/api/static/frontend")
@management_read_only_api
def get_frontend():
    """
    Serve built frontend application from template folder.
    """
    return send_from_directory(current_app.template_folder, "index.html")
