from scripts._lib.sha import content_hash


def test_hash_is_8_hex_chars():
    assert len(content_hash("anything")) == 8
    assert all(c in "0123456789abcdef" for c in content_hash("anything"))


def test_hash_is_deterministic_and_distinguishes():
    a = content_hash("alpha")
    b = content_hash("alpha")
    c = content_hash("beta")
    assert a == b
    assert a != c
