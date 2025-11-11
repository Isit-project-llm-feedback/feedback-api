import requests

BASE_URL = "http://localhost:5000"


def test_api():
    print("=== Testing Feedback System API ===\n")

    # 1. Test root endpoint
    print("1. Testing root endpoint:")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}, Response: {response.json()}\n")

    # 2. Test registration
    print("2. Testing registration:")
    response = requests.post(f"{BASE_URL}/api/auth/register",
                             json={
                                 'email': 'testuser@company.com',
                                 'password': '123456',
                                 'fullName': 'Тестовый Пользователь',
                                 'department': 'IT'
                             })
    print(f"Status: {response.status_code}, Response: {response.json()}\n")

    # 3. Test login
    print("3. Testing login:")
    response = requests.post(f"{BASE_URL}/api/auth/login",
                             json={
                                 'email': 'user1@company.com',
                                 'password': 'any'
                             })
    print(f"Status: {response.status_code}, Response: {response.json()}\n")

    # 4. Test protected endpoints
    token = 'fake-jwt-token-123'
    headers = {'Authorization': f'Bearer {token}'}

    print("4. Testing surveys endpoint:")
    response = requests.get(f"{BASE_URL}/api/surveys", headers=headers)
    print(f"Status: {response.status_code}, Response: {response.json()}\n")

    print("5. Testing survey results:")
    response = requests.get(f"{BASE_URL}/api/surveys/1/results", headers=headers)
    print(f"Status: {response.status_code}, Response: {response.json()}\n")


if __name__ == "__main__":
    test_api()