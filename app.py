from flask import Flask


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
    return 'Home Page'


if __name__ == '__main__':
    app.run()