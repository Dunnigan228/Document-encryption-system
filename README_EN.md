<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

<h1 align="center">SecureDocs</h1>

<p align="center">
  <b>Multi-layer Document Encryption System</b>
</p>

<p align="center">
  <a href="README.md">Русский</a> | <a href="README_EN.md">English</a>
</p>

---

## About

SecureDocs is a web application for document encryption using multiple layers of cryptographic protection. The simple interface allows you to encrypt a file in just a few clicks.

### Features

| Feature | Description |
|---------|-------------|
| Multi-layer encryption | AES-256-GCM + ChaCha20-Poly1305 + RSA-4096 |
| Web interface | Modern Material Design UI |
| Drag & Drop | Drag files to upload |
| Password generation | Cryptographically secure auto-generated passwords |
| Docker | One-command deployment |
| Auto-cleanup | Files deleted after 24 hours |

---

## Quick Start

### Docker (recommended)

```bash
git clone <repository>
cd document_encryption_system
docker-compose up --build
```

Open browser: **http://localhost:8000**

### Local Installation

```bash
pip install -r requirements.txt
cd app
python main.py
```

---

## Usage

### Encryption

1. Open the **"Encrypt"** tab
2. Drag a file or click to browse
3. Enter a password (or leave empty for auto-generation)
4. Click **"Encrypt"**
5. Download **encrypted file** and **key file**

### Decryption

1. Open the **"Decrypt"** tab
2. Upload the encrypted file
3. Upload the key file
4. Enter password (if used)
5. Click **"Decrypt"**

---

## Encryption Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     SOURCE FILE                         │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  1. COMPRESSION (zlib)                                  │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  2. AES-256-GCM                                         │
│     • 256-bit key                                       │
│     • Authenticated encryption                          │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  3. ChaCha20-Poly1305                                   │
│     • Additional protection layer                       │
│     • Timing attack resistant                           │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  4. CUSTOM TRANSFORMATIONS                              │
│     • S-box substitutions                               │
│     • Byte permutations                                 │
│     • 16 rounds                                         │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  5. RSA-4096 (key protection)                           │
│     • Symmetric keys encrypted with RSA                 │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  6. HMAC-SHA512 (integrity)                             │
│     • Data authenticity verification                    │
└─────────────────────┴───────────────────────────────────┘
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/encrypt` | Encrypt document |
| `POST` | `/api/decrypt` | Decrypt document |
| `GET` | `/api/download/{id}/{type}` | Download file |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/encrypt" \
  -F "file=@document.pdf" \
  -F "password=mypassword"
```

---

## Project Structure

```
document_encryption_system/
├── app/
│   ├── main.py              # FastAPI application
│   ├── static/
│   │   ├── css/style.css    # Styles
│   │   └── js/main.js       # Frontend logic
│   └── templates/
│       └── index.html       # HTML template
├── core/                    # Encryption core
│   ├── encryption_engine.py
│   ├── decryption_engine.py
│   └── key_manager.py
├── algorithms/              # Algorithms
│   ├── aes_handler.py
│   ├── chacha_handler.py
│   └── rsa_handler.py
├── security/                # Security
├── utils/                   # Utilities
├── config/                  # Configuration
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Supported Formats

| Format | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Word | `.doc`, `.docx` |
| Excel | `.xls`, `.xlsx` |
| Text | `.txt` |

---

## Security

- **PBKDF2** — 600,000 iterations for key derivation
- **AEAD** — authenticated encryption
- **RSA-4096** — asymmetric key protection
- **HMAC-SHA512** — integrity verification
- **Auto-cleanup** — files deleted after 24 hours

---

## Development

```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## License

This project is for educational purposes.

---

<p align="center">
  <sub>AES-256-GCM • ChaCha20-Poly1305 • RSA-4096 • HMAC-SHA512</sub>
</p>
