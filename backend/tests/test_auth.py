def test_otp_login_creates_user(client):
    res = client.post("/api/auth/otp/request", json={"phone": "+91 98765 43210"})
    assert res.status_code == 200
    otp = res.json()["dev_otp"]
    assert len(otp) == 6

    res = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": otp})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["phone"] == "9876543210"
    assert body["user"]["role"] == "customer"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).json()["phone"] == "9876543210"
    res = client.patch("/api/auth/me", json={"name": "Asha"}, headers=headers)
    assert res.json()["name"] == "Asha"


def test_wrong_otp_and_reuse_are_rejected(client):
    otp = client.post("/api/auth/otp/request", json={"phone": "9876543210"}).json()["dev_otp"]
    wrong = "000000" if otp != "000000" else "111111"
    assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": wrong}).status_code == 400
    assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": otp}).status_code == 200
    # An OTP works only once.
    assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": otp}).status_code == 400


def test_new_otp_invalidates_previous(client):
    first = client.post("/api/auth/otp/request", json={"phone": "9876543210"}).json()["dev_otp"]
    second = client.post("/api/auth/otp/request", json={"phone": "9876543210"}).json()["dev_otp"]
    if first != second:
        assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": first}).status_code == 400
    assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": second}).status_code == 200


def test_invalid_phone(client):
    assert client.post("/api/auth/otp/request", json={"phone": "12345"}).status_code == 422


def test_protected_routes_need_login(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
