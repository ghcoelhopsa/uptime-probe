from flask import Blueprint, render_template
from flask_login import login_required
from app import db
from models import Probe, Job, JobResult
from datetime import datetime, timedelta

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
@login_required
def index():
    # Dashboard data
    probes_count = Probe.query.count()
    active_probes = Probe.query.filter_by(is_active=True).count()
    
    jobs_count = Job.query.count()
    active_jobs = Job.query.filter_by(is_active=True).count()
    
    # Probes that have been offline for more than 5 minutes
    offline_threshold = datetime.utcnow() - timedelta(minutes=5)
    offline_probes = Probe.query.filter(
        db.or_(
            Probe.last_seen < offline_threshold,
            Probe.last_seen == None
        ),
        Probe.is_active == True
    ).all()
    
    return render_template('index.html', 
                           probes_count=probes_count,
                           active_probes=active_probes,
                           jobs_count=jobs_count,
                           active_jobs=active_jobs,
                           offline_probes=offline_probes)
