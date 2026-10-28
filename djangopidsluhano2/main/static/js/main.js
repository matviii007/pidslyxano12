/* =========================================================
   Підслухано у Ліцеї 8 — невеликий JavaScript для макета.

   ВАЖЛИВО ДЛЯ DJANGO:
   Більшість того, що тут позначено "ДЕМО", у справжньому сайті
   робитиме сервер (Django). Наприклад, фільтр за темою —
   це view, який повертає лише потрібні дописи.
   Такі шматки можна буде видалити.

   Те, що позначено "ЗАЛИШИТИ", корисне і на справжньому сайті.
   ========================================================= */

const params = new URLSearchParams(location.search);

/* ---------- ЗАЛИШИТИ: перемикач світлої/темної теми ---------- */
document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('pl8-theme', next); } catch (e) {}
  });
});

/* ---------- ЗАЛИШИТИ: спливаюче повідомлення (toast) ---------- */
function toast(text) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = '✓ ' + text;
  el.classList.add('is-on');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('is-on'), 2600);
}

/* ДЕМО: повідомлення після відправки форм (?msg=...).
   У Django замість цього використовують messages framework:
   messages.success(request, "Допис надіслано на модерацію") */
const MESSAGES = {
  welcome: 'Вітаємо в «Підслухано»!',
  moderation: 'Надіслано на модерацію. Зазвичай до 15 хв',
  reply: 'Відповідь додано',
  report: 'Дякуємо! Модератори перевірять допис',
  profile: 'Профіль оновлено',
  read: 'Усі сповіщення прочитано'
};
if (MESSAGES[params.get('msg')]) toast(MESSAGES[params.get('msg')]);

/* ЗАЛИШИТИ: якщо Django вже показав повідомлення (клас is-on), ховаємо його через 2.6 с */
const serverToast = document.querySelector('#toast.is-on');
if (serverToast) setTimeout(() => serverToast.classList.remove('is-on'), 2600);

/* ---------- ЗАЛИШИТИ: закривати меню "⋯", якщо клікнули деінде ---------- */
document.addEventListener('click', (e) => {
  document.querySelectorAll('details.dropdown[open]').forEach((d) => {
    if (!d.contains(e.target)) d.removeAttribute('open');
  });
});

/* ---------- ЗАЛИШИТИ: кнопка "Назад" ---------- */
document.querySelectorAll('[data-back]').forEach((a) => {
  a.addEventListener('click', (e) => {
    if (history.length > 1) { e.preventDefault(); history.back(); }
  });
});

/* ---------- ЗАЛИШИТИ: скопіювати посилання ---------- */
document.querySelectorAll('[data-share]').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const post = btn.closest('.post');
    const postUrl = post?.dataset.postUrl || post?.querySelector('.post__link')?.href;
    if (!postUrl) {
      console.error('Could not find the post link to share.');
      toast('Не вдалося знайти посилання на допис');
      return;
    }

    btn.closest('details')?.removeAttribute('open');
    try {
      await navigator.clipboard.writeText(new URL(postUrl, location.href).href);
      toast('Посилання скопійовано');
    } catch (error) {
      console.error('Could not copy the post link.', error);
      toast('Не вдалося скопіювати посилання');
    }
  });
});

/* ---------- ДЕМО: лайк і репост ----------
   У Django це буде маленька POST-форма або fetch() до /post/<id>/like/,
   а кількість лайків рахуватиме сервер. */
document.querySelectorAll('.act--like, .act--repost').forEach((btn) => {
  if (btn.closest('form')) return;
  btn.addEventListener('click', () => {
    const on = btn.classList.toggle('is-on');
    const span = btn.querySelector('span');
    const n = (parseInt(span.textContent, 10) || 0) + (on ? 1 : -1);
    span.textContent = n || '';
  });
});

