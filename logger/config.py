import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_logger(name:str)->logging.Logger:
    """Get logger
    
    :param name: current file name
    :type name: str"""
    return logging.getLogger(name)