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
  var accessEl = document.getElementById('accessFilter');
  var items = document.querySelectorAll('.record-item');
  var pills = document.querySelectorAll('#conceptFilter .filter-pill');
  var tabs = document.querySelectorAll('.view-tab');
  var panels = document.querySelectorAll('.view-panel');
  if (!searchEl || !countEl || !items.length) return;

  function normalize(value) {
    return (value || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  var activeKind = '';
  var activeKey = '';
  var activeAccess = '';
  var activeView = 'all';

  function hasToken(value, token) {
    return !token || (' ' + (value || '') + ' ').indexOf(' ' + token + ' ') >= 0;
  }

  function activePanel() {
    return document.querySelector('.view-panel[data-panel="' + activeView + '"]');
  }

  function applyFilters() {
    var query = searchEl.value.toLowerCase().trim();
    var queryAscii = normalize(searchEl.value);
    var currentPanel = activePanel();
    var visibleIds = {};
    items.forEach(function (item) {
      var hay = item.dataset.search || '';
      var hayAscii = item.dataset.searchAscii || '';
      var conceptHay = activeKind === 'medicinal' ? item.dataset.medicinal : item.dataset.ritual;
      var ok = (!query || hay.indexOf(query) >= 0 || hayAscii.indexOf(queryAscii) >= 0) &&
        hasToken(conceptHay, activeKey) &&
        (!activeAccess || item.dataset.access === activeAccess);
      item.classList.toggle('hidden', !ok);
      if (ok && currentPanel && currentPanel.contains(item)) {
        visibleIds[item.dataset.recordId || Math.random().toString()] = true;
      }
    });
    document.querySelectorAll('.browse-group, .name-index').forEach(function (group) {
      var visibleChild = group.querySelector('.record-item:not(.hidden)');
      group.classList.toggle('hidden', !visibleChild);
    });
    countEl.firstChild.textContent = Object.keys(visibleIds).length + ' ';
  }

  searchEl.addEventListener('input', applyFilters);
  if (accessEl) {
    accessEl.addEventListener('change', function () {
      activeAccess = accessEl.value;
      applyFilters();
    });
  }
  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      activeKind = pill.dataset.kind || '';
      activeKey = pill.dataset.key || '';
      applyFilters();
    });
  });
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      activeView = tab.dataset.view || 'all';
      tabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
      panels.forEach(function (panel) {
        panel.classList.toggle('active', panel.dataset.panel === activeView);
      });
      applyFilters();
    });
  });
  applyFilters();
})();
