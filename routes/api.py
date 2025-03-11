import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import text
from app import db
from models import Probe, Job, JobResult, ProbeLog

api_blueprint = Blueprint('api', __name__)

# Configure specific logger for API
logger = logging.getLogger('api')
handler = logging.FileHandler('logs/probe_connections.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

@api_blueprint.route('/api/probe/<api_key>/jobs', methods=['GET'])
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

@api_blueprint.route('/api/results', methods=['POST'])
def submit_job_result():
    """Endpoint for probes to send job results"""
    # Verificar se o probe existe e é ativo
    api_key = request.headers.get('Authorization')
    if not api_key or not api_key.startswith('Bearer '):
        return jsonify({
            'status': 'error',
            'message': 'API key not provided or malformatted'
        }), 401
    
    api_key = api_key.split('Bearer ')[1]
    
    # Carregar o probe completo - precisamos de todos os campos
    probe = Probe.query.filter_by(api_key=api_key, is_active=True).first()
    
    if not probe:
        logger.warning(f"Result submission attempt with invalid API key: {api_key}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid or inactive API key'
        }), 401
    
    # Obter dados dos resultados
    data = request.json
    if not data or 'job_id' not in data or 'success' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Incomplete data: job_id and success are required'
        }), 400
    
    # Verificar se o job existe e pertence ao probe - Precisamos do objeto completo
    job = Job.query.filter_by(id=data['job_id'], probe_id=probe.id).first()
    if not job:
        return jsonify({
            'status': 'error',
            'message': f"Job ID {data['job_id']} not found or does not belong to this probe"
        }), 404
    
    try:
        # Criar o registro de resultado
        result = JobResult(
            job_id=data['job_id'],
            success=data['success'],
            response_time_ms=data.get('response_time_ms'),
            packets_sent=data.get('packets_sent'),
            packets_received=data.get('packets_received'),
            error_message=data.get('error_message'),
            kuma_success=data.get('kuma_success', True),
            kuma_error=data.get('kuma_error')
        )
        db.session.add(result)
        
        # Atualizar o probe diretamente
        current_time = datetime.utcnow()
        probe.last_seen = current_time
        probe.last_connected = current_time
        
        # Registrar o log de conexão
        log = ProbeLog(
            probe_id=probe.id,
            action='submit_result',
            ip_address=request.remote_addr,
            details=f"Result submitted for job {job.name} (ID: {job.id})"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Result received for job {job.name} (ID: {job.id}) from probe {probe.name} (ID: {probe.id})")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error in submit_job_result: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to record result: {str(e)}'
        }), 500
    
    return jsonify({
        'status': 'success',
        'message': 'Result successfully recorded'
    })
