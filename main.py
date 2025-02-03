import hashlib
import logging
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from typing import Union
import os
import json
import time
import secrets
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()
user_folder_path = 'user_text'
ENGLISH_ALPHABET = 'AaBbCcDdEeFfGHIJKLMNOPQRSTUVWXYZ'
RUSSIAN_ALPHABET = 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЫЬЭЮЯ'
ENGLISH_ALPHABET_SIZE = len(ENGLISH_ALPHABET)
RUSSIAN_ALPHABET_SIZE = len(RUSSIAN_ALPHABET)

@app.post("/")
def read_root():
    return {"message": "Привет, мир!", "method": "POST"}

@app.get("/")
def read_root():
    return {"message": "Привет, мир!", "method": "GET"}

class User(BaseModel):
    login: str
    password: str
    id: Union[int, None] = -1
    token: str

class TextRequest(BaseModel):
    token: str
    text: str = None

class Cipher_Request(BaseModel):
    token: str
    text: str
    key: str

class EditTextRequest(BaseModel):
    token: str
    new_text: str

def find_user_by_login(login: str, user_folder: str):
    try:
        for filename in os.listdir(user_folder):
            with open(os.path.join(user_folder, filename), 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                if user_data["login"] == login:
                    return user_data
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя: {e}")
    return None

def token_search(token: str):
    for filename in os.listdir('users'):
        if filename.endswith(".json"):
            with open(os.path.join('users', filename), 'r') as file:
                user_data = json.load(file)
                if user_data["token"] == token:
                    return user_data["id"], user_data["login"]
    return None, None

def get_user_id_from_token(token: str):
    user_id, user_login = token_search(token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user_id

def check_password_strength(password: str) -> bool:
    if len(password) < 10:
        print("Пароль должен содержать минимум 10 символов.")
        return False
    if not re.search(r'[A-Z]', password):
        print("Пароль должен содержать хотя бы одну заглавную букву.")
        return False
    if not re.search(r'\d', password):
        print("Пароль должен содержать хотя бы одну цифру.")
        return False
    if not re.search(r'[!@#$%^&*()_+={}\[\]:;"\'<>,.?/\\|`~]', password):
        print("Пароль должен содержать хотя бы один специальный символ.")
        return False
    print("Пароль достаточно сложный.")
    return True

def detect_language(text: str) -> str:
    text = text.upper()
    russian_count = sum(1 for char in text if char in RUSSIAN_ALPHABET)
    english_count = sum(1 for char in text if char in ENGLISH_ALPHABET)
    if russian_count > english_count:
        return 'russian'
    elif english_count > russian_count:
        return 'english'
    else:
        raise ValueError("Не удалось определить язык текста")

def text_to_matrix(text: str, n: int, alphabet: str):
    text = text.replace(" ", "").upper()
    text_numbers = [alphabet.index(char) for char in text if char in alphabet]
    while len(text_numbers) % n != 0:
        text_numbers.append(alphabet.index('X' if alphabet == ENGLISH_ALPHABET else 'Е'))
    matrix = np.array(text_numbers).reshape(-1, n).T
    return matrix

def matrix_to_text(matrix: np.ndarray, alphabet: str):
    flat_matrix = matrix.flatten()
    text = ''.join(alphabet[i] for i in flat_matrix)
    return text

def hill_cipher_encrypt(text: str, key_matrix: np.ndarray, alphabet: str):
    n = key_matrix.shape[0]
    text_matrix = text_to_matrix(text, n, alphabet)
    encrypted_matrix = np.dot(key_matrix, text_matrix) % len(alphabet)
    return matrix_to_text(encrypted_matrix, alphabet)

def mod_inverse(matrix: np.ndarray, mod: int) -> np.ndarray:
    det = int(np.round(np.linalg.det(matrix)))
    det_inv = pow(det, -1, mod)
    adjugate = np.round(np.linalg.inv(matrix) * det).astype(int) % mod
    return (det_inv * adjugate) % mod

def hill_cipher_decrypt(text: str, key_matrix: np.ndarray, alphabet: str):
    n = key_matrix.shape[0]
    text_matrix = text_to_matrix(text, n, alphabet)
    inverse_key_matrix = mod_inverse(key_matrix, len(alphabet))
    decrypted_matrix = np.dot(inverse_key_matrix, text_matrix) % len(alphabet)
    return matrix_to_text(decrypted_matrix, alphabet)

@app.post("/create_user")
def register_user(user: User):
    if not check_password_strength(user.password):
        raise HTTPException(status_code=400, detail="Пароль слишком слабый, должен содержать хотя бы 10 символов.")
    user_folder = 'users'
    os.makedirs(user_folder, exist_ok=True)
    if find_user_by_login(user.login, user_folder):
        raise HTTPException(status_code=409, detail="Пользователь с таким логином уже существует.")
    user_id = int(time.time())
    user_token = secrets.token_hex(16)
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    user_data = {
        "id": user_id,
        "login": user.login,
        "password": hashed_password,
        "token": user_token,
    }
    user_filename = f"{user_folder}/user_{user_id}.json"
    with open(user_filename, 'w') as user_file:
        json.dump(user_data, user_file)
    return {"message": "Регистрация прошла успешно!", "token": user_token}

@app.post("/login")
def login(user: User):
    user_folder = 'users'
    try:
        user_data = find_user_by_login(user.login, user_folder)
        if user_data is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
        if hashed_password != user_data["password"]:
            raise HTTPException(status_code=401, detail="Неверный пароль")

        return {"message": "Авторизация прошла успешно", "token": user_data["token"]}

    except Exception as e:
        logging.error(f"Ошибка при авторизации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка на сервере")

@app.post("/add_text")  # Добавление текста
def add_text(text: TextRequest):
    user_id, user_login = token_search(text.token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join(user_folder_path, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    current_time = int(time.time())
    file_name = f"text_{current_time}.txt"
    file_path = os.path.join(user_folder, file_name)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text.text)
    return {"message": "Текст успешно добавлен!"}

@app.post("/delete_last_text")  # Удаление последнего добавленного текста
def delete_last_text(text: TextRequest):
    user_id, user_login = token_search(text.token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join(user_folder_path, str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        raise HTTPException(status_code=404, detail="Нет текстов для удаления")
    last_text_file = sorted(os.listdir(user_folder))[-1]
    last_text_path = os.path.join(user_folder, last_text_file)
    os.remove(last_text_path)
    return {"message": "Последний текст успешно удален!"}

@app.post("/edit_last_text")  # Редактирование последнего добавленного текста
def edit_last_text(request: EditTextRequest):
    user_id, user_login = token_search(request.token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join(user_folder_path, str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        raise HTTPException(status_code=404, detail="Нет текстов для редактирования")
    last_text_file = sorted(os.listdir(user_folder))[-1]
    last_text_path = os.path.join(user_folder, last_text_file)
    with open(last_text_path, "w", encoding="utf-8") as file:
        file.write(request.new_text)
    return {"message": "Последний текст успешно отредактирован!"}

@app.get("/view_texts/{token}")  # Просмотр всех текстов
def view_all_texts(token: str):
    user_id, user_login = token_search(token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join(user_folder_path, str(user_id))
    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        raise HTTPException(status_code=404, detail="Нет текстов для просмотра")
    texts = []
    for index, text_file in enumerate(sorted(os.listdir(user_folder))):
        file_path = os.path.join(user_folder, text_file)
        with open(file_path, "r", encoding="utf-8") as file:
            text_content = file.read()
            texts.append({"index": index + 1, "text": text_content})
    return {"texts": texts}

@app.post("/cipher/encrypt/")  # Запрос на шифрование
def encrypt(data: Cipher_Request):
    print(f"Полученные данные: {data}")
    user_id, user_login = token_search(data.token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join('user_text', str(user_id))
    print(f"Папка пользователя: {user_folder}")
    if not os.path.exists(user_folder):
        raise HTTPException(status_code=404, detail="Папка пользователя не существует")
    if not data.text:
        if not os.path.exists(user_folder) or not os.listdir(user_folder):
            raise HTTPException(status_code=404, detail="Нет доступных текстов для пользователя")
        raise HTTPException(status_code=404, detail="Текст для шифрования не передан")
    try:
        language = detect_language(data.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Не удалось определить язык текста: {str(e)}")
    try:
        key_values = list(map(int, data.key.split()))  # Разделяем строку на числа
        if len(key_values) != 4:  # Проверка, что ключ состоит из 4 чисел
            raise ValueError("Ключ должен содержать 4 числа")
        key_matrix = np.array(key_values).reshape(2, 2)
        print(f"Полученная матрица ключа: \n{key_matrix}")  # Для отладки
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат ключа: {str(e)}")
    if language == 'english':
        alphabet = ENGLISH_ALPHABET
    elif language == 'russian':
        alphabet = RUSSIAN_ALPHABET
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются только английский и русский языки")
    encrypted_text = hill_cipher_encrypt(data.text, key_matrix, alphabet)
    folder_path = "encrypted_text"
    os.makedirs(folder_path, exist_ok=True)
    user_folder = os.path.join(folder_path, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    text_id = int(time.time())
    file_path = os.path.join(user_folder, f"text_{text_id}.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(encrypted_text)
    return {"message": encrypted_text}

@app.get("/view_encrypted_texts/")  # Просмотр всех зашифрованных текстов
def view_encrypted_texts(token: str):
    user_id, user_login = token_search(token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    encrypted_folder_path = os.path.join("encrypted_text", str(user_id))
    if not os.path.exists(encrypted_folder_path) or not os.listdir(encrypted_folder_path):
        raise HTTPException(status_code=404, detail="Нет зашифрованных текстов для просмотра")
    encrypted_texts = []
    for text_file in sorted(os.listdir(encrypted_folder_path)):
        file_path = os.path.join(encrypted_folder_path, text_file)
        with open(file_path, "r", encoding="utf-8") as file:
            encrypted_texts.append({"file": text_file, "text": file.read()})
    return {"texts": encrypted_texts}

@app.post("/cipher/decrypt/")  # Запрос на дешифрование
def decrypt(data: Cipher_Request):
    print(f"Полученные данные: {data}")
    user_id, user_login = token_search(data.token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user_folder = os.path.join('encrypted_text', str(user_id))
    print(f"Папка пользователя: {user_folder}")
    if not os.path.exists(user_folder):
        raise HTTPException(status_code=404, detail="Папка пользователя не существует")
    if not data.text:
        if not os.listdir(user_folder):
            raise HTTPException(status_code=404, detail="Нет доступных зашифрованных текстов для пользователя")
        raise HTTPException(status_code=400, detail="Текст для дешифрования не передан")
    try:
        language = detect_language(data.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Не удалось определить язык текста: {str(e)}")
    try:
        key_values = list(map(int, data.key.split()))
        if len(key_values) != 4:
            raise ValueError("Ключ должен содержать 4 числа")
        key_matrix = np.array(key_values).reshape(2, 2)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат ключа: {str(e)}")
    if language == 'english':
        alphabet = ENGLISH_ALPHABET
    elif language == 'russian':
        alphabet = RUSSIAN_ALPHABET
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются только английский и русский языки")
    decrypted_text = hill_cipher_decrypt(data.text, key_matrix, alphabet)
    return {"message": decrypted_text}

@app.get("/get_user_id/{token}")  # Получение user_id по токену
def get_user_id(token: str):
    user_id, user_login = token_search(token)
    if user_id is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"user_id": user_id}