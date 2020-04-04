from flask import Flask


# Import all blueprints (views)
from views import *

# Import Config
from config import SECRET_KEY

app = Flask(__name__)

app.register_blueprint(home)
app.register_blueprint(hecs_calculator)

app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/home')
def home_page():
    return 'Home Page'


app.run(debug=False, host='192.168.0.249')
