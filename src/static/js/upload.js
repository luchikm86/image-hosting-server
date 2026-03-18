document.addEventListener('DOMContentLoaded', () => {

    // ─────────────────────────────────────────────
    // DOM ЕЛЕМЕНТИ
    // ─────────────────────────────────────────────

    // Отримуємо посилання на елементи сторінки
    const fileUpload = document.getElementById('file-upload');         // input для вибору файлу
    const imagesButton = document.getElementById('images-tab-btn');    // кнопка вкладки "Images"
    const dropzone = document.querySelector('.upload__dropzone');       // зона для drag & drop
    const currentUploadInput = document.querySelector('.upload__input'); // поле з URL файлу
    const copyButton = document.querySelector('.upload__copy');          // кнопка копіювання URL

    // Блок для показу повідомлень про успіх або помилку
    const messageBox = document.getElementById('message-box');

    // ─────────────────────────────────────────────
    // НАВІГАЦІЯ МІЖ ВКЛАДКАМИ
    // ─────────────────────────────────────────────

    // Визначаємо яка вкладка активна залежно від поточної сторінки
    const updateTabStyles = () => {
        const uploadTab = document.getElementById('upload-tab-btn');
        const imagesTab = document.getElementById('images-tab-btn');

        // Спочатку знімаємо активний клас з обох вкладок
        uploadTab.classList.remove('upload__tab--active');
        imagesTab.classList.remove('upload__tab--active');

        // Додаємо активний клас до потрібної вкладки
        if (window.location.pathname.includes('images-list')) {
            imagesTab.classList.add('upload__tab--active');
        } else {
            uploadTab.classList.add('upload__tab--active');
        }
    };

    // При кліку на вкладку "Images" — переходимо на сторінку списку
    if (imagesButton) {
        imagesButton.addEventListener('click', () => {
            window.location.href = '/images-list';
        });
    }

    // ─────────────────────────────────────────────
    // ПОВІДОМЛЕННЯ КОРИСТУВАЧУ
    // ─────────────────────────────────────────────

    // Показуємо повідомлення в блоці message-box замість alert()
    // type: "success" (зелений) або "error" (червоний)
    const showMessage = (text, type) => {
        if (!messageBox) return;

        // Встановлюємо текст і CSS клас для кольору
        messageBox.textContent = text;
        messageBox.className = `message-box message-box--${type}`;
        messageBox.style.display = 'block';

        // Автоматично ховаємо повідомлення через 4 секунди
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 4000);
    };

    // ─────────────────────────────────────────────
    // КНОПКА КОПІЮВАННЯ URL
    // ─────────────────────────────────────────────

    if (copyButton && currentUploadInput) {
        copyButton.addEventListener('click', () => {
            const textToCopy = currentUploadInput.value;

            // Копіюємо тільки якщо поле містить реальний URL
            if (textToCopy && textToCopy !== 'https://') {
                // navigator.clipboard — сучасний API для роботи з буфером обміну
                navigator.clipboard.writeText(textToCopy).then(() => {
                    // Тимчасово змінюємо текст кнопки для підтвердження
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

    // ─────────────────────────────────────────────
    // ЗАВАНТАЖЕННЯ ФАЙЛУ НА СЕРВЕР
    // ─────────────────────────────────────────────

    // Головна функція — відправляє файл на сервер і обробляє відповідь
    // async/await — дозволяє писати асинхронний код як синхронний
    const uploadFile = async (file) => {

        // Швидка перевірка на клієнті перед відправкою на сервер
        // Це економить час — не потрібно чекати відповіді сервера
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
        const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5MB в байтах

        // Перевіряємо MIME тип файлу
        if (!allowedTypes.includes(file.type)) {
            showMessage(`❌ Invalid file type: ${file.type}. Only JPG, PNG, GIF allowed.`, 'error');
            return;
        }

        // Перевіряємо розмір файлу
        if (file.size > MAX_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            showMessage(`❌ File too large: ${sizeMB}MB. Maximum is 5MB.`, 'error');
            return;
        }

        // FormData — спеціальний об'єкт для відправки файлів через HTTP
        // Браузер автоматично встановить Content-Type: multipart/form-data
        const formData = new FormData();
        formData.append('file', file); // "file" — ім'я поля яке очікує app.py

        try {
            // Показуємо індикатор завантаження
            showMessage('⏳ Uploading...', 'success');

            // fetch() — відправляє HTTP POST запит на наш сервер
            // await — чекаємо відповіді від сервера
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                // Content-Type НЕ вказуємо вручну — браузер сам додасть
                // multipart/form-data з правильним boundary рядком
            });

            // Парсимо JSON відповідь від сервера
            const data = await response.json();

            if (response.ok) {
                // response.ok = true якщо статус код 200-299
                // Показуємо URL завантаженого файлу в полі вводу
                if (currentUploadInput) {
                    currentUploadInput.value = `http://localhost:8000${data.url}`;
                }
                showMessage(`✅ File uploaded: ${data.original_name}`, 'success');

            } else {
                // Сервер повернув помилку (400 — невалідний файл, 500 — помилка сервера)
                showMessage(`❌ ${data.error}`, 'error');
            }

        } catch (err) {
            // catch спрацьовує при мережевій помилці (сервер недоступний)
            console.error('Upload error:', err);
            showMessage(`❌ Server error. Please try again.`, 'error');
        }
    };

    // ─────────────────────────────────────────────
    // ВИБІР ФАЙЛУ ЧЕРЕЗ КНОПКУ
    // ─────────────────────────────────────────────

    // Спрацьовує коли користувач вибрав файл через діалог
    fileUpload.addEventListener('change', async (event) => {
        const files = event.target.files;

        // Завантажуємо кожен файл по черзі (підтримуємо multiple)
        for (const file of files) {
            await uploadFile(file);
        }

        // Скидаємо значення input — дозволяє завантажити той самий файл знову
        event.target.value = '';
    });

    // ─────────────────────────────────────────────
    // DRAG & DROP
    // ─────────────────────────────────────────────

    // Забороняємо дефолтну поведінку браузера для всіх drag подій
    // Без цього браузер відкрив би файл замість завантаження
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();  // скасовуємо дефолтну дію
            e.stopPropagation(); // зупиняємо поширення події вгору по DOM
        });
    });

    // Підсвічуємо dropzone коли файл перетягують над нею
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.style.borderColor = 'rgb(0, 96, 255)';
            dropzone.style.backgroundColor = 'rgba(0, 96, 255, 0.05)';
        });
    });

    // Прибираємо підсвічування коли файл покинув зону або був відпущений
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.style.borderColor = '';
            dropzone.style.backgroundColor = '';
        });
    });

    // Обробляємо файли які перетягнули і відпустили в dropzone
    dropzone.addEventListener('drop', async (event) => {
        // event.dataTransfer.files — файли які перетягнули
        const files = event.dataTransfer.files;
        for (const file of files) {
            await uploadFile(file);
        }
    });

    // ─────────────────────────────────────────────
    // ІНІЦІАЛІЗАЦІЯ
    // ─────────────────────────────────────────────

    // Встановлюємо правильний стиль активної вкладки при завантаженні сторінки
    updateTabStyles();
});
