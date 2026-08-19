import io

from tests.conftest import login_as


def test_create_rename_and_edit_content_persists(client, users):
    alice = users["Alice"]
    login_as(client, alice.id)

    doc = client.post("/api/documents", json={"title": "Draft"}).json()
    doc_id = doc["id"]

    rename = client.patch(f"/api/documents/{doc_id}", json={"title": "Final title"})
    assert rename.status_code == 200
    assert rename.json()["title"] == "Final title"

    edit = client.patch(
        f"/api/documents/{doc_id}",
        json={"content_html": "<h1>Hi</h1><p><strong>Bold</strong> text</p><ul><li>one</li></ul>"},
    )
    assert edit.status_code == 200

    fetched = client.get(f"/api/documents/{doc_id}").json()
    assert fetched["title"] == "Final title"
    assert "<strong>Bold</strong>" in fetched["content_html"]
    assert "<h1>Hi</h1>" in fetched["content_html"]


def test_update_rejects_empty_title(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "x"}).json()["id"]

    resp = client.patch(f"/api/documents/{doc_id}", json={"title": "   "})
    assert resp.status_code == 400


def test_content_html_is_sanitized(client, users):
    login_as(client, users["Alice"].id)
    doc_id = client.post("/api/documents", json={"title": "x"}).json()["id"]

    client.patch(
        f"/api/documents/{doc_id}",
        json={"content_html": "<p>safe</p><script>alert(1)</script>"},
    )
    fetched = client.get(f"/api/documents/{doc_id}").json()
    assert "<script>" not in fetched["content_html"]
    assert "safe" in fetched["content_html"]


def test_upload_txt_creates_document(client, users):
    login_as(client, users["Alice"].id)
    file_content = b"Hello world\nSecond line"
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "notes"
    assert "Hello world" in body["content_html"]


def test_upload_rejects_unsupported_extension(client, users):
    login_as(client, users["Alice"].id)
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_nonexistent_document_returns_404(client, users):
    login_as(client, users["Alice"].id)
    resp = client.get("/api/documents/99999")
    assert resp.status_code == 404
