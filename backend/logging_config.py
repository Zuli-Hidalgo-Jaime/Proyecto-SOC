# backend/logging_config.py

import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,  # Cambia a DEBUG para más detalle
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
