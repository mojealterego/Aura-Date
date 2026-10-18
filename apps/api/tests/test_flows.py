from __future__ import annotations

from uuid import uuid4


def new_user(client, *, name="Alice", age=27, values=None):
    email = f"{uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={
        "email": email, "password": "secure long password 123",
        "display_name": name, "age": age
    })
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/me", headers=auth).json()
    response = client.put("/api/v1/me", headers=auth, json={
        "display_name": name, "bio": f"About {name}",
        "values": values or ["kindness", "adventure"], "min_age": 18,
        "max_age": 60, "ready": True
    })
    assert response.status_code == 200, response.text
    return auth, me["id"], email


def test_registration_login_privacy_and_validation(client):
    alice, uid, email = new_user(client)
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert "password_hash" not in client.get("/api/v1/me", headers=alice).text
    duplicate = client.post("/api/v1/auth/register", json={
        "email": email, "password": "secure long password 123",
        "display_name": "Alice", "age": 27
    })
    assert duplicate.status_code == 409
    minor = client.post("/api/v1/auth/register", json={
        "email": "minor@example.com", "password": "secure long password 123",
        "display_name": "Minor", "age": 17
    })
    assert minor.status_code == 422
    bad = client.post("/api/v1/auth/token", json={"email": email, "password": "wrong"})
    assert bad.status_code == 401
    good = client.post("/api/v1/auth/token", json={
        "email": email, "password": "secure long password 123"
    })
    assert good.status_code == 200
    assert client.get("/api/v1/me", headers=alice).json()["id"] == uid


def test_daily_introduction_mutual_consent_chat_and_block(client):
    alice, alice_id, _ = new_user(client, name="Alice")
    bob, bob_id, _ = new_user(client, name="Bob")
    response = client.get("/api/v1/introductions/today", headers=alice)
    assert response.status_code == 200, response.text
    intro = response.json()
    assert intro["person"]["id"] == bob_id
    assert client.get("/api/v1/introductions/today", headers=alice).json()["id"] == intro["id"]

    assert client.get("/api/v1/conversations", headers=alice).json() == []
    first = client.post(f"/api/v1/introductions/{intro['id']}/accept", headers=alice)
    assert first.json() == {"mutual": False, "conversation_id": None}
    inbox = client.get("/api/v1/introductions/inbox", headers=bob).json()
    assert any(item["id"] == intro["id"] for item in inbox)
    second = client.post(f"/api/v1/introductions/{intro['id']}/accept", headers=bob)
    assert second.status_code == 200
    conversation_id = second.json()["conversation_id"]
    assert conversation_id

    for i in range(20):
        msg = client.post(f"/api/v1/conversations/{conversation_id}/messages",
                          headers=alice if i % 2 == 0 else bob,
                          json={"content": f"This is a meaningful message number {i}"})
        assert msg.status_code == 201, msg.text
    conversation = client.get(f"/api/v1/conversations/{conversation_id}/messages",
                              headers=bob).json()
    assert conversation["reveal_stage"] == "unlocked"
    assert conversation["meaningful_messages"] == 20
    assert len(conversation["items"]) == 20

    stranger, _, _ = new_user(client, name="Eve")
    assert client.get(f"/api/v1/conversations/{conversation_id}/messages",
                      headers=stranger).status_code == 404
    assert client.post(f"/api/v1/conversations/{conversation_id}/messages",
                       headers=stranger, json={"content": "intrusion"}).status_code == 404

    assert client.post(f"/api/v1/safety/blocks/{bob_id}", headers=alice).status_code == 200
    assert client.get("/api/v1/conversations", headers=bob).json() == []
    assert client.get(f"/api/v1/conversations/{conversation_id}/messages",
                      headers=alice).status_code == 409


