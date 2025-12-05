

import logging
import os
from datetime import datetime
from config.settings import Settings


class Logger:
    
    
    def __init__(self, name: str = 'DocumentEncryption'):
        self.settings = Settings()
        self.logger = logging.getLogger(name)
        
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        
        self.logger.setLevel(getattr(logging, self.settings.LOG_LEVEL))
        
        
        log_dir = self.settings.LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        
        
        log_file = log_dir / f'encryption_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        
        formatter = logging.Formatter(
            self.settings.LOG_FORMAT,
            datefmt=self.settings.LOG_DATE_FORMAT
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        
        self.logger.info(message)
    
    def warning(self, message: str):
        
        self.logger.warning(message)
    
    def error(self, message: str):
        
        self.logger.error(message)
    
    def debug(self, message: str):
        
        self.logger.debug(message)
    
    def critical(self, message: str):
        
        self.logger.critical(message)