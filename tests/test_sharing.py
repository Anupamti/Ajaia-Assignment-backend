from tests.conftest import login_as


def test_owner_can_access_and_stranger_cannot(client, users):
    alice, bob = users["Alice"], users["Bob"]

    login_as(client, alice.id)
    create_resp = client.post("/api/documents", json={"title": "Alice's plan"})
    assert create_resp.status_code == 201
    doc_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_owner"] is True

    login_as(client, bob.id)
    stranger_resp = client.get(f"/api/documents/{doc_id}")
    assert stranger_resp.status_code == 404


def test_sharing_grants_access_and_marks_not_owner(client, users):
    alice, bob = users["Alice"], users["Bob"]

    login_as(client, alice.id)
    doc_id = client.post("/api/documents", json={"title": "Shared doc"}).json()["id"]
    share_resp = client.post(f"/api/documents/{doc_id}/share", json={"user_id": str(bob.id)})
    assert share_resp.status_code == 200
    assert {u["name"] for u in share_resp.json()["shared_with"]} == {"Bob"}

    login_as(client, bob.id)
    bob_resp = client.get(f"/api/documents/{doc_id}")
    assert bob_resp.status_code == 200
    assert bob_resp.json()["is_owner"] is False

    list_resp = client.get("/api/documents")
    ids_owned = [d["id"] for d in list_resp.json() if d["is_owner"]]
    ids_shared = [d["id"] for d in list_resp.json() if not d["is_owner"]]
    assert doc_id in ids_shared
    assert doc_id not in ids_owned


def test_non_owner_cannot_share_or_edit_beyond_access(client, users):
    alice, bob, carol = users["Alice"], users["Bob"], users["Carol"]

    login_as(client, alice.id)
    doc_id = client.post("/api/documents", json={"title": "Private"}).json()["id"]
    client.post(f"/api/documents/{doc_id}/share", json={"user_id": str(bob.id)})

    login_as(client, bob.id)
    forbidden_share = client.post(f"/api/documents/{doc_id}/share", json={"user_id": str(carol.id)})
    assert forbidden_share.status_code == 403

    login_as(client, carol.id)
    carol_resp = client.get(f"/api/documents/{doc_id}")
    assert carol_resp.status_code == 404


def test_requires_login(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 401
