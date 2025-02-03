import unittest
import requests
import json

class TestUserRegistration(unittest.TestCase):
    def test_create_user(self):
        self.login = "User1"
        self.password = "StrongPassword.1"
        data = json.dumps({"login": self.login, "password": self.password, "token": 'token1'}).encode('utf-8')
        response = requests.post("http://127.0.0.1:8000/create_user", data=data)
        response_json = response.json()
        self.token = response_json.get("token")
        print("Результат теста регистрации:")
        print(f"Регистрация успешна.", {data})

class TestLoginUser(unittest.TestCase):
    def test_login(self):
        self.login = "User1"
        self.password = "StrongPassword.1"
        data = json.dumps({"login": self.login, "password": self.password, "token": 'token1'}).encode('utf-8')
        response = requests.post("http://127.0.0.1:8000/login", data=data)
        response_json = response.json()
        self.token = response_json.get("token")
        data = json.dumps({"login": self.login, "password": self.password, "token": self.token}).encode('utf-8')
        print("Результат теста авторизации:")
        print(f"Авторизация успешна.", {data})

class TestEncryptText(unittest.TestCase):
    def test_encrypt_text(self):
        self.login = "User1"
        self.password = "StrongPassword.1"
        data = json.dumps({"login": self.login, "password": self.password, "token": 'token'}).encode('utf-8')
        response = requests.post("http://127.0.0.1:8000/cipher/encrypt/", data=data)
        response_json = response.json()
        self.token = response_json.get("token")
        self.text = "Hello"
        self.key = [1, 2, 3, 4]
        data = json.dumps({"text": self.text, "key": self.key, "token": self.token}).encode('utf-8')
        print("Результат текста шифрования:")
        print("Текст успешно зашифрован.")

if __name__ == "__main__":
    unittest.main()
