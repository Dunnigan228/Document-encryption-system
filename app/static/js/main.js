const translations = {
    ru: {
        logo: 'SecureDocs',
        title: 'Шифрование документов',
        subtitle: 'Защитите свои файлы надёжным шифрованием',
        tab_encrypt: 'Зашифровать',
        tab_decrypt: 'Расшифровать',
        upload_title: 'Перетащите файл сюда',
        upload_subtitle: 'или нажмите для выбора',
        upload_encrypted: 'Зашифрованный файл',
        upload_key: 'Файл ключа',
        password_label: 'Пароль (необязательно)',
        password_placeholder: 'Оставьте пустым для автогенерации',
        password_hint: 'Если не указать, будет создан автоматически',
        decrypt_password_label: 'Пароль (если использовался)',
        decrypt_password_placeholder: 'Введите пароль, если указывали при шифровании',
        btn_encrypt: 'Зашифровать',
        btn_decrypt: 'Расшифровать',
        btn_processing: 'Обработка...',
        encrypt_success: 'Файл зашифрован',
        decrypt_success: 'Файл расшифрован',
        result_file: 'Файл:',
        result_type: 'Тип:',
        result_size: 'Размер:',
        result_size_before: 'Размер до:',
        result_size_after: 'Размер после:',
        result_password: 'Пароль:',
        result_filename: 'Имя файла:',
        download_encrypted: 'Скачать файл',
        download_key: 'Скачать ключ',
        download_decrypted: 'Скачать файл',
        warning_save: 'Сохраните оба файла. Без ключа расшифровка невозможна.',
        encrypt_another: 'Зашифровать другой файл',
        decrypt_another: 'Расшифровать другой файл',
        footer: 'AES-256 + ChaCha20 + RSA-4096',
        error_prefix: 'Ошибка: ',
        error_no_file: 'Файл не доступен для скачивания',
        error_download: 'Ошибка при скачивании: ',
        copied: 'Скопировано'
    },
    en: {
        logo: 'SecureDocs',
        title: 'Document Encryption',
        subtitle: 'Protect your files with strong encryption',
        tab_encrypt: 'Encrypt',
        tab_decrypt: 'Decrypt',
        upload_title: 'Drop file here',
        upload_subtitle: 'or click to browse',
        upload_encrypted: 'Encrypted file',
        upload_key: 'Key file',
        password_label: 'Password (optional)',
        password_placeholder: 'Leave empty to auto-generate',
        password_hint: 'Will be generated automatically if not provided',
        decrypt_password_label: 'Password (if used)',
        decrypt_password_placeholder: 'Enter password if you used one',
        btn_encrypt: 'Encrypt',
        btn_decrypt: 'Decrypt',
        btn_processing: 'Processing...',
        encrypt_success: 'File encrypted',
        decrypt_success: 'File decrypted',
        result_file: 'File:',
        result_type: 'Type:',
        result_size: 'Size:',
        result_size_before: 'Size before:',
        result_size_after: 'Size after:',
        result_password: 'Password:',
        result_filename: 'Filename:',
        download_encrypted: 'Download file',
        download_key: 'Download key',
        download_decrypted: 'Download file',
        warning_save: 'Save both files. Decryption is impossible without the key.',
        encrypt_another: 'Encrypt another file',
        decrypt_another: 'Decrypt another file',
        footer: 'AES-256 + ChaCha20 + RSA-4096',
        error_prefix: 'Error: ',
        error_no_file: 'No file available for download',
        error_download: 'Download error: ',
        copied: 'Copied'
    }
};

let currentLang = localStorage.getItem('lang') || 'ru';
let currentFileId = null;

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.documentElement.lang = lang;

    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (translations[lang][key]) {
            el.textContent = translations[lang][key];
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.dataset.i18nPlaceholder;
        if (translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });

    document.title = translations[lang].title;
}

function t(key) {
    return translations[currentLang][key] || key;
}

function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(`${tabName}-panel`).classList.add('active');
        });
    });
}

function setupFileUpload(inputId, zoneId) {
    const input = document.getElementById(inputId);
    const zone = document.getElementById(zoneId);

    if (!input || !zone) return;

    zone.addEventListener('dragover', e => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            input.files = e.dataTransfer.files;
            showSelectedFile(zone, input.files[0].name);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            showSelectedFile(zone, input.files[0].name);
        }
    });
}

function showSelectedFile(zone, fileName) {
    const content = zone.querySelector('.upload-content');
    const selected = zone.querySelector('.file-selected');
    const nameSpan = selected.querySelector('.selected-name');

    content.style.display = 'none';
    selected.style.display = 'flex';
    nameSpan.textContent = fileName;
}

