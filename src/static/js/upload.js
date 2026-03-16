document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const imagesButton = document.getElementById('images-tab-btn');
    const dropzone = document.querySelector('.upload__dropzone');
    const currentUploadInput = document.querySelector('.upload__input');
    const copyButton = document.querySelector('.upload__copy');

    // Використовуємо для показу повідомлень замість alert()
    const messageBox = document.getElementById('message-box');

    // Оновлюємо стиль активної вкладки залежно від поточної сторінки
    const updateTabStyles = () => {
        const uploadTab = document.getElementById('upload-tab-btn');
        const imagesTab = document.getElementById('images-tab-btn');

        uploadTab.classList.remove('upload__tab--active');
        imagesTab.classList.remove('upload__tab--active');

        // Перевіряємо чи ми на сторінці images-list
        if (window.location.pathname.includes('images-list')) {
            imagesTab.classList.add('upload__tab--active');
        } else {
            uploadTab.classList.add('upload__tab--active');
        }
    };

    // Переходимо на сторінку зображень при кліку на вкладку
    if (imagesButton) {
        imagesButton.addEventListener('click', () => {
            window.location.href = '/images-list';
        });
    }

    // Показуємо повідомлення користувачу замість alert()
    // type: "success" або "error"
    const showMessage = (text, type) => {
        if (!messageBox) return;

        messageBox.textContent = text;
        messageBox.className = `message-box message-box--${type}`;
        messageBox.style.display = 'block';

        // Ховаємо повідомлення через 4 секунди
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 4000);
    };

    if (copyButton && currentUploadInput) {
        copyButton.addEventListener('click', () => {
            const textToCopy = currentUploadInput.value;

            // Копіюємо тільки якщо поле не порожнє
            if (textToCopy && textToCopy !== 'https://') {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    copyButton.textContent = 'COPIED!';
                    setTimeout(() => {
                        copyButton.textContent = 'COPY';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                });
            }
        });
    }

    const uploadFile = async (file) => {
        // Перевірка на клієнті (швидка) перед відправкою на сервер
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
        const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5MB

        if (!allowedTypes.includes(file.type)) {
            showMessage(`❌ Invalid file type: ${file.type}. Only JPG, PNG, GIF allowed.`, 'error');
            return;
        }

        if (file.size > MAX_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            showMessage(`❌ File too large: ${sizeMB}MB. Maximum is 5MB.`, 'error');
            return;
        }

        // Створюємо FormData — спеціальний об'єкт для відправки файлів
        // Це те що браузер відправляє як multipart/form-data
        const formData = new FormData();
        // "file" — це ім'я поля яке чекає наш сервер
        // app.py: if "file" not in form
        formData.append('file', file);

        try {
            // Показуємо що файл завантажується
            showMessage('⏳ Uploading...', 'success');

            // fetch() — відправляє HTTP запит на наш сервер
            // Це як XMLHttpRequest але сучасніше і простіше
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                // Content-Type НЕ вказуємо — браузер сам встановить
                // multipart/form-data з правильним boundary
            });

            // Отримуємо JSON відповідь від сервера
            const data = await response.json();

            if (response.ok) {
                // Сервер повернув 200 — успіх!
                // Показуємо URL завантаженого файлу в полі вводу
                if (currentUploadInput) {
                    currentUploadInput.value = `http://localhost:8000${data.url}`;
                }
                showMessage(`✅ File uploaded: ${data.original_name}`, 'success');

            } else {
                // Сервер повернув помилку (400, 500)
                showMessage(`❌ ${data.error}`, 'error');
            }

        } catch (err) {
            // Мережева помилка — сервер недоступний
            console.error('Upload error:', err);
            showMessage(`❌ Server error. Please try again.`, 'error');
        }
    };

    fileUpload.addEventListener('change', async (event) => {
        const files = event.target.files;

        // Завантажуємо кожен файл по черзі
        for (const file of files) {
            await uploadFile(file);
        }

        // Скидаємо input щоб можна було завантажити той самий файл знову
        event.target.value = '';
    });

    // Забороняємо дефолтну поведінку браузера (відкрити файл)
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    // Підсвічуємо dropzone при перетягуванні
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.style.borderColor = 'rgb(0, 96, 255)';
            dropzone.style.backgroundColor = 'rgba(0, 96, 255, 0.05)';
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.style.borderColor = '';
            dropzone.style.backgroundColor = '';
        });
    });

    // Обробляємо файли які перетягнули
    dropzone.addEventListener('drop', async (event) => {
        const files = event.dataTransfer.files;
        for (const file of files) {
            await uploadFile(file);
        }
    });

    updateTabStyles();
});