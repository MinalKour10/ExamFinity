from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from Python_Files.models import User
from Python_Files.forms import LoginForm, RegisterForm

# Home page (dashboard)
@app.route('/')
@login_required
def home():
    return render_template('dashboard.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        flash("Invalid credentials", "danger")
    
    return render_template('login.html', form=form)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash("Username already exists, please choose another.", "danger")
            return redirect(url_for('register'))

        # Check if email already exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash("Email is already registered, please choose another.", "danger")
            return redirect(url_for('register'))

        # Create new user and store in DB
        new_user = User(username=form.username.data, email=form.email.data, 
                        password=generate_password_hash(form.password.data))
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# Dashboard (Home page for authenticated users)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