function removeFile(type) {
    const map = {
        encrypt: { input: 'encrypt-file', zone: 'encrypt-upload-zone' },
        decrypt: { input: 'decrypt-file', zone: 'decrypt-upload-zone' },
        key: { input: 'key-file', zone: 'key-upload-zone' }
    };

    const { input: inputId, zone: zoneId } = map[type];
    const input = document.getElementById(inputId);
    const zone = document.getElementById(zoneId);

    if (input) input.value = '';
    if (zone) {
        const content = zone.querySelector('.upload-content');
        const selected = zone.querySelector('.file-selected');
        content.style.display = 'block';
        selected.style.display = 'none';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function setFormLoading(form, loading) {
    const btnContent = form.querySelector('.btn-content');
    const btnLoading = form.querySelector('.btn-loading');
    const submitBtn = form.querySelector('.submit-btn');

    btnContent.style.display = loading ? 'none' : 'flex';
    btnLoading.style.display = loading ? 'flex' : 'none';
    submitBtn.disabled = loading;
}

document.getElementById('encrypt-form').addEventListener('submit', async e => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    setFormLoading(form, true);

    try {
        const response = await fetch('/api/encrypt', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Encryption failed');
        }

        const result = await response.json();
        currentFileId = result.file_id;

        document.getElementById('result-original-name').textContent = result.original_filename;
        document.getElementById('result-file-type').textContent = result.file_type;
        document.getElementById('result-original-size').textContent = formatFileSize(result.original_size);
        document.getElementById('result-encrypted-size').textContent = formatFileSize(result.encrypted_size);

        const passwordInfo = document.querySelector('.password-info');
        if (result.password_generated) {
            document.getElementById('result-password').textContent = result.password_generated;
            passwordInfo.style.display = 'flex';
        } else {
            passwordInfo.style.display = 'none';
        }

        form.style.display = 'none';
        document.getElementById('encrypt-result').style.display = 'block';

    } catch (error) {
        alert(t('error_prefix') + error.message);
    } finally {
        setFormLoading(form, false);
    }
});

document.getElementById('decrypt-form').addEventListener('submit', async e => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    setFormLoading(form, true);

    try {
        const response = await fetch('/api/decrypt', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Decryption failed');
        }

        const result = await response.json();
        currentFileId = result.file_id;

        document.getElementById('decrypt-result-filename').textContent = result.original_filename;
        document.getElementById('decrypt-result-type').textContent = result.file_type;
        document.getElementById('decrypt-result-size').textContent = formatFileSize(result.size);

        form.style.display = 'none';
        document.getElementById('decrypt-result').style.display = 'block';

    } catch (error) {
        alert(t('error_prefix') + error.message);
    } finally {
        setFormLoading(form, false);
    }
});

async function downloadFile(type) {
    if (!currentFileId) {
        alert(t('error_no_file'));
        return;
    }

    try {
        const response = await fetch(`/api/download/${currentFileId}/${type}`);

        if (!response.ok) throw new Error('Download failed');

        const blob = await response.blob();
        const disposition = response.headers.get('content-disposition');
        let filename = `file.${type}`;

        if (disposition) {
            const match = disposition.match(/filename="?([^"]+)"?/);
            if (match) filename = match[1];
        }

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        a.remove();

    } catch (error) {
        alert(t('error_download') + error.message);
    }
}

function copyPassword() {
    const password = document.getElementById('result-password').textContent;
    navigator.clipboard.writeText(password).then(() => {
        const btn = event.target.closest('.icon-btn');
        const icon = btn.querySelector('.material-icons');
        const original = icon.textContent;
        icon.textContent = 'check';
        setTimeout(() => {
            icon.textContent = original;
        }, 1500);
    });
}

function resetEncrypt() {
    const form = document.getElementById('encrypt-form');
    form.reset();
    form.style.display = 'block';
    document.getElementById('encrypt-result').style.display = 'none';
    removeFile('encrypt');
    currentFileId = null;
}

function resetDecrypt() {
    const form = document.getElementById('decrypt-form');
    form.reset();
    form.style.display = 'block';
    document.getElementById('decrypt-result').style.display = 'none';
    removeFile('decrypt');
    removeFile('key');
    currentFileId = null;
}

document.addEventListener('DOMContentLoaded', () => {
    setLanguage(currentLang);
    setupTabs();
    setupFileUpload('encrypt-file', 'encrypt-upload-zone');
    setupFileUpload('decrypt-file', 'decrypt-upload-zone');
    setupFileUpload('key-file', 'key-upload-zone');

    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
    });
});
