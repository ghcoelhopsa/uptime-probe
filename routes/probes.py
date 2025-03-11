from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Probe, ProbeLog
from forms.probes import ProbeForm

probes_blueprint = Blueprint('probes', __name__, url_prefix='/probes')

@probes_blueprint.route('/')
@login_required
def list_probes():
    probes = Probe.query.all()
    return render_template('probes/list.html', probes=probes, title='Probes')

@probes_blueprint.route('/new', methods=['GET', 'POST'])
@login_required
def create_probe():
    form = ProbeForm()
    if form.validate_on_submit():
        probe = Probe(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        probe.generate_api_key()
        
        db.session.add(probe)
        db.session.commit()
        
        flash(f'Probe {probe.name} created successfully!', 'success')
        return redirect(url_for('probes.list_probes'))
    
    return render_template('probes/form.html', form=form, title='New Probe')

@probes_blueprint.route('/probes/edit/<int:probe_id>', methods=['GET', 'POST'])
@login_required
def edit_probe(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    form = ProbeForm(probe_id=probe_id, obj=probe)
    
    if form.validate_on_submit():
        try:
            # Atualizar campos do probe sem iniciar uma nova transação
            probe.name = form.name.data
            probe.description = form.description.data
            probe.is_active = form.is_active.data
            
            # Commit das alterações
            db.session.commit()
            
            flash(f'Probe "{probe.name}" was updated successfully!', 'success')
            return redirect(url_for('probes.list_probes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating probe: {str(e)}', 'danger')
    
    return render_template('probes/form.html', form=form, probe=probe, title="Edit Probe")

@probes_blueprint.route('/<int:probe_id>/delete', methods=['POST'])
@login_required
def delete_probe(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    
    # Check if probe has any jobs
    if probe.jobs.count() > 0:
        flash(f'Cannot delete probe {probe.name} because it has associated jobs.', 'danger')
        return redirect(url_for('probes.list_probes'))
    
    name = probe.name
    db.session.delete(probe)
    db.session.commit()
    
    flash(f'Probe {name} deleted successfully!', 'success')
    return redirect(url_for('probes.list_probes'))

@probes_blueprint.route('/<int:probe_id>/regenerate-key', methods=['POST'])
@login_required
def regenerate_api_key(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    probe.generate_api_key()
    db.session.commit()
    
    flash(f'API Key for probe {probe.name} has been regenerated successfully.', 'success')
    return redirect(url_for('probes.edit_probe', probe_id=probe.id))

@probes_blueprint.route('/<int:probe_id>/jobs')
@login_required
def probe_jobs(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    return render_template('probes/jobs.html', probe=probe, title=f'Jobs for Probe {probe.name}')

@probes_blueprint.route('/<int:probe_id>/logs')
@login_required
def view_probe_logs(probe_id):
    """Display connection logs for the probe"""
    probe = Probe.query.get_or_404(probe_id)
    
    # Get probe logs, ordered by most recent
    logs = ProbeLog.query.filter_by(probe_id=probe.id).order_by(ProbeLog.timestamp.desc()).all()
    
    return render_template('probes/logs.html', probe=probe, logs=logs)
