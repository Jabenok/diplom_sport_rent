from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'warning'


def create_app(config_object='config.Config'):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)

    # register routes
    from . import routes  # noqa: E402
    routes.register_routes(app)

    return app
