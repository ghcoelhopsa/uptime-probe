from datetime import datetime
from app import db
from flask_login import UserMixin
from passlib.hash import pbkdf2_sha256
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

# Removed the login_manager.user_loader decorator that is now in app.py

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Tornando o email opcional
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)
        
    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)
    
    def is_account_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
        
    def __repr__(self):
        return f'<User {self.username}>'

class Probe(db.Model):
    __tablename__ = 'probes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.Text)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_connected = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with jobs
    jobs = db.relationship('Job', backref='probe', lazy='dynamic')
    
    def generate_api_key(self):
        """Generate a unique API key for the probe"""
        import secrets
        self.api_key = secrets.token_hex(32)
        return self.api_key
    
    def __repr__(self):
        return f'<Probe {self.name}>'

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    job_type = db.Column(db.String(20), default='ping', nullable=False)  # Set as 'ping'
    target_host = db.Column(db.String(256), nullable=False)  # Host for ping
    kuma_url = db.Column(db.String(256), nullable=False)  # URL of Uptime Kuma to send results
    interval_seconds = db.Column(db.Integer, default=300, nullable=False)
    timeout_seconds = db.Column(db.Integer, default=10, nullable=False)
    retries = db.Column(db.Integer, default=3, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    probe_id = db.Column(db.Integer, db.ForeignKey('probes.id'), nullable=False)
    
    # Relationship with job results
    results = db.relationship('JobResult', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Job {self.name}> ({self.job_type})'

class JobResult(db.Model):
    __tablename__ = 'job_results'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)
    response_time_ms = db.Column(db.Float, nullable=True)
    packets_sent = db.Column(db.Integer, nullable=True)
    packets_received = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    kuma_success = db.Column(db.Boolean, default=True)  # New column to indicate if the sending to Kuma was successful
    kuma_error = db.Column(db.Text, nullable=True)      # New column to store the error of communication with Kuma
    
    def __repr__(self):
        return f'<JobResult {self.job_id} at {self.timestamp}>'

# Model for probe connection logs
class ProbeLog(db.Model):
    __tablename__ = 'probe_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    probe_id = db.Column(db.Integer, db.ForeignKey('probes.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)  # 'connect', 'heartbeat', 'fetch_jobs'
    ip_address = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    
    # Relationship with the probe
    probe = db.relationship('Probe', backref=db.backref('logs', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<ProbeLog {self.action} - {self.timestamp}>'
