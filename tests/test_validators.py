from app.domain.validators import is_valid_url, normalize_channel_id

def test_is_valid_url():
    assert is_valid_url("https://exemplo.com")
    assert not is_valid_url("htp:/errado")

def test_normalize_channel_id():
    assert normalize_channel_id("UCabc123") == "UCabc123"
    assert normalize_channel_id("canalxyz") == "@canalxyz"
