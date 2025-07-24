def test_register_user(client):
    response = client.post(
        "/api/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword",
        },
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