/* ---------- ДЕМО: підписка ---------- */
document.querySelectorAll('[data-follow]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const following = btn.classList.toggle('btn--ghost');
    btn.textContent = following ? 'Ви підписані' : 'Підписатися';
  });
});

/* ---------- ДЕМО: вкладки (?tab=...) ----------
   Елементи з data-tabs="posts" (або в стрічці data-filter="all anon")
   показуються лише на перелічених вкладках.
   У Django фільтрацію робить view, а в шаблоні лише підсвічується активна вкладка:
   class="tabs__btn {% if active_tab == 'anon' %}is-active{% endif %}" */
const tabsNav = document.querySelector('[data-tabs-nav]');
if (tabsNav) {
  const tab = params.get('tab') || tabsNav.dataset.default;
  tabsNav.querySelectorAll('[data-tab]').forEach((a) => {
    a.classList.toggle('is-active', a.dataset.tab === tab);
    // зберігаємо вибрану тему, коли перемикаємо вкладку
    if (params.get('topic')) a.href += '&topic=' + encodeURIComponent(params.get('topic'));
  });
  document.querySelectorAll(tabsNav.dataset.target).forEach((el) => {
    const list = el.dataset.tabs || el.dataset.filter;
    el.hidden = !list.split(' ').includes(tab);
  });
}

/* ---------- ДЕМО: фільтр за темою (?topic=...) ---------- */
const chips = document.querySelectorAll('.chips [data-tag]');
if (chips.length) {
  const tag = params.get('topic') || '';
  chips.forEach((c) => {
    c.classList.toggle('is-active', c.dataset.tag === tag);
    if (params.get('tab')) c.href += (c.href.includes('?') ? '&' : '?') + 'tab=' + params.get('tab');
  });
  if (tag) {
    document.querySelectorAll('.feed .post').forEach((p) => {
      if (p.dataset.tag !== tag) p.hidden = true;
    });
  }
  const anyVisible = [...document.querySelectorAll('.feed .post')].some((p) => !p.hidden);
  const empty = document.querySelector('[data-empty]');
  if (empty) empty.hidden = anyVisible;
}

/* ---------- ДЕМО: пошук (?q=...) ---------- */
const results = document.querySelector('[data-search-results]');
if (results) {
  const q = (params.get('q') || '').trim().toLowerCase();
  const input = document.querySelector('input[name="q"]');
  if (q) {
    input.value = params.get('q');
    results.hidden = false;
    document.querySelector('[data-search-default]').hidden = true;
    document.querySelector('[data-search-q]').textContent = params.get('q');
    let found = 0;
    results.querySelectorAll('.post').forEach((p) => {
      const match = p.textContent.toLowerCase().includes(q.replace('#', ''));
      p.hidden = !match;
      if (match) found++;
    });
    results.querySelector('[data-empty]').hidden = found > 0;
  }
}

/* ---------- ЗАЛИШИТИ: лічильник символів і "Анонім" у формі нового допису ---------- */
const textarea = document.querySelector('[data-counter]');
if (textarea) {
  const count = document.querySelector('[data-count]');
  textarea.addEventListener('input', () => { count.textContent = textarea.value.length; });
}
const anonToggle = document.querySelector('[data-anon-toggle]');
const moderationToggle = document.querySelector('[data-moderation-toggle]');
const composeName = document.querySelector('[data-compose-name]');
if (anonToggle && composeName) {
  const row = composeName.closest('.compose__row');
  const anonymousAvatar = row.querySelector('[data-author-anonymous]');
  const profileAvatar = row.querySelector('[data-author-profile]');
  const moderationAvatar = row.querySelector('[data-author-moderation]');
  const profileBio = row.querySelector('[data-author-bio]');
  const updateAuthorPreview = () => {
    const isModeration = Boolean(moderationToggle?.checked);
    const isAnonymous = !isModeration && anonToggle.checked;

    composeName.textContent = isModeration
      ? composeName.dataset.moderationName
      : isAnonymous
        ? composeName.dataset.anonymousName
        : composeName.dataset.userName;
    anonymousAvatar.hidden = !isAnonymous;
    profileAvatar.hidden = isAnonymous || isModeration;
    moderationAvatar.hidden = !isModeration;
    profileBio.hidden = isAnonymous || isModeration;
  };

  anonToggle.addEventListener('change', () => {
    if (anonToggle.checked && moderationToggle) moderationToggle.checked = false;
    updateAuthorPreview();
  });
  moderationToggle?.addEventListener('change', () => {
    if (moderationToggle.checked) anonToggle.checked = false;
    updateAuthorPreview();
  });
  updateAuthorPreview();
}

