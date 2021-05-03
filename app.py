from flask import Flask, render_template

# Import all blueprints (views)
from views import *

# Import Config
from config import SECRET_KEY

app = Flask(__name__)

app.register_blueprint(home)
app.register_blueprint(hecs_calculator)

app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/')
def home_page():
    return render_template("home.html")


if __name__ == '__main__':
    app.run()

# PYTHON ANYWHERE WSGI CONFIG FILE SETUP
# # This file contains the WSGI configuration required to serve up your
# # web application at http://<your-username>.pythonanywhere.com/
# # It works by setting the variable 'application' to a WSGI handler of some
# # description.
# #
# # The below has been auto-generated for your Flask project
#
# import sys
#
# # add your project directory to the sys.path
# project_home = '/home/nbart1/Nick_Barty_Website'
# if project_home not in sys.path:
#     sys.path = [project_home] + sys.path
#
# # import flask app but need to call it "application" for WSGI to work
# from app import app as application  # noqa
