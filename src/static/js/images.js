document.addEventListener('DOMContentLoaded', () => {

    // ─────────────────────────────────────────────
    // DOM ELEMENTS
    // ─────────────────────────────────────────────

    const fileListWrapper = document.getElementById('file-list-wrapper');
    const uploadTab = document.getElementById('upload-tab-btn');
    const imagesTab = document.getElementById('images-tab-btn');

    // ─────────────────────────────────────────────
    // TAB NAVIGATION
    // ─────────────────────────────────────────────

    // Позначаємо вкладку "Images" як активну
    uploadTab.classList.remove('upload__tab--active');
    imagesTab.classList.add('upload__tab--active');

    // Переходимо на сторінку завантаження при кліку
    if (uploadTab) {
        uploadTab.addEventListener('click', () => {
            window.location.href = '/upload';
        });
    }

    // ─────────────────────────────────────────────
    // FETCH IMAGES FROM SERVER
    // ─────────────────────────────────────────────

    const loadImages = async () => {
        try {
            // Показуємо що завантажуємо
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">Loading...</p>';

            // Отримуємо список зображень з сервера
            // GET /api/images → {"images": [{filename, url, size}, ...]}
            const response = await fetch('/api/images');
            const data = await response.json();

            // Відображаємо список
            displayImages(data.images);

        } catch (err) {
            console.error('Failed to load images:', err);
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">❌ Failed to load images.</p>';
        }
    };

    // ─────────────────────────────────────────────
    // DISPLAY IMAGES
    // ─────────────────────────────────────────────

    const displayImages = (images) => {
        fileListWrapper.innerHTML = '';

        // Якщо список порожній — показуємо повідомлення
        if (!images || images.length === 0) {
            fileListWrapper.innerHTML = '<p class="upload__promt" style="text-align:center; margin-top:50px;">No images uploaded yet.</p>';
            return;
        }

        // Створюємо контейнер таблиці
        const container = document.createElement('div');
        container.className = 'file-list-container';

        // Заголовок таблиці
        const header = document.createElement('div');
        header.className = 'file-list-header';
        header.innerHTML = `
            <div class="file-col file-col-name">Name</div>
            <div class="file-col file-col-url">URL</div>
            <div class="file-col file-col-delete">Delete</div>
        `;
        container.appendChild(header);

        // Список файлів
        const list = document.createElement('div');
        list.id = 'file-list';

        images.forEach((image) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-list-item';

            // Конвертуємо байти в КБ для відображення
            const sizeKB = (image.size / 1024).toFixed(1);

            // Повний URL для копіювання
            const fullUrl = `http://localhost:8000${image.url}`;

            fileItem.innerHTML = `
                <div class="file-col file-col-name">
                    <span class="file-icon">🖼️</span>
                    <span class="file-name">${image.filename}</span>
                </div>
                <div class="file-col file-col-url">
                    <a href="${fullUrl}" target="_blank">${fullUrl}</a>
                </div>
                <div class="file-col file-col-delete">
                    <button class="delete-btn" data-filename="${image.filename}">🗑️</button>
                </div>
            `;
            list.appendChild(fileItem);
        });

        container.appendChild(list);
        fileListWrapper.appendChild(container);

        // Додаємо обробники для кнопок видалення
        addDeleteListeners();
    };

    // ─────────────────────────────────────────────
    // DELETE IMAGE
    // ─────────────────────────────────────────────

    const addDeleteListeners = () => {
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const filename = event.currentTarget.dataset.filename;

                // Підтвердження видалення
                if (!confirm(`Delete ${filename}?`)) return;

                try {
                    // Відправляємо запит на видалення
                    // POST /delete/<filename>
                    const response = await fetch(`/delete/${filename}`, {
                        method: 'POST'
                    });

                    const data = await response.json();

                    if (response.ok) {
                        // Оновлюємо список після видалення
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
    // INIT — завантажуємо список при відкритті сторінки
    // ─────────────────────────────────────────────

    loadImages();
});