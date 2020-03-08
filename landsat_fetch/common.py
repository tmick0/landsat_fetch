
import logging

logging.basicConfig(level=logging.INFO)

__all__ = ["LANDSAT_8_URL", "LOGGER"]

LANDSAT_8_URL = "http://landsat-pds.s3.amazonaws.com/c1/L8/"
LOGGER = logging
