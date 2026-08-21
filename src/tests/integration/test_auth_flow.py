import pytest


class TestAuthFlowIntegration:
    @pytest.mark.asyncio
    async def test_register_new_user(self, app_client):
        response = await app_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "New Integration User",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "user_id" in data
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_conflict(self, app_client, test_user):
        response = await app_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "AnotherPassword123!",
                "full_name": "Duplicate User",
            }
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, app_client, test_user):
        response = await app_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Password123!",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, app_client, test_user):
        response = await app_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword!",
            }
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, app_client):
        response = await app_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "Password123!",
            }
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_profile_authenticated(self, app_client, auth_headers, test_user):
        response = await app_client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["role"] == "member"
        assert "monthly_llm_budget" in data

    @pytest.mark.asyncio
    async def test_get_current_user_profile_unauthorized(self, app_client):
        response = await app_client.get("/api/v1/users/me")
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token(self, app_client, user_token):
        response = await app_client.post(
            "/api/v1/auth/refresh",
            json={"token": user_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_logout_authenticated(self, app_client, auth_headers, user_token):
        response = await app_client.post(
            "/api/v1/auth/logout",
            json={"token": user_token},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["detail"]
