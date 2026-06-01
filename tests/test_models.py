from app.models import User, Equipment, Rental, Category
from app import db


def test_user_password_hash_and_check():
    user = User(full_name='Тест', email='test@example.com')
    user.set_password('password123')

    assert user.password_hash != 'password123'
    assert user.check_password('password123')
    assert not user.check_password('wrong-password')


def test_rental_equipment_relationship(app):
    user = User(full_name='Тест', email='user@example.com')
    user.set_password('secret')
    db.session.add(user)

    category = Category(name='Велоспорт')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Велосипед', category=category, price_per_hour=150.0)
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=user.id, equipment_id=equipment.id)
    rental.equipment = equipment
    db.session.add(rental)
    db.session.commit()

    assert rental.equipment == equipment
    assert equipment.rental[0] == rental
