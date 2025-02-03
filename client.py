import os
import requests
from typing import Union
from pydantic import BaseModel

user_token = None
class User(BaseModel):
    login: str
    password: str
    id: Union[int, None] = -1
    token: str

class TextRequest(BaseModel):
    token: str
    text: str

def send_post(url, data):
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Ошибка на сервере", "status_code": response.status_code}

def send_get(url, data):
    response = requests.get(url, params=data)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Request failed", "status_code": response.status_code}

def get_user_id_from_token(token: str):
    try:
        response = requests.get(f'http://127.0.0.1:8000/get_user_id/{token}')
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("user_id")
        else:
            print("Ошибка при получении user_id: ", response.json())
            return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None

def registration():
    global user_token
    login = input("Введите логин: ")
    password = input("Введите пароль (не менее 10 символов): ")
    if len(password) < 10:
        print("Пароль должен содержать не менее 10 символов.")
        return False
    user_data = User(login=login, password=password, token='token')
    response = requests.post("http://127.0.0.1:8000/create_user", json=user_data.model_dump())
    if response.status_code == 200:
        response_data = response.json()
        user_token = response_data["token"]
        return True
    else:
        print("Ошибка регистрации:", response.json())
        return False

def auth():
    global user_token
    login = input("Введите логин: ")
    password = input("Введите пароль: ")
    user_data = User(login=login, password=password, token='').model_dump()
    response = send_post('http://127.0.0.1:8000/login', data=user_data)
    if "token" in response:
        user_token = response["token"]
        return True
    else:
        print("Ошибка авторизации:", response)
        return False

def add_text():
    global user_token
    text = input("Введите текст, который хотите добавить: ")
    text_data = TextRequest(text=text, token=user_token)
    text_data_dict = text_data.model_dump()  # Получаем словарь
    response = send_post('http://127.0.0.1:8000/add_text', data=text_data_dict)
    if response.get("error"):
        print("Ошибка: ", response.get("error"))
        return False
    print(response["message"])

def view_all_texts():
    global user_token
    data = {
        "token": user_token
    }
    response = requests.get(f'http://127.0.0.1:8000/view_texts/{user_token}')  # Отправляем запрос на сервер
    if response.status_code != 200:
        print("Ошибка: ", response.json())  # Для отладки
        return False
    texts = response.json().get("texts", [])
    if texts:
        print("Все тексты пользователя:")
        for item in texts:
            print(f"{item['index']}. Текст: {item['text']}")
    else:
        print("Нет текстов для отображения.")

def edit_last_text():
    global user_token
    new_text = input("Введите новый текст: ")
    data = {
        "token": user_token,
        "new_text": new_text
    }
    response = send_post('http://127.0.0.1:8000/edit_last_text', data=data)
    if response.get("error"):
        print("Ошибка: ", response.get("error"))
        return False
    print("Текст успешно отредактирован!")

def delete_last_text():
    global user_token
    data = {
        "token": user_token
    }
    response = send_post('http://127.0.0.1:8000/delete_last_text/', data=data)
    if response.get("error"):
        print("Ошибка: ", response.get("error"))
        return False
    print(response["message"])

