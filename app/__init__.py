from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import inspect, text

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'warning'


def _ensure_category_schema(app):
    from .models import Category

    db.create_all()
    inspector = inspect(db.engine)

    if 'equipment' not in inspector.get_table_names():
        return

    equipment_columns = [column['name'] for column in inspector.get_columns('equipment')]
    if 'category_id' in equipment_columns:
        return

    Category.__table__.create(bind=db.engine, checkfirst=True)

    if 'category' in equipment_columns:
        if db.engine.dialect.name == 'sqlite':
            db.session.execute(text('ALTER TABLE equipment ADD COLUMN category_id INTEGER'))
        else:
            db.session.execute(text('ALTER TABLE equipment ADD COLUMN category_id INT NULL'))

        db.session.commit()

        existing_categories = {}
        rows = db.session.execute(text('SELECT id, category FROM equipment')).fetchall()

        for equipment_id, category_name in rows:
            if not category_name:
                continue
            category_name = category_name.strip()
            if not category_name:
                continue
            if category_name not in existing_categories:
                existing = Category.query.filter_by(name=category_name).first()
                if not existing:
                    existing = Category(name=category_name)
                    db.session.add(existing)
                    db.session.flush()
                existing_categories[category_name] = existing.id

        db.session.commit()

        for equipment_id, category_name in rows:
            if not category_name:
                continue
            category_name = category_name.strip()
            category_id = existing_categories.get(category_name)
            if category_id:
                db.session.execute(
                    text('UPDATE equipment SET category_id = :category_id WHERE id = :equipment_id'),
                    {'category_id': category_id, 'equipment_id': equipment_id},
                )
        db.session.commit()
    else:
        if db.engine.dialect.name == 'sqlite':
            db.session.execute(text('ALTER TABLE equipment ADD COLUMN category_id INTEGER'))
        else:
            db.session.execute(text('ALTER TABLE equipment ADD COLUMN category_id INT NULL'))
        db.session.commit()


def create_app(config_object='config.Config'):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        _ensure_category_schema(app)
        from . import routes
        routes.register_routes(app)

    return app
