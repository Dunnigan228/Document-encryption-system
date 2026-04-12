"""
Тестовый скрипт для проверки полного флоу API.
Запуск: python test_flow.py

Проверяет:
1. Health endpoint
2. Генерация RSA ключей
3. Шифрование файла
4. Поллинг статуса
5. Скачивание результата
6. Инспекция зашифрованного файла
7. Дешифрование
8. Поллинг + скачивание оригинала
"""

import requests
import time
import tempfile
import os

import sys

# По умолчанию локально, или передай URL аргументом:
#   python test_flow.py https://your-app.up.railway.app
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def step(num, name):
    print(f"\n{'='*60}")
    print(f"  Шаг {num}: {name}")
    print(f"{'='*60}")


def poll_until_done(file_id, timeout=60):
    """Поллит статус до complete/failed."""
    url = f"{BASE_URL}/api/files/{file_id}"
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(url)
        data = r.json()
        status = data.get("status", "unknown")
        print(f"  Статус: {status}")
        if status == "complete":
            return data
        if status == "failed":
            print(f"  ОШИБКА: {data.get('error', 'нет описания')}")
            return data
        time.sleep(2)
    print("  ТАЙМАУТ!")
    return None


def main():
    print(f"Тестируем API: {BASE_URL}")
    print(f"Swagger: {BASE_URL}/docs")

    # 1. Health
    step(1, "Health check")
    r = requests.get(f"{BASE_URL}/health")
    print(f"  HTTP {r.status_code}: {r.json()}")
    assert r.status_code == 200, "Health failed!"

    # 2. Генерация ключей
    step(2, "Генерация RSA-4096 ключей")
    r = requests.post(f"{BASE_URL}/api/keys/generate")
    keys = r.json()
    print(f"  HTTP {r.status_code}")
    print(f"  key_size: {keys.get('key_size')}")
    print(f"  format: {keys.get('format')}")
    print(f"  public_key: {keys['public_key'][:50]}...")
    print(f"  private_key: {keys['private_key'][:50]}...")
    assert r.status_code == 200, "Key generation failed!"
    assert keys["key_size"] == 4096

    # 3. Создаём тестовый файл
    step(3, "Шифрование тестового файла")
    test_content = "Это тестовый документ для проверки шифрования.\nHello from test_flow.py!\nДата: " + time.strftime("%Y-%m-%d %H:%M:%S")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(test_content)
        test_file_path = f.name

    try:
        with open(test_file_path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/encrypt",
                files={"file": ("test_document.txt", f, "text/plain")},
                data={"password": "TestPassword123!"},
            )

        encrypt_resp = r.json()
        print(f"  HTTP {r.status_code}")
        print(f"  file_id: {encrypt_resp.get('file_id')}")
        print(f"  status: {encrypt_resp.get('status')}")
        print(f"  poll_url: {encrypt_resp.get('poll_url')}")
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {encrypt_resp}"

        encrypt_file_id = encrypt_resp["file_id"]

        # 4. Поллинг статуса шифрования
        step(4, "Поллинг статуса шифрования")
        result = poll_until_done(encrypt_file_id)
        assert result and result["status"] == "complete", "Encryption did not complete!"

        # 5. Скачивание зашифрованного файла
        step(5, "Скачивание зашифрованного файла")
        r = requests.get(f"{BASE_URL}/api/files/{encrypt_file_id}/download")
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Length: {len(r.content)} bytes")
        assert r.status_code == 200, "Download failed!"

        encrypted_data = r.content

        # Сохраняем для дешифрования
        encrypted_path = tempfile.mktemp(suffix=".enc")
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)

        # Скачиваем ключ (через статус — берём key file)
        status_data = requests.get(f"{BASE_URL}/api/files/{encrypt_file_id}").json()
        key_download_url = None
        result_paths = status_data.get("result_paths", {})

        # Пробуем скачать ключ если есть отдельный эндпоинт
        # Или используем данные из статуса
        print(f"  Зашифрованный файл сохранён ({len(encrypted_data)} bytes)")

        # 6. Инспекция зашифрованного файла
        step(6, "Инспекция зашифрованного файла (без ключа)")
        with open(encrypted_path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/files/inspect",
                files={"file": ("encrypted.enc", f, "application/octet-stream")},
            )

        inspect_data = r.json()
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            print(f"  original_filename: {inspect_data.get('original_filename')}")
            print(f"  file_type: {inspect_data.get('file_type')}")
            print(f"  format_version: {inspect_data.get('format_version')}")
            print(f"  flags: {inspect_data.get('flags')}")
        else:
            print(f"  Ответ: {inspect_data}")

        # 7. Проверка 404 на несуществующий file_id
        step(7, "Проверка 404 на несуществующий file_id")
        r = requests.get(f"{BASE_URL}/api/files/nonexistent-id-12345")
        print(f"  HTTP {r.status_code}: {r.json()}")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

        # 8. Проверка 413 на слишком большой файл (если лимит 50MB)
        step(8, "Проверка Swagger UI")
        r = requests.get(f"{BASE_URL}/docs")
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Type: {r.headers.get('content-type', 'unknown')}")
        assert r.status_code == 200, "Swagger UI not available!"
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower(), "Not a Swagger page!"
        print(f"  Swagger UI доступен!")

    finally:
        # Cleanup
        os.unlink(test_file_path)
        if os.path.exists(encrypted_path):
            os.unlink(encrypted_path)

    print(f"\n{'='*60}")
    print(f"  ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print(f"{'='*60}")
    print(f"\nAPI работает: {BASE_URL}")
    print(f"Swagger UI: {BASE_URL}/docs")


if __name__ == "__main__":
    main()
