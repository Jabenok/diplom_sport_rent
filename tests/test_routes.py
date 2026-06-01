from datetime import datetime

from app import db
from app.models import User, Equipment, Category


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
