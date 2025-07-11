# tests/backend/test_redis_client.py
import pytest
from backend.utils.redis_client import add_embedding, get_vector

def test_add_and_get_scalar_vector():
    # ----- escalar (1-dim) -----
    add_embedding("unit:key1", [42.0])
    assert get_vector("unit:key1") == pytest.approx([42.0], rel=1e-6)

    # ----- vector completo -----
    demo_vec = [1.1, 2.2, 3.3]
    add_embedding("unit:key2", demo_vec)
    assert get_vector("unit:key2") == pytest.approx(demo_vec, rel=1e-6)

