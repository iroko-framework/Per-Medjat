(function () {
  var LANGS = ['en', 'es', 'fr', 'yo', 'pt'];
  var uiCopy = window.EWE_UI_COPY || {};
  var stored = localStorage.getItem('ewe-ui-lang') || 'en';
  if (LANGS.indexOf(stored) < 0) stored = 'en';

  function textFor(key, lang) {
    return uiCopy[key] && uiCopy[key][lang] ? uiCopy[key][lang] : null;
  }

  function applyLang(lang) {
    document.body.setAttribute('data-ui-lang', lang);
    document.querySelectorAll('.ui-copy').forEach(function (el) {
      var key = el.getAttribute('data-copy-key');
      var value = textFor(key, lang);
      if (value) el.textContent = value;
    });
    var searchInput = document.getElementById('plantSearch');
    if (searchInput) {
      var placeholder = textFor('search_placeholder', lang);
      if (placeholder) searchInput.placeholder = placeholder;
    }
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.lang === lang);
    });
    localStorage.setItem('ewe-ui-lang', lang);
  }

  document.querySelectorAll('.lang-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { applyLang(btn.dataset.lang); });
  });

  applyLang(stored);
})();

(function () {
  var searchEl = document.getElementById('plantSearch');
  var countEl = document.getElementById('searchCount');
  var cards = document.querySelectorAll('.plant-card');
  var pills = document.querySelectorAll('#ritualFilter .filter-pill');
  if (!searchEl || !countEl || !cards.length) return;

  function normalize(value) {
    return (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  }

  var activeRitual = '';

  function applyFilters() {
    var query = searchEl.value.toLowerCase().trim();
    var queryAscii = normalize(searchEl.value);
    var visible = 0;
    cards.forEach(function (card) {
      var hay = card.dataset.search || '';
      var hayAscii = card.dataset.searchAscii || '';
      var ok = (!query || hay.indexOf(query) >= 0 || hayAscii.indexOf(queryAscii) >= 0) &&
        (!activeRitual || card.dataset.ritual === activeRitual);
      card.classList.toggle('hidden', !ok);
      if (ok) visible++;
    });
    countEl.firstChild.textContent = visible + ' ';
  }

  searchEl.addEventListener('input', applyFilters);
  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      activeRitual = pill.dataset.ritual;
      applyFilters();
    });
  });
})();
