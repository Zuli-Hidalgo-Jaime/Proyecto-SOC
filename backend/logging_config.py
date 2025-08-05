# backend/logging_config.py
import logging

def setup_logging():
    """
    Configura logging global para el backend.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
