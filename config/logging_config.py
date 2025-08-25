import logging
import sys

def setup_logging():
    """
    Configures structured logging to standard output.
    In a containerized environment, logs are typically sent to stdout/stderr
    and collected by the container orchestrator.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
        stream=sys.stdout, # Log to standard output
        datefmt='%Y-%m-%dT%H:%M:%S%z'
    )
    
    # You can also customize the log level for noisy libraries if needed
    # logging.getLogger("some_library").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully.")