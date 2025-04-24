from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = Flask(__name__, template_folder='Templates_HTML', static_folder='Static_files')
app.secret_key = os.environ.get("SESSION_SECRET", "devkey")

# Configuration for database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///instance/exams.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize the user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Fix for Heroku or reverse proxies
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialize app before first request (alternative to `before_first_request` for Flask 2.x)
@app.before_first_request
def initialize_app():
    # Place any initialization code you need here
    pass

# Register routes after initialization
from Python_Files.models import *
import Python_Files.routes

if __name__ == "__main__":
    app.run(debug=True)
import os

# Ensure the 'instance' directory exists
os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

@app.before_first_request
def create_tables():
    db.create_all()
