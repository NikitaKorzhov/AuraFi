import pytest
from logger import get_logger

@pytest.mark.parametrize("logger_name", [
    "test_logger",
    "auth_service",
    "db_connection_123",
])
def test_logger_name(logger_name):
    logger=get_logger(logger_name)
    assert logger.name==logger_name, f"Expected logger name to be '{logger_name}', but got '{logger.name}'"