def test_match_eligibility_and_reports(client):
    alice, _, _ = new_user(client, name="Alice", age=27)
    bob, bob_id, _ = new_user(client, name="Bob", age=35)
    alice_profile = client.put("/api/v1/me", headers=alice, json={
        "display_name": "Alice", "bio": "", "values": ["kindness"],
        "min_age": 20, "max_age": 30, "ready": True
    })
    assert alice_profile.status_code == 200
    assert client.get("/api/v1/introductions/today", headers=alice).json()["person"] is None
    invalid = client.put("/api/v1/me", headers=alice, json={
        "display_name": "Alice", "bio": "", "values": ["kindness", "kindness"],
        "min_age": 30, "max_age": 20, "ready": True
    })
    assert invalid.status_code == 422
    report = client.post("/api/v1/safety/reports", headers=alice,
                         json={"subject_id": bob_id, "reason": "spam", "details": "Unwanted messages"})
    assert report.status_code == 201
    assert client.post("/api/v1/safety/reports", headers=alice,
                       json={"subject_id": bob_id, "reason": "punish", "details": ""}).status_code == 422


def test_account_deletion_revokes_identity_and_erases_messages(client):
    alice, _, _ = new_user(client, name="Alice")
    bob, _, _ = new_user(client, name="Bob")
    intro = client.get("/api/v1/introductions/today", headers=alice).json()
    client.post(f"/api/v1/introductions/{intro['id']}/accept", headers=alice)
    result = client.post(f"/api/v1/introductions/{intro['id']}/accept", headers=bob)
    convo = result.json()["conversation_id"]
    assert convo
    assert client.post(f"/api/v1/conversations/{convo}/messages",
                       headers=bob, json={"content": "Hello Alice"}).status_code == 201
    deleted = client.delete("/api/v1/me", headers=alice)
    assert deleted.status_code == 204
    assert client.get("/api/v1/me", headers=alice).status_code == 401
    assert client.get("/api/v1/conversations", headers=bob).json() == []
    assert client.get(f"/api/v1/conversations/{convo}/messages", headers=bob).status_code == 404


def test_three_active_conversation_limit_and_release(client):
    from datetime import date, timedelta

    from sqlalchemy.orm import Session
    from aura_api.models import Conversation, Introduction

    owner_auth, owner_id, _ = new_user(client, name="Owner")
    other_ids = [new_user(client, name=f"Other{i}")[1] for i in range(4)]
    with Session(client.app.state.engine) as session:
        for i, other_id in enumerate(other_ids):
            intro = Introduction(
                owner_id=other_id,
                candidate_id=owner_id,
                day=date(2026, 1, 1) + timedelta(days=i),
                owner_accepts=True,
                candidate_accepts=i < 3,
            )
            session.add(intro)
            session.flush()
            if i < 3:
                session.add(Conversation(introduction_id=intro.id))
            else:
                fourth_id = intro.id
        session.commit()
    before = client.post(f"/api/v1/introductions/{fourth_id}/accept", headers=owner_auth)
    assert before.status_code == 409
    existing = client.get("/api/v1/conversations", headers=owner_auth).json()
    assert len(existing) == 3
    close = client.post(
        f"/api/v1/conversations/{existing[0]['id']}/close", headers=owner_auth)
    assert close.status_code == 200
    after = client.post(f"/api/v1/introductions/{fourth_id}/accept", headers=owner_auth)
    assert after.status_code == 200
    assert after.json()["mutual"] is True
    assert len(client.get("/api/v1/conversations", headers=owner_auth).json()) == 3


def test_no_messages_without_mutual_consent(client):
    alice, _, _ = new_user(client, name="Alice")
    bob, _, _ = new_user(client, name="Bob")
    intro = client.get("/api/v1/introductions/today", headers=alice).json()
    assert client.post(f"/api/v1/introductions/{intro['id']}/accept",
                       headers=alice).json()["conversation_id"] is None
    assert client.get("/api/v1/conversations", headers=alice).json() == []
    assert client.get("/api/v1/conversations", headers=bob).json() == []
