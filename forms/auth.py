from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired('This field is required')])
    password = PasswordField('Password', validators=[DataRequired('This field is required')])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired('This field is required'),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    current_password = PasswordField('Current Password', validators=[
        DataRequired('This field is required')
    ])
    new_password = PasswordField('New Password', validators=[
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Profile')
