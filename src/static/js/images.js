document.addEventListener('DOMContentLoaded', () => {

    // ─────────────────────────────────────────────
    // DOM ЕЛЕМЕНТИ
    // ─────────────────────────────────────────────

    // Контейнер де відображається список зображень
    const fileListWrapper = document.getElementById('file-list-wrapper');
    // Кнопки вкладок навігації
    const uploadTab = document.getElementById('upload-tab-btn');
    const imagesTab = document.getElementById('images-tab-btn');

    // ─────────────────────────────────────────────
    // НАВІГАЦІЯ МІЖ ВКЛАДКАМИ
    // ─────────────────────────────────────────────

    // Позначаємо вкладку "Images" як активну при завантаженні сторінки
    uploadTab.classList.remove('upload__tab--active');
    imagesTab.classList.add('upload__tab--active');

    // При кліку на вкладку "Upload" — переходимо на сторінку завантаження
    if (uploadTab) {
        uploadTab.addEventListener('click', () => {
            window.location.href = '/upload';
        });
    }

    // ─────────────────────────────────────────────
    // ЗАВАНТАЖЕННЯ СПИСКУ ЗОБРАЖЕНЬ З СЕРВЕРА
    // ─────────────────────────────────────────────

    // Отримує список зображень з API і відображає їх на сторінці
    const loadImages = async () => {
        try {
            // Показуємо індикатор завантаження поки чекаємо відповідь
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">Loading...</p>';

            // GET /api/images — повертає JSON з масивом зображень з БД
            // Відповідь: {"images": [{id, filename, original_name, size, url}, ...]}
            const response = await fetch('/api/images');
            const data = await response.json();

            // Передаємо масив зображень у функцію відображення
            displayImages(data.images);

        } catch (err) {
            // Показуємо помилку якщо сервер недоступний
            console.error('Failed to load images:', err);
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">❌ Failed to load images.</p>';
        }
    };

    // ─────────────────────────────────────────────
    // ВІДОБРАЖЕННЯ СПИСКУ ЗОБРАЖЕНЬ
    // ─────────────────────────────────────────────

    // Динамічно створює HTML таблицю зображень і вставляє в DOM
    const displayImages = (images) => {
        // Очищаємо контейнер перед новим рендером
        fileListWrapper.innerHTML = '';

        // Якщо список порожній — показуємо повідомлення користувачу
        if (!images || images.length === 0) {
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">No images uploaded yet.</p>';
            return;
        }

        // Створюємо зовнішній контейнер таблиці
        const container = document.createElement('div');
        container.className = 'file-list-container';

        // Рядок заголовків таблиці
        const header = document.createElement('div');
        header.className = 'file-list-header';
        header.innerHTML = `
            <div class="file-col file-col-name">Name</div>
            <div class="file-col file-col-url">URL</div>
            <div class="file-col file-col-delete">Delete</div>
        `;
        container.appendChild(header);

        // Контейнер для рядків списку
        const list = document.createElement('div');
        list.id = 'file-list';

        // Перебираємо масив зображень і створюємо рядок для кожного
        images.forEach((image) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-list-item';

            // Конвертуємо розмір з байтів в КБ для зручного відображення
            const sizeKB = (image.size / 1024).toFixed(1);

            // Формуємо повний URL для перегляду зображення
            const fullUrl = `http://localhost:8000${image.url}`;

            // Рядок таблиці з іконкою, назвою, URL і кнопкою видалення
            // data-id і data-filename зберігають дані для обробника видалення
            fileItem.innerHTML = `
                <div class="file-col file-col-name">
                    <span class="file-icon">🖼️</span>
                    <span class="file-name">${image.filename}</span>
                </div>
                <div class="file-col file-col-url">
                    <a href="${fullUrl}" target="_blank">${fullUrl}</a>
                </div>
                <div class="file-col file-col-delete">
                    <button class="delete-btn" data-id="${image.id}" data-filename="${image.filename}">🗑️</button>
                </div>
            `;
            list.appendChild(fileItem);
        });

        container.appendChild(list);
        fileListWrapper.appendChild(container);

        // Після рендеру додаємо обробники кліку для кнопок видалення
        addDeleteListeners();
    };

    // ─────────────────────────────────────────────
    // ВИДАЛЕННЯ ЗОБРАЖЕННЯ
    // ─────────────────────────────────────────────

    // Додає обробники кліку до всіх кнопок видалення в таблиці
    const addDeleteListeners = () => {
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {

                // Читаємо id і назву файлу з data атрибутів кнопки
                const imageId = event.currentTarget.dataset.id;
                const filename = event.currentTarget.dataset.filename;

                // Просимо підтвердження перед видаленням
                if (!confirm(`Delete ${filename}?`)) return;

                try {
                    // POST /delete/<id> — видаляє запис з БД і файл з диску
                    const response = await fetch(`/delete/${imageId}`, {
                        method: 'POST'
                    });

                    const data = await response.json();

                    if (response.ok) {
                        // Після успішного видалення — перезавантажуємо список
                        loadImages();
                    } else {
                        alert(`❌ ${data.error}`);
                    }

                } catch (err) {
                    console.error('Delete error:', err);
                    alert('❌ Server error. Please try again.');
                }
            });
        });
    };

    // ─────────────────────────────────────────────
    // ІНІЦІАЛІЗАЦІЯ
    // ─────────────────────────────────────────────

    // Завантажуємо список зображень одразу при відкритті сторінки
    loadImages();
});
