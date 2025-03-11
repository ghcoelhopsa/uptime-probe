from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL
from models import Probe, Job
from wtforms import ValidationError

class JobForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired('This field is required'),
        Length(min=3, max=64, message='Name must be between 3 and 64 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=255, message='Description cannot be more than 255 characters')
    ])
    target_host = StringField('Target Host', validators=[
        DataRequired('This field is required'),
        Length(min=1, max=256, message='Hostname or IP address must be between 1 and 256 characters')
    ], description='Hostname or IP address to ping')
    kuma_url = StringField('Uptime Kuma URL', validators=[
        DataRequired('This field is required'),
        URL()
    ])
    interval_seconds = IntegerField('Interval (seconds)', default=60, validators=[
        DataRequired('This field is required'),
        NumberRange(min=5, message='Minimum interval is 5 seconds')
    ], description='Interval between checks in seconds')
    timeout_seconds = IntegerField('Timeout (seconds)', default=10, validators=[
        DataRequired('This field is required'),
        NumberRange(min=1, max=60, message='Timeout must be between 1 and 60 seconds')
    ], description='Response timeout in seconds')
    retries = IntegerField('Retries', default=0, validators=[
        NumberRange(min=0, max=5, message='Number of retries must be between 0 and 5')
    ], description='Number of attempts before considering a failure')
    is_active = BooleanField('Active', default=True)
    probe_id = SelectField('Probe', coerce=int, validators=[DataRequired('This field is required')])
    submit = SubmitField('Save')
    
    def __init__(self, *args, **kwargs):
        # Extract job_id if provided
        self.job_id = kwargs.pop('job_id', None)
        super(JobForm, self).__init__(*args, **kwargs)
        self.probe_id.choices = [(p.id, p.name) for p in Probe.query.filter_by(is_active=True).all()]
        
    def validate_name(self, name):
        job = Job.query.filter_by(name=name.data).first()
        if job and job.id != self.job_id:
            raise ValidationError('This name is already in use by another job')
