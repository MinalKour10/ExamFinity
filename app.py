from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = Flask(__name__, template_folder='Templates_HTML', static_folder='Static_files')
app.secret_key = os.environ.get("SESSION_SECRET", "devkey")

# Set database URI (either from environment or default to SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///instance/exams.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and CSRF protection
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # This will redirect to login if needed

# User loader for flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Middleware for handling proxy headers (if using a reverse proxy)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Register routes
import Python_Files.routes

# Create all tables before the first request (if they don't exist)
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