/* ---------- Редактор обрізання фото профілю ---------- */
const avatarInput = document.querySelector('[data-avatar-input]');
const cropModal = document.querySelector('[data-avatar-crop-modal]');
const cropCanvas = document.querySelector('[data-avatar-crop-canvas]');
const cropZoom = document.querySelector('[data-avatar-crop-zoom]');
const avatarPreview = document.querySelector('[data-avatar-preview]');

if (avatarInput && cropModal && cropCanvas && cropZoom && avatarPreview) {
  const context = cropCanvas.getContext('2d');
  const cancelButtons = cropModal.querySelectorAll('[data-avatar-crop-cancel]');
  const saveButton = cropModal.querySelector('[data-avatar-crop-save]');
  const fileNameLabel = document.querySelector('[data-avatar-filename]');
  const initialPreview = [...avatarPreview.childNodes].map((node) => node.cloneNode(true));
  const maxFileSize = 5 * 1024 * 1024;
  let sourceImage = null;
  let sourceUrl = null;
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let pointerPosition = null;
  let previousFocus = null;

  const imageSize = () => ({
    width: sourceImage.naturalWidth * scale,
    height: sourceImage.naturalHeight * scale,
  });

  const clampOffset = () => {
    const size = imageSize();
    offsetX = Math.min(0, Math.max(cropCanvas.width - size.width, offsetX));
    offsetY = Math.min(0, Math.max(cropCanvas.height - size.height, offsetY));
  };

  const drawCrop = () => {
    if (!sourceImage || !context) return;
    clampOffset();
    const size = imageSize();
    context.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
    context.drawImage(sourceImage, offsetX, offsetY, size.width, size.height);
  };

  const resetPreview = () => {
    avatarPreview.replaceChildren(...initialPreview.map((node) => node.cloneNode(true)));
  };

  const closeCrop = (cancelSelection) => {
    cropModal.hidden = true;
    sourceImage = null;
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    sourceUrl = null;
    if (cancelSelection) {
      avatarInput.value = '';
      if (fileNameLabel) fileNameLabel.textContent = 'Фото не вибрано';
      resetPreview();
    }
    previousFocus?.focus();
  };

  avatarInput.addEventListener('change', () => {
    const file = avatarInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      avatarInput.value = '';
      if (fileNameLabel) fileNameLabel.textContent = 'Фото не вибрано';
      toast('Оберіть файл зображення');
      return;
    }
    if (file.size > maxFileSize) {
      avatarInput.value = '';
      if (fileNameLabel) fileNameLabel.textContent = 'Фото не вибрано';
      toast('Розмір фото не може перевищувати 5 МБ');
      return;
    }

    if (fileNameLabel) fileNameLabel.textContent = file.name;
    sourceUrl = URL.createObjectURL(file);
    sourceImage = new Image();
    sourceImage.onload = () => {
      const coverScale = Math.max(
        cropCanvas.width / sourceImage.naturalWidth,
        cropCanvas.height / sourceImage.naturalHeight,
      );
      scale = coverScale;
      offsetX = (cropCanvas.width - sourceImage.naturalWidth * scale) / 2;
      offsetY = (cropCanvas.height - sourceImage.naturalHeight * scale) / 2;
      cropZoom.value = '1';
      previousFocus = document.activeElement;
      cropModal.hidden = false;
      drawCrop();
      saveButton.focus();
    };
    sourceImage.onerror = () => {
      URL.revokeObjectURL(sourceUrl);
      sourceUrl = null;
      sourceImage = null;
      avatarInput.value = '';
    if (fileNameLabel) fileNameLabel.textContent = 'Фото не вибрано';
    toast('Не вдалося відкрити це фото');
    };
    sourceImage.src = sourceUrl;
  });

  cropZoom.addEventListener('input', () => {
    if (!sourceImage) return;
    const coverScale = Math.max(
      cropCanvas.width / sourceImage.naturalWidth,
      cropCanvas.height / sourceImage.naturalHeight,
    );
    const currentZoom = scale / coverScale;
    const nextZoom = Number(cropZoom.value);
    const centerX = (cropCanvas.width / 2 - offsetX) / currentZoom;
    const centerY = (cropCanvas.height / 2 - offsetY) / currentZoom;
    scale = coverScale * nextZoom;
    offsetX = cropCanvas.width / 2 - centerX * nextZoom;
    offsetY = cropCanvas.height / 2 - centerY * nextZoom;
    drawCrop();
  });

  cropCanvas.addEventListener('pointerdown', (event) => {
    if (!sourceImage) return;
    pointerPosition = { x: event.clientX, y: event.clientY };
    cropCanvas.setPointerCapture(event.pointerId);
  });
  cropCanvas.addEventListener('pointermove', (event) => {
    if (!pointerPosition) return;
    const bounds = cropCanvas.getBoundingClientRect();
    const ratio = cropCanvas.width / bounds.width;
    offsetX += (event.clientX - pointerPosition.x) * ratio;
    offsetY += (event.clientY - pointerPosition.y) * ratio;
    pointerPosition = { x: event.clientX, y: event.clientY };
    drawCrop();
  });
  cropCanvas.addEventListener('pointerup', () => { pointerPosition = null; });
  cropCanvas.addEventListener('pointercancel', () => { pointerPosition = null; });

  cancelButtons.forEach((button) => {
    button.addEventListener('click', () => closeCrop(true));
  });
  cropModal.addEventListener('click', (event) => {
    if (event.target === cropModal) closeCrop(true);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !cropModal.hidden) closeCrop(true);
  });

  saveButton.addEventListener('click', () => {
    if (!sourceImage || !context) return;
    const outputCanvas = document.createElement('canvas');
    outputCanvas.width = 512;
    outputCanvas.height = 512;
    const outputContext = outputCanvas.getContext('2d');
    if (!outputContext) {
      toast('Не вдалося підготувати фото');
      return;
    }
    outputContext.fillStyle = '#fff';
    outputContext.fillRect(0, 0, outputCanvas.width, outputCanvas.height);
    const ratio = outputCanvas.width / cropCanvas.width;
    const size = imageSize();
    outputContext.drawImage(
      sourceImage,
      offsetX * ratio,
      offsetY * ratio,
      size.width * ratio,
      size.height * ratio,
    );
    outputCanvas.toBlob((blob) => {
      if (!blob) {
        toast('Не вдалося обрізати фото');
        return;
      }
      const croppedFile = new File(
        [blob],
        'avatar.jpg',
        { type: 'image/jpeg', lastModified: Date.now() },
      );
      if (croppedFile.size > maxFileSize) {
        toast('Не вдалося стиснути фото до 5 МБ');
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(croppedFile);
      avatarInput.files = transfer.files;
      if (fileNameLabel) fileNameLabel.textContent = 'Фото обрізано — готове до збереження';
      const previewImage = new Image();
      previewImage.className = 'avatar__image';
      previewImage.alt = 'Попередній перегляд фото профілю';
      previewImage.src = URL.createObjectURL(croppedFile);
      avatarPreview.replaceChildren(previewImage);
      closeCrop(false);
    }, 'image/jpeg', 0.88);
  });
}
