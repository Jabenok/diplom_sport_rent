from datetime import datetime

from app import db
from app.models import User, Equipment, Rental, Category


def register(client, full_name, email, password):
    return client.post(
        '/register',
        data={'full_name': full_name, 'email': email, 'password': password},
        follow_redirects=False,
    )


def login(client, email, password):
    return client.post(
        '/login',
        data={'email': email, 'password': password},
        follow_redirects=False,
    )


def test_register_and_login(client):
    response = register(client, 'Тестовый пользователь', 'test@example.com', 'password123')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    response = login(client, 'test@example.com', 'password123')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')


def test_admin_equipment_forbidden_for_non_admin(client):
    user = User(full_name='Пользователь', email='user@example.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    login_response = login(client, 'user@example.com', 'password')
    assert login_response.status_code == 302

    response = client.get('/admin/equipment')
    assert response.status_code == 403


def test_rent_item_requires_profile_data(client):
    user = User(full_name='Пользователь', email='rent@example.com')
    user.set_password('password')
    db.session.add(user)

    category = Category(name='Безопасность')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Шлем', category=category, price_per_hour=50.0)
    db.session.add(equipment)
    db.session.commit()

    login_response = login(client, 'rent@example.com', 'password')
    assert login_response.status_code == 302

    response = client.get(f'/rent/{equipment.id}', follow_redirects=True)
    assert 'Для аренды необходимо заполнить телефон' in response.get_data(as_text=True)


def test_rent_item_process_validates_dates(client):
    user = User(
        full_name='Арендатор',
        email='order@example.com',
        phone='1234567890',
    )
    user.set_password('password')
    user.set_passport('1234567890')
    db.session.add(user)

    category = Category(name='Теннис')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Ракетка', category=category, price_per_hour=120.0)
    db.session.add(equipment)
    db.session.commit()

    login_response = login(client, 'order@example.com', 'password')
    assert login_response.status_code == 302

    now = datetime.now().replace(second=0, microsecond=0)
    response = client.post(
        '/rent/process',
        data={
            'item_id': equipment.id,
            'rent_start': now.strftime('%Y-%m-%dT%H:%M'),
            'rent_end': now.strftime('%Y-%m-%dT%H:%M'),
        },
        follow_redirects=True,
    )

    assert 'Дата окончания должна быть больше даты начала!' in response.get_data(as_text=True)


def test_admin_equipment_crud(client):
    admin = User(full_name='Админ', email='admin@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    login_response = login(client, 'admin@example.com', 'password')
    assert login_response.status_code == 302

    category = Category(name='Горные')
    db.session.add(category)
    db.session.commit()

    # Create equipment
    response = client.post(
        '/admin/equipment',
        data={'title': 'Ботинки', 'category_id': str(category.id), 'price': '200', 'status': 'Available'},
        follow_redirects=True,
    )
    assert 'Добавлено: Ботинки' in response.get_data(as_text=True)

    equipment = Equipment.query.filter_by(title='Ботинки').first()
    assert equipment is not None
    assert equipment.price_per_hour == 200.0

    # Update equipment
    response = client.post(
        '/admin/equipment',
        data={
            'item_id': equipment.id,
            'title': 'Ботинки PRO',
            'category_id': str(category.id),
            'price': '250',
            'status': 'Available',
        },
        follow_redirects=True,
    )
    assert 'Обновлено: Ботинки PRO' in response.get_data(as_text=True)

    updated_equipment = Equipment.query.get(equipment.id)
    assert updated_equipment.title == 'Ботинки PRO'
    assert updated_equipment.price_per_hour == 250.0

    # Delete equipment
    response = client.get(f'/admin/equipment/delete/{equipment.id}', follow_redirects=True)
    assert 'Удалено: Ботинки PRO' in response.get_data(as_text=True)
    assert Equipment.query.get(equipment.id) is None


def test_admin_equipment_status_change_returns_active_rental(client):
    admin = User(full_name='Админ', email='admin3@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)

    renter = User(full_name='Арендатор', email='renter@example.com', phone='1234567890')
    renter.set_password('password')
    renter.set_passport('1234567890')
    db.session.add(renter)

    category = Category(name='Снаряжение')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Каяк', category=category, price_per_hour=250.0, status='Rented')
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=renter.id, equipment_id=equipment.id, rent_start=datetime.now())
    db.session.add(rental)
    db.session.commit()

    login_response = login(client, 'admin3@example.com', 'password')
    assert login_response.status_code == 302

    response = client.post(
        '/admin/equipment',
        data={
            'item_id': equipment.id,
            'title': 'Каяк',
            'category_id': str(category.id),
            'price': '250',
            'status': 'Available',
        },
        follow_redirects=True,
    )

    assert 'Обновлено: Каяк' in response.get_data(as_text=True)

    updated_equipment = Equipment.query.get(equipment.id)
    updated_rental = Rental.query.get(rental.id)

    assert updated_equipment.status == 'Available'
    assert updated_rental.is_returned is True
    assert updated_rental.rent_end is not None


def test_admin_equipment_status_change_returns_null_active_rental(client):
    admin = User(full_name='Админ', email='admin5@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)

    renter = User(full_name='Арендатор', email='renter2@example.com', phone='1234567890')
    renter.set_password('password')
    renter.set_passport('1234567890')
    db.session.add(renter)

    category = Category(name='Снаряжение2')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Сапоги', category=category, price_per_hour=220.0, status='Rented')
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=renter.id, equipment_id=equipment.id, rent_start=datetime.now(), is_returned=None)
    db.session.add(rental)
    db.session.commit()

    login_response = login(client, 'admin5@example.com', 'password')
    assert login_response.status_code == 302

    response = client.post(
        '/admin/equipment',
        data={
            'item_id': equipment.id,
            'title': 'Сапоги',
            'category_id': str(category.id),
            'price': '220',
            'status': 'Available',
        },
        follow_redirects=True,
    )

    assert 'Обновлено: Сапоги' in response.get_data(as_text=True)

    updated_rental = Rental.query.get(rental.id)
    assert updated_rental.is_returned is True
    assert updated_rental.rent_end is not None


def test_admin_equipment_delete_blocked_when_rental_exists(client):
    admin = User(full_name='Админ', email='admin2@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)

    user = User(full_name='Пользователь', email='user2@example.com')
    user.set_password('password')
    user.phone = '1234567890'
    user.set_passport('1234567890')
    db.session.add(user)

    category = Category(name='Альпинизм')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Кошки', category=category, price_per_hour=120.0)
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=user.id, equipment_id=equipment.id)
    db.session.add(rental)
    db.session.commit()

    login_response = login(client, 'admin2@example.com', 'password')
    assert login_response.status_code == 302

    response = client.get(f'/admin/equipment/delete/{equipment.id}', follow_redirects=True)
    assert 'Нельзя удалить предмет, к которому привязаны активные аренды.' in response.get_data(as_text=True)
    assert Equipment.query.get(equipment.id) is not None


def test_admin_equipment_available_status_allows_deletion_after_active_rental(client):
    admin = User(full_name='Админ', email='admin6@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)

    renter = User(full_name='Пользователь', email='user4@example.com')
    renter.set_password('password')
    renter.phone = '1234567890'
    renter.set_passport('1234567890')
    db.session.add(renter)

    category = Category(name='Велосипеды')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Велосипед', category=category, price_per_hour=200.0, status='Rented')
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=renter.id, equipment_id=equipment.id, rent_start=datetime.now(), is_returned=False)
    db.session.add(rental)
    db.session.commit()

    login_response = login(client, 'admin6@example.com', 'password')
    assert login_response.status_code == 302

    response = client.post(
        '/admin/equipment',
        data={
            'item_id': equipment.id,
            'title': 'Велосипед',
            'category_id': str(category.id),
            'price': '200',
            'status': 'Available',
        },
        follow_redirects=True,
    )
    assert 'Обновлено: Велосипед' in response.get_data(as_text=True)

    response = client.get(f'/admin/equipment/delete/{equipment.id}', follow_redirects=True)
    assert 'Удалено: Велосипед' in response.get_data(as_text=True)
    assert Equipment.query.get(equipment.id) is None


def test_admin_equipment_delete_allowed_after_returned_rental(client):
    admin = User(full_name='Админ', email='admin4@example.com', is_admin=True)
    admin.set_password('password')
    db.session.add(admin)

    user = User(full_name='Пользователь', email='user3@example.com')
    user.set_password('password')
    user.phone = '1234567890'
    user.set_passport('1234567890')
    db.session.add(user)

    category = Category(name='Лыжи')
    db.session.add(category)
    db.session.commit()

    equipment = Equipment(title='Лыжи', category=category, price_per_hour=150.0)
    db.session.add(equipment)
    db.session.commit()

    rental = Rental(user_id=user.id, equipment_id=equipment.id, is_returned=True, rent_end=datetime.now())
    db.session.add(rental)
    db.session.commit()

    login_response = login(client, 'admin4@example.com', 'password')
    assert login_response.status_code == 302

    response = client.get(f'/admin/equipment/delete/{equipment.id}', follow_redirects=True)
    assert 'Удалено: Лыжи' in response.get_data(as_text=True)
    assert Equipment.query.get(equipment.id) is None
