document.addEventListener('DOMContentLoaded', function () {

    // ─────────────────────────────────────────────
    // ВИПАДКОВЕ ЗОБРАЖЕННЯ
    // ─────────────────────────────────────────────

    // Отримуємо всі блоки з зображеннями зі сторінки
    // querySelectorAll повертає список всіх елементів з класом .hero__img
    const allImgBloks = document.querySelectorAll('.hero__img');

    // Генеруємо випадковий індекс від 0 до кількості зображень
    // Math.random() → випадкове число від 0.0 до 1.0
    // * allImgBloks.length → від 0.0 до кількості зображень
    // Math.floor() → округлюємо вниз до цілого числа
    const randomIndex = Math.floor(Math.random() * allImgBloks.length);

    // Отримуємо випадковий блок по індексу
    const randomBlock = allImgBloks[randomIndex];

    // Додаємо клас is-visible щоб показати одне випадкове зображення
    // В CSS: .hero__img { display: none }
    //        .hero__img.is-visible { display: block }
    randomBlock.classList.add('is-visible');

    // ─────────────────────────────────────────────
    // СТИЛІ СТОРІНКИ
    // ─────────────────────────────────────────────

    // Встановлюємо темний фон для головної сторінки
    document.body.style.setProperty('background-color', '#151515');

    // ─────────────────────────────────────────────
    // КНОПКА ПЕРЕХОДУ
    // ─────────────────────────────────────────────

    // Знаходимо кнопку "Tail-ent Showcase" в хедері
    const showcaseButton = document.querySelector('.header__button-btn');

    // Перевіряємо чи кнопка існує на сторінці (захист від помилок)
    if (showcaseButton) {

        // При кліку на кнопку — переходимо на сторінку завантаження
        showcaseButton.addEventListener('click', function () {
            window.location.href = '/upload';
        });
    }
});
