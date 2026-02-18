# utils/logger.py
"""
Logger structuré avec rotation de fichiers
"""
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from pathlib import Path
from config.settings import LOGGING_CONFIG

class StructuredLogger:
    """Logger avec sortie JSON structurée"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('cidr_app')
        self.logger.setLevel(getattr(logging, LOGGING_CONFIG['level']))
        
        # Éviter les doublons de handlers
        if not self.logger.handlers:
            # Handler fichier avec rotation
            log_file = LOGGING_CONFIG['file']
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LOGGING_CONFIG['max_bytes'],
                backupCount=LOGGING_CONFIG['backup_count']
            )
            
            # Format JSON
            formatter = logging.Formatter(LOGGING_CONFIG['format'])
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            
            # Handler console pour développement
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def log(self, level: str, event: str, **kwargs):
        """
        Log un événement avec contexte
        
        Args:
            level: Niveau de log (INFO, WARNING, ERROR, CRITICAL)
            event: Type d'événement
            **kwargs: Données contextuelles
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            **kwargs
        }
        
        # Convertir en message JSON
        message = json.dumps(log_data, default=str)
        
        # Logger selon le niveau
        level_map = {
            'DEBUG': self.logger.debug,
            'INFO': self.logger.info,
            'WARNING': self.logger.warning,
            'ERROR': self.logger.error,
            'CRITICAL': self.logger.critical
        }
        
        log_func = level_map.get(level.upper(), self.logger.info)
        log_func(message)
    
    def info(self, event: str, **kwargs):
        """Log niveau INFO"""
        self.log('INFO', event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log niveau WARNING"""
        self.log('WARNING', event, **kwargs)
    
    def error(self, event: str, **kwargs):
        """Log niveau ERROR"""
        self.log('ERROR', event, **kwargs)
    
    def critical(self, event: str, **kwargs):
        """Log niveau CRITICAL"""
        self.log('CRITICAL', event, **kwargs)

# Instance globale
logger = StructuredLogger()
