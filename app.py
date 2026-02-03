from datetime import timedelta
from sys import prefix

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from blueprint.main import app as main_blueprint
from blueprint.overlay import app as overlay_blueprint
from blueprint.admin import app as admin_blueprint
from config import *
import ext

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = SQL_CONFIG
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1h
app.permanent_session_lifetime = timedelta(days=3)

ext.db.init_app(app)
ext.csrf.init_app(app)

app.app_context().push()
ext.db.create_all()

app.register_blueprint(main_blueprint)
app.register_blueprint(overlay_blueprint, url_prefix=f"/overlay/{OVERLAY_PATH}")
app.register_blueprint(admin_blueprint, url_prefix=f"/admin/{ADMIN_PATH}")

if __name__ == "__main__":
    app.run(debug=True, port=8080)
