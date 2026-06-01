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
    passport_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_passport(self, passport_data):
        """Hash and store passport data"""
        if passport_data:
            self.passport_hash = generate_password_hash(passport_data)
        else:
            self.passport_hash = None

    def check_passport(self, passport_data):
        """Verify passport data against stored hash"""
        if not self.passport_hash:
            return False
        return check_password_hash(self.passport_hash, passport_data)


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Category {self.name}>'


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='equipment')
    price_per_hour = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Available')

    @property
    def category_name(self):
        return self.category.name if self.category else 'Без категории'


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
