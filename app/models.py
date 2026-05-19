from . import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    passport_data = db.Column(db.String(10))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price_per_hour = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Available')


class Rental(db.Model):
    __tablename__ = 'rental'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    rent_start = db.Column(db.DateTime, default=datetime.utcnow)
    rent_end = db.Column(db.DateTime)
    is_returned = db.Column(db.Boolean, default=False)

    equipment = db.relationship('Equipment', backref='rental')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
