from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import Job, Probe, JobResult
from forms.jobs import JobForm
import json
from datetime import datetime

jobs_blueprint = Blueprint('jobs', __name__)

@jobs_blueprint.route('/jobs')
@login_required
def list_jobs():
    jobs = Job.query.all()
    return render_template('jobs/list.html', jobs=jobs)

@jobs_blueprint.route('/jobs/new', methods=['GET', 'POST'])
@login_required
def create_job():
    form = JobForm()
    
    # Populate probe select field with probes from the database
    form.probe_id.choices = [
        (probe.id, probe.name) for probe in Probe.query.filter_by(is_active=True).all()
    ]
    
    if form.validate_on_submit():
        job = Job(
            name=form.name.data,
            description=form.description.data,
            job_type='ping',  # Always ping
            target_host=form.target_host.data,
            kuma_url=form.kuma_url.data,
            probe_id=form.probe_id.data,
            interval_seconds=form.interval_seconds.data,
            timeout_seconds=form.timeout_seconds.data,
            retries=form.retries.data,
            is_active=form.is_active.data
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash(f'Job "{job.name}" created successfully!', 'success')
        return redirect(url_for('jobs.list_jobs'))
    
    return render_template('jobs/form.html', form=form, title="New Job")

@jobs_blueprint.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    form = JobForm(job_id=job_id, obj=job)
    
    # Populate probe select field with probes from the database
    form.probe_id.choices = [
        (probe.id, probe.name) for probe in Probe.query.order_by(Probe.name).all()
    ]
    
    if form.validate_on_submit():
        try:
            # Atualizar campos do job sem iniciar uma nova transação
            job.name = form.name.data
            job.description = form.description.data
            # job_type remains as ping
            job.target_host = form.target_host.data
            job.kuma_url = form.kuma_url.data
            job.probe_id = form.probe_id.data
            job.interval_seconds = form.interval_seconds.data
            job.timeout_seconds = form.timeout_seconds.data
            job.retries = form.retries.data
            job.is_active = form.is_active.data
            
            # Commit das alterações
            db.session.commit()
            
            flash(f'Job "{job.name}" was updated successfully!', 'success')
            return redirect(url_for('jobs.list_jobs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating job: {str(e)}', 'danger')
    
    return render_template('jobs/form.html', form=form, job=job, title="Edit Job")

@jobs_blueprint.route('/jobs/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Delete all results associated with the job
    JobResult.query.filter_by(job_id=job.id).delete()
    
    db.session.delete(job)
    db.session.commit()
    
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('jobs.list_jobs'))

@jobs_blueprint.route('/jobs/results/<int:job_id>')
@login_required
def view_results(job_id):
    job = Job.query.get_or_404(job_id)
    results = JobResult.query.filter_by(job_id=job.id).order_by(JobResult.timestamp.desc()).limit(100).all()
    
    return render_template('jobs/results.html', job=job, results=results)

# API Endpoint to receive monitoring results
@jobs_blueprint.route('/api/report', methods=['POST'])
def receive_report():
    data = request.json
    
    # Verify API key
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({'error': 'API key is required'}), 401
    
    probe = Probe.query.filter_by(api_key=api_key).first()
    if not probe:
        return jsonify({'error': 'Invalid API key'}), 401
    
    # Update the last connection timestamp of the probe
    probe.last_connected = datetime.utcnow()
    db.session.commit()
    
    # Process job result
    job_id = data.get('job_id')
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    job = Job.query.filter_by(id=job_id, probe_id=probe.id).first()
    if not job:
        return jsonify({'error': 'Job not found or not associated with this probe'}), 404
    
    # Create job result
    result = JobResult(
        job_id=job.id,
        success=data.get('success', False),
        response_time_ms=data.get('response_time_ms'),
        packets_sent=data.get('packets_sent'),
        packets_received=data.get('packets_received'),
        error_message=data.get('error_message')
    )
    
    db.session.add(result)
    db.session.commit()
    
    return jsonify({'status': 'success'}), 200
