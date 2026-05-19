from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import math

from .models import User, Equipment, Rental
from . import db


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def register_routes(app):
    main = Blueprint('main', __name__)

    @main.route('/', endpoint='index')
    def index():
        items = Equipment.query.all()
        return render_template('index.html', items=items)


    @main.route('/register', methods=['GET', 'POST'], endpoint='register')
    def register():
        if request.method == 'POST':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            password = request.form.get('password')

            if User.query.filter_by(email=email).first():
                flash('Email уже зарегистрирован', 'danger')
                return redirect(url_for('main.register'))

            new_user = User(full_name=full_name, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Регистрация успешна!', 'success')
            return redirect(url_for('main.login'))
        return render_template('register.html')


    @main.route('/login', methods=['GET', 'POST'], endpoint='login')
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('main.index'))
            else:
                flash('Неверный логин или пароль', 'danger')
        return render_template('login.html')


    @main.route('/logout', endpoint='logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('main.index'))


    @main.route('/profile', endpoint='profile')
    @login_required
    def profile():
        user_rentals = Rental.query.filter_by(user_id=current_user.id).all()
        return render_template('profile.html', rentals=user_rentals, now=datetime.now())


    @main.route('/profile/update', methods=['POST'], endpoint='update_profile')
    @login_required
    def update_profile():
        phone = request.form.get('phone')
        passport = request.form.get('passport_data')
        full_name = request.form.get('full_name')

        if full_name:
            current_user.full_name = full_name
        current_user.phone = phone
        current_user.passport_data = passport

        try:
            db.session.commit()
            flash('Данные успешно обновлены!', 'success')
        except Exception:
            db.session.rollback()
            flash('Ошибка при обновлении данных.', 'danger')

        return redirect(url_for('main.profile'))


    @main.route('/admin/equipment', methods=['GET', 'POST'], endpoint='admin_equipment')
    @login_required
    @admin_required
    def admin_equipment():
        if request.method == 'POST':
            item_id = request.form.get('item_id')
            title = request.form.get('title')
            category = request.form.get('category')
            price = request.form.get('price')
            status = request.form.get('status')

            if item_id:
                item = Equipment.query.get(item_id)
                if item:
                    item.title = title
                    item.category = category
                    item.price_per_hour = float(price)
                    item.status = status
                    flash(f'Обновлено: {title}', 'success')
            else:
                new_item = Equipment(
                    title=title,
                    category=category,
                    price_per_hour=float(price),
                    status=status,
                )
                db.session.add(new_item)
                flash(f'Добавлено: {title}', 'success')

            db.session.commit()
            return redirect(url_for('main.admin_equipment'))

        all_items = Equipment.query.all()
        return render_template('admin_equipment.html', items=all_items)


    @main.route('/rent/<int:item_id>', endpoint='rent_item')
    @login_required
    def rent_item(item_id):
        if not current_user.phone or not current_user.passport_data:
            flash('Для аренды необходимо заполнить телефон и паспортные данные в профиле!', 'danger')
            return redirect(url_for('main.profile'))

        item = Equipment.query.get_or_404(item_id)

        if item.status != 'Available':
            flash('Этот предмет сейчас недоступен для аренды.', 'danger')
            return redirect(url_for('main.index'))

        new_rental = Rental(
            user_id=current_user.id,
            equipment_id=item.id,
            rent_start=datetime.now(),
            is_returned=False,
        )

        item.status = 'Rented'

        try:
            db.session.add(new_rental)
            db.session.commit()
            flash(f'Вы успешно арендовали "{item.title}"!', 'success')
        except Exception:
            db.session.rollback()
            flash('Произошла ошибка при оформлении аренды.', 'danger')

        return redirect(url_for('main.profile'))


    @main.route('/rent/process', methods=['POST'], endpoint='rent_item_process')
    @login_required
    def rent_item_process():
        if not current_user.phone or not current_user.passport_data:
            flash('Заполните данные в профиле для аренды!', 'danger')
            return redirect(url_for('main.profile'))

        item_id = request.form.get('item_id')
        start_str = request.form.get('rent_start')
        end_str = request.form.get('rent_end')

        start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
        end_dt = datetime.strptime(end_str, '%Y-%m-%dT%H:%M')

        if end_dt <= start_dt:
            flash('Дата окончания должна быть больше даты начала!', 'danger')
            return redirect(url_for('main.index'))

        item = Equipment.query.get_or_404(item_id)

        if item.status != 'Available':
            flash('Предмет уже занят.', 'danger')
            return redirect(url_for('main.index'))

        diff = end_dt - start_dt
        hours = max(1, math.ceil(diff.total_seconds() / 3600))
        total_cost = hours * item.price_per_hour

        new_rental = Rental(
            user_id=current_user.id,
            equipment_id=item.id,
            rent_start=start_dt,
            rent_end=end_dt,
            is_returned=False,
        )

        item.status = 'Rented'
        db.session.add(new_rental)
        db.session.commit()

        flash(f'Аренда оформлена! Итоговая стоимость: {total_cost} ₽', 'success')
        return redirect(url_for('main.profile'))


    @main.route('/return_item/<int:rental_id>', methods=['POST'], endpoint='process_return')
    @login_required
    def process_return(rental_id):
        rental = Rental.query.get_or_404(rental_id)

        now = datetime.now()
        duration = now - rental.rent_start
        hours = max(1, math.ceil(duration.total_seconds() / 3600))
        final_price = hours * rental.equipment.price_per_hour

        rental.is_returned = True
        rental.rent_end = now
        rental.equipment.status = 'Available'

        db.session.commit()

        return redirect(url_for('main.profile', show_payment=True, amount=final_price))


    @main.route('/admin/return/<int:rental_id>', endpoint='return_item')
    @login_required
    @admin_required
    def return_item(rental_id):
        rental = Rental.query.get_or_404(rental_id)

        rental.is_returned = True
        rental.rent_end = datetime.now()
        rental.equipment.status = 'Available'

        db.session.commit()
        flash(f'Предмет "{rental.equipment.title}" возвращен на склад.', 'success')
        return redirect(url_for('main.admin_equipment'))


    @main.route('/admin/equipment/delete/<int:item_id>', endpoint='delete_equipment')
    @login_required
    @admin_required
    def delete_equipment(item_id):
        item = Equipment.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash(f'Удалено: {item.title}', 'danger')
        return redirect(url_for('main.admin_equipment'))

    app.register_blueprint(main)
