import datetime

from app.models import DocumentVersion
from tests.conftest import login_as


def backdate_versions(db_session, minutes: int):
    """Push every existing version's created_at back in time so the
    5-minute autosave-checkpoint gate no longer blocks a new snapshot."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
    db_session.query(DocumentVersion).update({DocumentVersion.created_at: cutoff})
    db_session.commit()


def test_first_content_edit_checkpoints_prior_state(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "Draft"}).json()["id"]

    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v1</p>"})

    versions = client.get(f"/api/documents/{doc_id}/versions").json()
    assert len(versions) == 1
    assert versions[0]["edited_by_name"] == "Alice"


def test_rapid_edits_do_not_flood_version_history(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "Draft"}).json()["id"]

    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v1</p>"})
    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v2</p>"})
    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v3</p>"})

    versions = client.get(f"/api/documents/{doc_id}/versions").json()
    assert len(versions) == 1


def test_edit_after_interval_adds_new_checkpoint(client, users, db_session):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "Draft"}).json()["id"]

    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v1</p>"})
    backdate_versions(db_session, minutes=10)
    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>v2</p>"})

    versions = client.get(f"/api/documents/{doc_id}/versions").json()
    assert len(versions) == 2


def test_restore_reverts_content_and_checkpoints_current_state(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "Draft"}).json()["id"]

    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>original</p>"})
    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>changed</p>"})

    versions = client.get(f"/api/documents/{doc_id}/versions").json()
    original_version_id = versions[-1]["id"]  # oldest = the pre-"original" blank checkpoint

    version_detail = client.get(f"/api/documents/{doc_id}/versions/{original_version_id}").json()
    assert version_detail["content_html"] == "<p></p>"

    restored = client.post(f"/api/documents/{doc_id}/versions/{original_version_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["content_html"] == "<p></p>"

    fetched = client.get(f"/api/documents/{doc_id}").json()
    assert fetched["content_html"] == "<p></p>"

    # Restore force-checkpoints the pre-restore state even though it's < 5 min old.
    versions_after = client.get(f"/api/documents/{doc_id}/versions").json()
    assert len(versions_after) == 2


def test_versions_are_scoped_to_document_access(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "Private"}).json()["id"]
    client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>secret</p>"})

    login_as(client, users["Bob"].id)
    resp = client.get(f"/api/documents/{doc_id}/versions")
    assert resp.status_code == 404
