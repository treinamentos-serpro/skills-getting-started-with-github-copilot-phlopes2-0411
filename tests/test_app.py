from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def activity_data(monkeypatch):
    data = deepcopy(app_module.activities)
    monkeypatch.setattr(app_module, "activities", data)
    return data


@pytest.fixture
def client(activity_data):
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_root_redirects_to_homepage(client):
    # Arrange
    follow_redirects = False

    # Act
    response = client.get("/", follow_redirects=follow_redirects)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client, activity_data):
    # Arrange
    expected = activity_data

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected
    assert "Chess Club" in response.json()


def test_signup_adds_participant_and_updates_activity_listing(client, activity_data):
    # Arrange
    email = "new+student@mergington.edu"
    expected = deepcopy(activity_data)
    expected["Chess Club"]["participants"].append(email)

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert client.get("/activities").json() == expected


def test_signup_rejects_existing_participant(client, activity_data):
    # Arrange
    expected = deepcopy(activity_data)
    email = activity_data["Chess Club"]["participants"][0]

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activity_data == expected


def test_signup_rejects_repeated_registration(client, activity_data):
    # Arrange
    email = "new+student@mergington.edu"
    assert client.post(
        "/activities/Chess Club/signup", params={"email": email}
    ).status_code == 200
    expected = deepcopy(activity_data)

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert activity_data == expected
    assert activity_data["Chess Club"]["participants"].count(email) == 1


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_endpoints_reject_unknown_activity(client, activity_data, method):
    # Arrange
    expected = deepcopy(activity_data)

    # Act
    response = client.request(
        method, "/activities/Unknown Club/signup", params={"email": "student@mergington.edu"}
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert activity_data == expected


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_endpoints_require_email(client, activity_data, method):
    # Arrange
    expected = deepcopy(activity_data)

    # Act
    response = client.request(method, "/activities/Chess Club/signup")

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]
    assert activity_data == expected


def test_unregister_removes_participant_and_updates_activity_listing(client, activity_data):
    # Arrange
    email = activity_data["Chess Club"]["participants"][0]
    expected = deepcopy(activity_data)
    expected["Chess Club"]["participants"].remove(email)

    # Act
    response = client.delete("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert client.get("/activities").json() == expected


def test_unregister_rejects_unknown_participant(client, activity_data):
    # Arrange
    expected = deepcopy(activity_data)

    # Act
    response = client.delete(
        "/activities/Chess Club/signup", params={"email": "unknown@mergington.edu"}
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student not signed up for this activity"}
    assert activity_data == expected


def test_unregister_rejects_repeated_removal(client, activity_data):
    # Arrange
    email = activity_data["Chess Club"]["participants"][0]
    assert client.delete(
        "/activities/Chess Club/signup", params={"email": email}
    ).status_code == 200
    expected = deepcopy(activity_data)

    # Act
    response = client.delete("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert activity_data == expected


def test_participant_can_register_again_after_unregistering(client, activity_data):
    # Arrange
    email = activity_data["Chess Club"]["participants"][0]
    expected = deepcopy(activity_data)
    assert client.delete(
        "/activities/Chess Club/signup", params={"email": email}
    ).status_code == 200

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert sorted(activity_data["Chess Club"]["participants"]) == sorted(
        expected["Chess Club"]["participants"]
    )