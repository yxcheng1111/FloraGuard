from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  
from flask_login import login_user, login_required, logout_user, current_user
import re


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        email_regex  = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
        pattern = re.compile(email_regex)

        if pattern.match(email):
            user = User.query.filter_by(email=email).first()
            if user:
                if check_password_hash(user.password, password):
                    flash('Logged in successfully!', category='success')
                    login_user(user, remember=True)
                    return redirect(url_for('views.home'))
                else:
                    flash('Incorrect password, try again.', category='error')
            else:
                flash('Email does not exist.', category='error')
        else:
            flash('Invalid email format!', category='error')
        
    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successfully!', category='success')
    return redirect(url_for('auth.login'))

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        email_regex  = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
        phone_regex = "^(01\\d{1}-\\d{7}|01\\d{1}-\\d{8}|01\\d{8}|01\\d{9})$"
        email_pattern = re.compile(email_regex)
        phone_pattern = re.compile(phone_regex)
        if email_pattern.match(email):
            if phone_pattern.match(phone):
                if "-" not in phone:
                    phone = phone[:3] + "-" + phone[3:]
                user = User.query.filter_by(email=email, phone=phone).first()
                if user:
                    user.password = generate_password_hash('12345', method='pbkdf2')
                    db.session.commit()
                    flash('Password has been reset to 12345!', category='success')
                    return redirect(url_for('auth.login'))
                else:
                    flash('Incorrect email or phone number!', category='error')
            else:
                flash('Invalid phone format!', category='error')
        else:
            flash('Invalid email format!', category='error')
    return render_template('reset_password.html',user=current_user)

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        phone_no = request.form.get('phoneNo')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        email_regex  = "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
        phone_regex = "^(01\\d{1}-\\d{7}|01\\d{1}-\\d{8}|01\\d{8}|01\\d{9})$"
        email_pattern = re.compile(email_regex)
        phone_pattern = re.compile(phone_regex)

        if email_pattern.match(email):
            if phone_pattern.match(phone_no):
                user = User.query.filter_by(email=email).first()
                if user:
                    flash('Email already exists.', category='error')
                elif password1 != password2:
                    flash('Passwords don\'t match.', category='error')
                else:
                    if "-" not in phone_no:
                        phone_no = phone_no[:3] + "-" + phone_no[3:]
                    new_user = User(email=email, password=generate_password_hash(
                        password1, method='pbkdf2'), phone=phone_no)
                    db.session.add(new_user)
                    db.session.commit()
                    login_user(new_user, remember=True)
                    flash('Account created!', category='success')
                    return redirect(url_for('views.home'))
            else:
                flash('Invalid phone format!', category='error')
        else:
            flash('Invalid email format!', category='error')
    return render_template("sign_up.html", user=current_user)


