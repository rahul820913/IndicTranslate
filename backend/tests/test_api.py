from .conftest import signup

BODY = {"text": "How are you?", "source_language": "eng_Latn", "target_language": "hin_Deva"}


def test_health_and_languages(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    codes = [l["code"] for l in client.get("/api/v1/languages").json()]
    assert "hin_Deva" in codes and "eng_Latn" in codes


def test_translate_and_cache(client):
    first = client.post("/api/v1/translations", json={**BODY, "text": "Cache me"}).json()
    second = client.post("/api/v1/translations", json={**BODY, "text": "Cache me"}).json()
    assert first["cached"] is False and second["cached"] is True
    assert first["translated_text"] == second["translated_text"]


def test_validation_errors(client):
    bad_pair = {**BODY, "source_language": "hin_Deva", "target_language": "tam_Taml"}
    assert client.post("/api/v1/translations", json=bad_pair).status_code == 400
    assert client.post("/api/v1/translations", json={**BODY, "text": ""}).status_code == 422
    assert client.post("/api/v1/translations", json={**BODY, "target_language": "xx"}).status_code == 400


def test_history_requires_auth(client):
    assert client.get("/api/v1/translations").status_code == 401


def test_save_history_delete_and_isolation(client):
    alice = signup(client, "alice@example.com")
    bob = signup(client, "bob@example.com")

    saved = client.post("/api/v1/translations", json={**BODY, "save": True}, headers=alice).json()
    tid = saved["id"]
    assert tid

    assert client.get("/api/v1/translations", headers=alice).json()["total"] == 1
    assert client.get("/api/v1/translations", headers=bob).json()["total"] == 0
    assert client.get(f"/api/v1/translations/{tid}", headers=bob).status_code == 404
    assert client.delete(f"/api/v1/translations/{tid}", headers=bob).status_code == 404

    assert client.post("/api/v1/feedback", json={"translation_id": tid, "rating": 5}, headers=alice).status_code == 201
    assert client.delete(f"/api/v1/translations/{tid}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/translations/{tid}", headers=alice).status_code == 404


def test_login(client):
    signup(client, "carol@example.com")
    ok = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "password123"})
    bad = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "wrong-password"})
    assert ok.status_code == 200 and bad.status_code == 401
