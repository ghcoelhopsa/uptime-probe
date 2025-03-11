from datetime import datetime, timedelta
from app import db
from models import JobResult, ProbeLog
import logging
from flask import current_app
import time

logger = logging.getLogger('uptime-monitor')

def cleanup_old_logs():
    """Remove logs older than 24 hours"""
    try:
        start_time = time.time()
        # Verificar se estamos em um contexto de aplicação
        if not current_app:
            logger.error("No application context available for log cleanup")
            return 0, 0
        
        # Calculate the cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Usar transação explicitamente para melhor controle
        db.session.begin()
        
        # Fazer a remoção por lotes para reduzir o impacto no banco de dados
        # Primeiro, obter os IDs dos registros que serão excluídos
        job_results_ids = [r.id for r in JobResult.query.filter(JobResult.timestamp < cutoff_time).limit(10000).all()]
        probe_logs_ids = [p.id for p in ProbeLog.query.filter(ProbeLog.timestamp < cutoff_time).limit(10000).all()]
        
        # Remover em lotes para evitar sobrecarga do banco de dados
        job_results_count = 0
        probe_logs_count = 0
        
        # Remover JobResults em lotes de 1000
        batch_size = 1000
        for i in range(0, len(job_results_ids), batch_size):
            batch = job_results_ids[i:i+batch_size]
            if batch:
                JobResult.query.filter(JobResult.id.in_(batch)).delete(synchronize_session='fetch')
                job_results_count += len(batch)
                
                # Fazer commit a cada lote para liberar a transação
                db.session.commit()
                db.session.begin()
        
        # Remover ProbeLogs em lotes de 1000
        for i in range(0, len(probe_logs_ids), batch_size):
            batch = probe_logs_ids[i:i+batch_size]
            if batch:
                ProbeLog.query.filter(ProbeLog.id.in_(batch)).delete(synchronize_session='fetch')
                probe_logs_count += len(batch)
                
                # Fazer commit a cada lote para liberar a transação
                db.session.commit()
                db.session.begin()
        
        # Commit final (se necessário)
        db.session.commit()
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Cleaned up {job_results_count} job results and {probe_logs_count} probe logs older than 24 hours in {duration:.2f} seconds")
        return job_results_count, probe_logs_count
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore errors during rollback
        return 0, 0
