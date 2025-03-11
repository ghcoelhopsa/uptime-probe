import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import text
from app import db, limiter
from models import Probe, Job, JobResult, ProbeLog

api_blueprint = Blueprint('api', __name__)

# Configure specific logger for API
logger = logging.getLogger('api')
handler = logging.FileHandler('logs/probe_connections.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

@api_blueprint.route('/api/probe/<api_key>/jobs', methods=['GET'])
@limiter.limit("10 per minute")
def get_probe_jobs(api_key):
    """Endpoint for probes to obtain their configured jobs"""
    # Register probe connection
    client_ip = request.remote_addr
    logger.info(f"Probe connection from IP {client_ip} with API key {api_key}")
    
    # Verificar se o probe existe e é ativo 
    probe = Probe.query.filter_by(api_key=api_key, is_active=True).first()
    
    if not probe:
        logger.warning(f"Failed connection attempt with invalid API key: {api_key} from IP {client_ip}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid or inactive API key'
        }), 401
    
    # Obter jobs ativos para este probe
    jobs = Job.query.filter_by(probe_id=probe.id, is_active=True).all()
    
    try:
        # Atualizar o último acesso do probe
        probe.last_seen = datetime.utcnow()
        
        # Registrar o log no banco de dados
        log = ProbeLog(
            probe_id=probe.id,
            action='fetch_jobs',
            ip_address=client_ip,
            details=f"Probe requested configured jobs list"
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error in get_probe_jobs: {str(e)}")
    
    # Formatar jobs para a resposta
    jobs_data = [{
        'id': job.id,
        'name': job.name,
        'job_type': job.job_type,
        'target_host': job.target_host,
        'kuma_url': job.kuma_url,
        'interval_seconds': job.interval_seconds,
        'timeout_seconds': job.timeout_seconds,
        'retries': job.retries
    } for job in jobs]
    
    return jsonify({
        'status': 'success',
        'probe_id': probe.id,
        'probe_name': probe.name,
        'jobs': jobs_data,
        'jobs_count': len(jobs_data)  # Adicionar a contagem de jobs que o probe espera
    })

@api_blueprint.route('/api/probe/<api_key>/heartbeat', methods=['POST'])
@limiter.limit("30 per minute")
def probe_heartbeat(api_key):
    """Endpoint for probes to send heartbeat signals"""
    # Verificar se o probe existe e é ativo
    probe = Probe.query.filter_by(api_key=api_key, is_active=True).first()
    
    client_ip = request.remote_addr
    
    if not probe:
        logger.warning(f"Failed heartbeat attempt with invalid API key: {api_key} from IP {client_ip}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid or inactive API key'
        }), 401
    
    try:
        # Atualizar o último acesso do probe
        probe.last_seen = datetime.utcnow()
        
        # Registrar o log no banco de dados
        log = ProbeLog(
            probe_id=probe.id,
            action='heartbeat',
            ip_address=client_ip,
            details=f"Heartbeat received"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Heartbeat from probe {probe.name} (ID: {probe.id}) from IP {client_ip}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error in probe_heartbeat: {str(e)}")
    
    return jsonify({
        'status': 'success',
        'message': 'Heartbeat received',
        'timestamp': datetime.utcnow().isoformat()
    })

@api_blueprint.route('/api/probe/<api_key>/results', methods=['POST'])
@limiter.limit("100 per minute")
def submit_job_result(api_key):
    """Endpoint for probes to send job results"""
    # Verificar se o probe existe e é ativo
    probe = Probe.query.filter_by(api_key=api_key, is_active=True).first()
    
    if not probe:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or inactive API key'
        }), 401
    
    # Registrar conexão do probe
    probe_log = ProbeLog(
        probe_id=probe.id,
        action="submit_results",
        details="Probe submitted job results"
    )
    db.session.add(probe_log)
    
    # Validar formato dos dados
    data = request.json
    if not data or not isinstance(data, dict) or 'job_id' not in data or 'success' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Invalid data format'
        }), 400
    
    # Procurar job correspondente
    job = Job.query.filter_by(id=data['job_id'], probe_id=probe.id).first()
    if not job:
        return jsonify({
            'status': 'error',
            'message': 'Job not found or not assigned to this probe'
        }), 404
    
    # Criar registro de resultado
    job_result = JobResult(
        job_id=job.id,
        success=data['success'],
        response_time=data.get('response_time'),
        status_code=data.get('status_code'),
        error_message=data.get('error_message'),
        output=data.get('output'),
        kuma_status_code=data.get('kuma_status_code'),
        kuma_response=data.get('kuma_response')
    )
    
    db.session.add(job_result)
    db.session.commit()
    
    # Atualizar timestamp de última execução
    job.last_run = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Job result recorded successfully'
    })
