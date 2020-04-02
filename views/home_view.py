from flask import render_template, Blueprint

blueprint_name = "home"

home = Blueprint(blueprint_name, __name__)


@home.route(f'/{blueprint_name}')
def _home():
    return render_template(f"{blueprint_name}.html")
