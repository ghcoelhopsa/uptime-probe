from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from forms.auth import LoginForm, ProfileForm
from datetime import datetime, timedelta
import re

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form, title='Login')
        
        # Check if account is locked
        if user.is_account_locked():
            remaining_time = user.locked_until - datetime.utcnow()
            minutes = remaining_time.seconds // 60
            flash(f'Account is temporarily locked. Try again in {minutes} minutes.', 'danger')
            return render_template('auth/login.html', form=form, title='Login')
        
        # Verify password
        if user.check_password(form.password.data):
            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            db.session.commit()
            
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        else:
            # Increment failed login attempts
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                flash('Too many failed login attempts. Your account has been locked for 15 minutes.', 'danger')
            else:
                remaining_attempts = 5 - user.failed_login_attempts
                flash(f'Invalid password. {remaining_attempts} attempts remaining before account lockout.', 'danger')
            
            db.session.commit()
    
    return render_template('auth/login.html', form=form, title='Login')

@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    # Pre-populate the form with current user data
    if request.method == 'GET':
        form.username.data = current_user.username
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('auth/profile.html', form=form, title='Update Profile')
        
        # Check if username is already taken by another user
        if form.username.data != current_user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user and existing_user.id != current_user.id:
                flash('This username is already in use', 'danger')
                return render_template('auth/profile.html', form=form, title='Update Profile')
        
        # Update user profile
        current_user.username = form.username.data
        
        # Update password if provided
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
            flash('Password updated successfully', 'success')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', form=form, title='Update Profile')

# Route to ensure at least one admin user exists
@auth_blueprint.route('/setup', methods=['GET', 'POST'])
def setup():
    # Check if any user exists
    user_count = User.query.count()
    
    # If a user already exists, redirect to login
    if user_count > 0:
        flash('System is already set up', 'info')
        return redirect(url_for('auth.login'))
    
    form = ProfileForm()
    if form.validate_on_submit():
        # Create the admin user
        user = User(
            username=form.username.data,
            is_admin=True
        )
        user.set_password(form.new_password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Admin user created successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/setup.html', form=form, title='Initial Setup')
