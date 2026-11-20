import pytest

from main.models import User


@pytest.mark.django_db
def test_registration_creates_user(client):
    # Подготовка данных
    password = "Test-password-123"

    # Действие
    response = client.post(
        "/api/register",
        data={
            "username": "Тестовый пользователь",
            "email": "test@example.com",
            "phone": "",
            "password": password,
            "password_confirm": password,
            "terms": True,
            "privacy": True,
        },
        content_type="application/json",
    )

    # Проверка результата
    assert response.status_code == 201

    user = User.objects.get(email="test@example.com")
    assert user.name == "Тестовый пользователь"
    assert user.check_password(password)
    assert user.password != password