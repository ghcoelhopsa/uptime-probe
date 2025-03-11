from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from models import Probe

class ProbeForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired('This field is required'),
        Length(min=3, max=64, message='Name must be between 3 and 64 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=500, message='Description cannot be more than 500 characters')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')
    
    def __init__(self, *args, **kwargs):
        # Extract probe_id if provided
        self.probe_id = kwargs.pop('probe_id', None)
        super(ProbeForm, self).__init__(*args, **kwargs)
    
    def validate_name(self, name):
        probe = Probe.query.filter_by(name=name.data).first()
        if probe and probe.id != self.probe_id:
            raise ValidationError('This name is already in use by another probe')
