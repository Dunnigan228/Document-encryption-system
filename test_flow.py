"""
Тестовый скрипт для проверки полного флоу API.
Запуск: python test_flow.py [URL]

Проверяет полный цикл:
1. Health endpoint
2. Генерация RSA ключей
3. Шифрование файла → 202
4. Поллинг статуса шифрования
5. Скачивание зашифрованного файла (?type=encrypted)
6. Скачивание key bundle (?type=key)
7. Инспекция зашифрованного файла
8. Дешифрование (encrypted + key_bundle) → 202
9. Поллинг статуса дешифрования
10. Скачивание оригинала + проверка содержимого
11. Проверка 404 на несуществующий file_id
12. Проверка Swagger UI
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

    temp_files = []  # для cleanup

    try:
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

        # 3. Шифрование тестового файла
        step(3, "Шифрование тестового файла")
        test_content = "Это тестовый документ для проверки шифрования.\nHello from test_flow.py!\nДата: " + time.strftime("%Y-%m-%d %H:%M:%S")

        test_file_path = tempfile.mktemp(suffix=".txt")
        temp_files.append(test_file_path)
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_content)

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
        step(5, "Скачивание зашифрованного файла (?type=encrypted)")
        r = requests.get(f"{BASE_URL}/api/files/{encrypt_file_id}/download", params={"type": "encrypted"})
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Length: {len(r.content)} bytes")
        assert r.status_code == 200, f"Download encrypted failed: {r.text}"

        encrypted_path = tempfile.mktemp(suffix=".enc")
        temp_files.append(encrypted_path)
        with open(encrypted_path, "wb") as f:
            f.write(r.content)
        print(f"  Сохранён: {encrypted_path}")

        # 6. Скачивание key bundle
        step(6, "Скачивание key bundle (?type=key)")
        r = requests.get(f"{BASE_URL}/api/files/{encrypt_file_id}/download", params={"type": "key"})
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Length: {len(r.content)} bytes")
        assert r.status_code == 200, f"Download key failed: {r.text}"

        key_path = tempfile.mktemp(suffix=".key")
        temp_files.append(key_path)
        with open(key_path, "wb") as f:
            f.write(r.content)

        # Проверяем что это валидный JSON
        import json
        key_data = json.loads(r.content)
        print(f"  Формат: JSON")
        print(f"  Поля: {', '.join(key_data.keys())}")
        assert "aes_key" in key_data or "encrypted" in key_data, "Key bundle missing expected fields!"
        print(f"  Key bundle валидный!")

        # 7. Инспекция зашифрованного файла
        step(7, "Инспекция зашифрованного файла (без ключа)")
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

        # 8. Дешифрование (encrypted_file + key_bundle)
        step(8, "Дешифрование (encrypted + key bundle)")
        with open(encrypted_path, "rb") as enc_f, open(key_path, "rb") as key_f:
            r = requests.post(
                f"{BASE_URL}/api/decrypt",
                files={
                    "encrypted_file": ("test_document.txt.enc", enc_f, "application/octet-stream"),
                    "key_file": ("test_document.txt.key", key_f, "application/json"),
                },
                data={"password": "TestPassword123!"},
            )

        decrypt_resp = r.json()
        print(f"  HTTP {r.status_code}")
        print(f"  file_id: {decrypt_resp.get('file_id')}")
        print(f"  status: {decrypt_resp.get('status')}")
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {decrypt_resp}"

        decrypt_file_id = decrypt_resp["file_id"]

        # 9. Поллинг статуса дешифрования
        step(9, "Поллинг статуса дешифрования")
        result = poll_until_done(decrypt_file_id)
        assert result and result["status"] == "complete", f"Decryption failed: {result}"

        # 10. Скачивание оригинала + проверка
        step(10, "Скачивание расшифрованного файла + проверка")
        r = requests.get(f"{BASE_URL}/api/files/{decrypt_file_id}/download")
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Length: {len(r.content)} bytes")
        assert r.status_code == 200, f"Download decrypted failed: {r.text}"

        decrypted_content = r.content.decode("utf-8")
        print(f"  Содержимое: {decrypted_content[:80]}...")

        if decrypted_content == test_content:
            print(f"  СОВПАДАЕТ с оригиналом!")
        else:
            print(f"  ВНИМАНИЕ: содержимое отличается!")
            print(f"  Оригинал ({len(test_content)} chars): {test_content[:50]}...")
            print(f"  Получено ({len(decrypted_content)} chars): {decrypted_content[:50]}...")
            assert False, "Decrypted content does not match original!"

        # 11. Проверка 404
        step(11, "Проверка 404 на несуществующий file_id")
        r = requests.get(f"{BASE_URL}/api/files/nonexistent-id-12345")
        print(f"  HTTP {r.status_code}: {r.json()}")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

        # 12. Swagger UI
        step(12, "Проверка Swagger UI")
        r = requests.get(f"{BASE_URL}/docs")
        print(f"  HTTP {r.status_code}")
        print(f"  Content-Type: {r.headers.get('content-type', 'unknown')}")
        assert r.status_code == 200, "Swagger UI not available!"
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower(), "Not a Swagger page!"
        print(f"  Swagger UI доступен!")

    finally:
        for path in temp_files:
            if os.path.exists(path):
                os.unlink(path)

    print(f"\n{'='*60}")
    print(f"  ВСЕ 12 ПРОВЕРОК ПРОЙДЕНЫ!")
    print(f"  Полный цикл: encrypt → key → decrypt → verify ✓")
    print(f"{'='*60}")
    print(f"\nAPI работает: {BASE_URL}")
    print(f"Swagger UI: {BASE_URL}/docs")


if __name__ == "__main__":
    main()
