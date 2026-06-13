import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_data():
    client.post("/dev/reset")


# --- Active queue filtering ---

def test_active_queue_excludes_approved():
    resp = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in resp.json()["items"]]
    assert "RV-1029" not in ids  # approved


def test_active_queue_excludes_rejected():
    resp = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in resp.json()["items"]]
    assert "RV-1034" not in ids  # rejected


def test_active_queue_excludes_escalated():
    resp = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in resp.json()["items"]]
    assert "RV-1033" not in ids  # escalated


def test_active_queue_includes_active_items():
    resp = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in resp.json()["items"]]
    assert "RV-1024" in ids  # unassigned
    assert "RV-1030" in ids  # in_review


# --- Active queue sorting ---

def test_active_queue_sorted_by_urgency():
    resp = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in resp.json()["items"]]
    expected = [
        "RV-1024",  # high, priority, 2026-04-02T08:15
        "RV-1030",  # high, priority, 2026-04-02T11:55
        "RV-1037",  # high, priority, 2026-04-02T15:30
        "RV-1043",  # high, priority, 2026-04-03T04:55
        "RV-1025",  # high, standard, 2026-04-01T09:30
        "RV-1032",  # high, standard, 2026-04-01T17:20
        "RV-1041",  # high, standard, 2026-04-03T06:30
        "RV-1036",  # high, standard, 2026-04-03T09:10
        "RV-1035",  # medium, priority, 2026-04-02T06:50
        "RV-1040",  # medium, priority, 2026-04-02T13:20
        "RV-1026",  # medium, priority, 2026-04-03T07:20
        "RV-1028",  # medium, standard, 2026-04-01T14:05
        "RV-1039",  # medium, standard, 2026-04-01T19:45
        "RV-1027",  # low, standard, 2026-04-02T10:45
        "RV-1031",  # low, standard, 2026-04-03T08:40
        "RV-1038",  # low, standard, 2026-04-03T11:00
    ]
    assert ids == expected


# --- Claim rules ---

def test_claim_unassigned_succeeds():
    resp = client.post("/review-items/RV-1024/actions", json={"action": "claim", "reviewer": "alex"})
    assert resp.status_code == 200
    item = resp.json()["item"]
    assert item["status"] == "in_review"
    assert item["assigned_reviewer"] == "alex"


def test_claim_in_review_fails():
    resp = client.post("/review-items/RV-1027/actions", json={"action": "claim", "reviewer": "alex"})
    assert resp.status_code == 409


def test_claim_approved_fails():
    resp = client.post("/review-items/RV-1029/actions", json={"action": "claim", "reviewer": "alex"})
    assert resp.status_code == 409


def test_claim_rejected_fails():
    resp = client.post("/review-items/RV-1034/actions", json={"action": "claim", "reviewer": "alex"})
    assert resp.status_code == 409


# --- Approve/reject/escalate rules ---

def test_approve_in_review_succeeds():
    resp = client.post("/review-items/RV-1030/actions", json={"action": "approve", "reviewer": "alex"})
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "approved"


def test_reject_in_review_succeeds():
    resp = client.post("/review-items/RV-1028/actions", json={"action": "reject", "reviewer": "alex"})
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "rejected"


def test_escalate_in_review_succeeds():
    resp = client.post("/review-items/RV-1027/actions", json={"action": "escalate", "reviewer": "alex"})
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "escalated"


def test_approve_unassigned_fails():
    resp = client.post("/review-items/RV-1024/actions", json={"action": "approve", "reviewer": "alex"})
    assert resp.status_code == 409


def test_reject_escalated_fails():
    resp = client.post("/review-items/RV-1033/actions", json={"action": "reject", "reviewer": "alex"})
    assert resp.status_code == 409


# --- Terminal state immutability ---

def test_no_actions_on_approved_item():
    for action in ["claim", "approve", "reject", "escalate"]:
        resp = client.post("/review-items/RV-1029/actions", json={"action": action, "reviewer": "alex"})
        assert resp.status_code == 409, f"{action} should fail on approved item"


def test_no_actions_on_rejected_item():
    for action in ["claim", "approve", "reject", "escalate"]:
        resp = client.post("/review-items/RV-1034/actions", json={"action": action, "reviewer": "alex"})
        assert resp.status_code == 409, f"{action} should fail on rejected item"


# --- Reviewer recording ---

def test_reviewer_recorded_on_claim():
    resp = client.post("/review-items/RV-1024/actions", json={"action": "claim", "reviewer": "alex"})
    assert resp.json()["item"]["assigned_reviewer"] == "alex"


def test_reviewer_recorded_on_approve():
    resp = client.post("/review-items/RV-1030/actions", json={"action": "approve", "reviewer": "alex"})
    assert resp.json()["item"]["assigned_reviewer"] == "alex"


# --- Full workflow ---

def test_claim_then_approve_workflow():
    client.post("/review-items/RV-1024/actions", json={"action": "claim", "reviewer": "alex"})
    resp = client.post("/review-items/RV-1024/actions", json={"action": "approve", "reviewer": "alex"})
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "approved"

    queue = client.get("/review-items", params={"active_only": True})
    ids = [item["id"] for item in queue.json()["items"]]
    assert "RV-1024" not in ids