def encrypt():
    global user_token
    user_id = get_user_id_from_token(user_token)
    user_folder = os.path.join('user_text', str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        print("Нет доступных текстов для шифрования.")
        return False
    text_files = os.listdir(user_folder)
    print(f"Доступные тексты: {text_files}")
    for idx, file in enumerate(text_files):
        print(f"{idx + 1}. {file}")
    try:
        file_choice = int(input("Введите номер текста для шифрования: "))
        if file_choice < 1 or file_choice > len(text_files):
            print("Неверный выбор.")
            return False
    except ValueError:
        print("Ошибка: Введите число.")
        return False
    selected_file = text_files[file_choice - 1]
    with open(os.path.join(user_folder, selected_file), 'r', encoding='utf-8') as f:
        text_to_encrypt = f.read()
    key = input("Введите ключ для шифрования (например '2 3 4 5'): ")
    data = {
        "token": user_token,
        "text": text_to_encrypt,
        "key": key
    }
    response = send_post('http://127.0.0.1:8000/cipher/encrypt/', data=data)
    if response.get("error"):
        print("Ошибка: ", response.get("error"))
        return False
    print("Зашифрованный текст: ", response["message"])

def view_encrypted_texts():
    user_id = get_user_id_from_token(user_token)
    user_folder = os.path.join('encrypted_text', str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        print("Нет доступных зашифрованных текстов.")
        return False
    encrypted_texts = []
    for file_name in os.listdir(user_folder):
        file_path = os.path.join(user_folder, file_name)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_texts.append({
                    'file': file_name,
                    'text': f.read()
                })
    print("Доступные зашифрованные тексты:")
    for idx, encrypted_text in enumerate(encrypted_texts):
        print(f"{idx + 1}. {encrypted_text['file']}")
    try:
        text_choice = int(input("Введите номер текста для просмотра: "))
        if text_choice < 1 or text_choice > len(encrypted_texts):
            print("Неверный выбор.")
            return False
    except ValueError:
        print("Ошибка: Введите число.")
        return False
    selected_text = encrypted_texts[text_choice - 1]
    print(f"Текст из файла {selected_text['file']}:")
    print(selected_text['text'])

def decrypt():
    global user_token
    user_id = get_user_id_from_token(user_token)
    user_folder = os.path.join('encrypted_text', str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        print("Нет доступных зашифрованных текстов.")
        return False
    encrypted_files = os.listdir(user_folder)
    print("Доступные зашифрованные тексты:")
    for idx, file in enumerate(encrypted_files):
        print(f"{idx + 1}. {file}")
    try:
        file_choice = int(input("Введите номер текста для дешифрования: "))
        if file_choice < 1 or file_choice > len(encrypted_files):
            print("Неверный выбор.")
            return False
    except ValueError:
        print("Ошибка: Введите число.")
        return False
    selected_file = encrypted_files[file_choice - 1]
    with open(os.path.join(user_folder, selected_file), 'r', encoding='utf-8') as f:
        encrypted_text = f.read()
    key = input("Введите ключ для дешифрования: ")
    data = {
        "token": user_token,
        "text": encrypted_text,
        "key": key
    }
    response = send_post('http://127.0.0.1:8000/cipher/decrypt/', data=data)
    if response.get("error"):
        print("Ошибка: ", response.get("error"))
        return False
    print("Дешифрованный текст: ", response["message"])


def main_menu():
    is_authenticated = False  # Переменная для отслеживания состояния авторизации/регистрации

    while True:
        if not is_authenticated:  # Если пользователь не авторизован, показываем только регистрацию и авторизацию
            print("Добро пожаловать в приложение для шифрования текста шифром Хилла.")
            print("Перед началом работы с текстом, пожалуйста, зарегистрируйтесь или авторизуйтесь.")
            print("\nМеню:")
            print("1. Регистрация")
            print("2. Авторизация")
            choice = input("Выберите опцию (1-2): ")

            if choice == "1":
                if registration():
                    print("Регистрация успешна!")
                    is_authenticated = True  # После регистрации можно работать с текстами
                else:
                    print("Ошибка регистрации.")

            elif choice == "2":
                if auth():
                    print("Авторизация успешна!")
                    is_authenticated = True  # После авторизации можно работать с текстами
                else:
                    print("Ошибка авторизации.")

            else:
                print("Неверный выбор. Попробуйте снова.")

        else:  # Если пользователь авторизован или зарегистрирован, показываем меню с текстами
            print("\nМеню работы с текстом:")
            print("1. Добавить текст")
            print("2. Просмотреть все добавленные тексты")
            print("3. Редактировать последний добавленный текст")
            print("4. Удалить последний добавленный текст")
            print("5. Зашифровать добавленный текст")
            print("6. Дешифровать текст")
            print("7. Просмотреть зашифрованные тексты")
            print("8. Выход")

            choice = input("Выберите опцию (1-7): ")

            if choice == "1":
                add_text()
            elif choice == "2":
                view_all_texts()
            elif choice == "3":
                edit_last_text()
            elif choice == "4":
                delete_last_text()
            elif choice == "5":
                encrypt()
            elif choice == "6":
                decrypt()
            elif choice == "7":
                view_encrypted_texts()
            elif choice == "8":
                print("Выход из программы.")
                break
            else:
                print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main_menu()