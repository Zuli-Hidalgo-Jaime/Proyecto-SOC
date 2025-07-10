# tests/backend/test_redis_client.py
import pytest
from backend.utils.redis_client import set_key, get_key, set_vector, get_vector

def test_set_and_get_key():
    set_key("saludo", "hola mundo")
    resultado = get_key("saludo")
    assert resultado == "hola mundo"

def test_set_and_get_vector():
    vector_demo = [1.1, 2.2, 3.3]
    set_vector("mi_vector", vector_demo)
    resultado = get_vector("mi_vector")
    assert resultado == vector_demo

