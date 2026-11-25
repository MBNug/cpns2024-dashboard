(() => {
  'use strict';

  const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
  const BOOKMARK_STORAGE_KEY = 'cpns2024_bookmarks';
  const THEME_STORAGE_KEY = 'cpns2024_theme';
  const MAX_BOOKMARKS = 10;

  // Consistent 1.75px-stroke inline SVG icon library
  const ICONS = {
    sun:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>',
    moon:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
    starOutline:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    starFilled:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    pin:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
    eye:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>',
    close:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    check:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    plus:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    alert:
      '<svg class="icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
    chevFirst:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/></svg>',
    chevPrev:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
    chevNext:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
    chevLast:
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/></svg>'
  };

  const state = {
    q: '',
    jurusan: '',
    jurusan_id: null,
    jenjang: 'ALL',
    kategori_instansi: 'ALL',
    instansi_id: 'ALL',
    instansi_nama: '',
    jenis_formasi: 'ALL',
    status_keketatan: 'ALL',
    zero_applicant_only: false,
    gaji_min: 0,
    sort_by: 'kuota_desc',
    page: 1,
    limit: 10
  };

  let allInstansi = [];
  let statsCache = null;
  let activeDetailId = null;
  let currentDetailData = null;
  let currentDetailInstansi = '';
  let currentDetailRegulasi = '';
  const loadedFormasiMap = new Map();
  let tableViewMode = window.innerWidth < 768 ? 'cards' : 'table';
  let userForcedViewMode = false;
  let lastLoadedItems = [];
  let lastLoadedStartIdx = 1;

  let tableAbortController = null;
  let jurusanAbortController = null;
  let detailAbortController = null;
  let topAnalyticsAbortController = null;
  let isAnalyticsOpen = false;
  let lastTopAnalyticsSignature = null;
  let activeAnalyticsSnapshot = null;
  let toastTimer = null;

  const thpSimState = {
    isPns100: false,
    keluarga: 'TK0',
    cpns80: 0,
    pns100: 0,
    uangMakanBulan: 0,
    tukinMin: 0,
    tukinMax: 0,
    tukinBaseline: 0
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function cleanLocation(str) {
    if (!str) return '-';
    return String(str).replace(/^[\s|•-]+/, '').trim() || '-';
  }

  function formatRp(val) {
    if (!val) return 'Rp\u00A00';
    return 'Rp\u00A0' + Number(val).toLocaleString('id-ID');
  }

  function formatJuta(val) {
    if (!val) return 'Rp\u00A00';
    const jt = (val / 1000000).toFixed(1).replace('.0', '').replace('.', ',');
    return `Rp\u00A0${jt}\u00A0Jt`;
  }

  function debounce(func, wait = 300) {
    let timeout;
    return function debounced(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  function showToast(message, tone = 'info') {
    const toast = document.getElementById('toast-notification');
    if (!toast) return;
    toast.className = 'toast-banner';
    if (tone === 'warn') toast.classList.add('tone-warn');
    if (tone === 'success') toast.classList.add('tone-success');
    const leadIcon = tone === 'success' ? ICONS.check : ICONS.alert;
    toast.innerHTML = `${leadIcon}<span>${escapeHtml(message)}</span>`;
    toast.classList.remove('is-hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.add('is-hidden');
    }, 2800);
  }

  async function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (!ok) throw new Error('Clipboard copy failed');
    return true;
  }

  // =========================================================================
  // URL DEEP-LINK SYNCHRONIZATION
  // =========================================================================
  function buildFilterParams(includePagination = true, includeDetail = true) {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.jurusan) params.set('jurusan', state.jurusan);
    if (state.jurusan_id) params.set('jurusan_id', String(state.jurusan_id));
    if (state.jenjang !== 'ALL') params.set('jenjang', state.jenjang);
    if (state.kategori_instansi !== 'ALL') params.set('kategori_instansi', state.kategori_instansi);
    if (state.instansi_id !== 'ALL') {
      params.set('instansi_id', String(state.instansi_id));
      if (state.instansi_nama) params.set('instansi_nama', state.instansi_nama);
    }
    if (state.jenis_formasi !== 'ALL') params.set('jenis_formasi', state.jenis_formasi);
    if (state.status_keketatan !== 'ALL') params.set('status_keketatan', state.status_keketatan);
    if (state.zero_applicant_only) params.set('zero_applicant_only', 'true');
    if (state.gaji_min > 0) params.set('gaji_min', String(state.gaji_min));
    if (state.sort_by !== 'kuota_desc') params.set('sort_by', state.sort_by);
    if (includePagination) {
      if (state.page > 1) params.set('page', String(state.page));
      if (state.limit !== 10) params.set('limit', String(state.limit));
    }
    if (includeDetail && activeDetailId) {
      params.set('detail', String(activeDetailId));
    }
    return params;
  }

  function syncStateToUrl() {
    const params = buildFilterParams(true, true);
    const qs = params.toString();
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    try {
      window.history.replaceState(null, '', newUrl);
    } catch (_e) {
      // Ignore SecurityError under restricted file:// contexts
    }
  }

  function initStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('q')) state.q = params.get('q').trim();
    if (params.has('jurusan')) state.jurusan = params.get('jurusan').trim();
    if (params.has('jurusan_id')) {
      const jid = Number(params.get('jurusan_id'));
      state.jurusan_id = Number.isFinite(jid) && jid > 0 ? jid : null;
    }
    if (params.has('jenjang')) state.jenjang = params.get('jenjang') || 'ALL';
    if (params.has('kategori_instansi')) state.kategori_instansi = params.get('kategori_instansi') || 'ALL';
    if (params.has('instansi_id')) state.instansi_id = params.get('instansi_id') || 'ALL';
    if (params.has('instansi_nama')) state.instansi_nama = params.get('instansi_nama') || '';
    if (params.has('jenis_formasi')) state.jenis_formasi = params.get('jenis_formasi') || 'ALL';
    if (params.has('status_keketatan')) state.status_keketatan = params.get('status_keketatan') || 'ALL';
    if (params.get('zero_applicant_only') === 'true') {
      state.zero_applicant_only = true;
      if (state.status_keketatan === 'ALL') state.status_keketatan = 'Tanpa Pelamar';
    } else if (state.status_keketatan === 'Tanpa Pelamar') {
      state.zero_applicant_only = true;
    }
    if (params.has('gaji_min')) {
      const gm = Number(params.get('gaji_min'));
      state.gaji_min = Number.isFinite(gm) && gm >= 0 ? gm : 0;
    }
    if (params.has('sort_by')) state.sort_by = params.get('sort_by') || 'kuota_desc';
    if (params.has('page')) {
      const pg = Number(params.get('page'));
      state.page = Number.isFinite(pg) && pg >= 1 ? pg : 1;
    }
    if (params.has('limit')) {
      const lim = Number(params.get('limit'));
      state.limit = [10, 25, 50, 100].includes(lim) ? lim : 10;
    }
    return params.get('detail') || null;
  }

  function countActiveSecondaryFilters() {
    let count = 0;
    if (state.q) count += 1;
    if (state.jenjang !== 'ALL') count += 1;
    if (state.kategori_instansi !== 'ALL') count += 1;
    if (state.instansi_id !== 'ALL') count += 1;
    if (state.jenis_formasi !== 'ALL') count += 1;
    if (state.status_keketatan !== 'ALL') count += 1;
    if (state.gaji_min > 0) count += 1;
    if (state.sort_by !== 'kuota_desc') count += 1;
    return count;
  }

  function syncControlsFromState() {
    const inputQ = document.getElementById('filter-q');
    const btnClearQ = document.getElementById('btn-clear-q');
    if (inputQ) inputQ.value = state.q;
    if (btnClearQ) btnClearQ.classList.toggle('is-hidden', !state.q);

    const inputJurusan = document.getElementById('filter-jurusan-input');
    const btnClearJurusan = document.getElementById('btn-clear-jurusan');
    if (inputJurusan) inputJurusan.value = state.jurusan;
    if (btnClearJurusan) btnClearJurusan.classList.toggle('is-hidden', !state.jurusan);

    const elJenjang = document.getElementById('filter-jenjang');
    if (elJenjang) elJenjang.value = state.jenjang;
    const elKat = document.getElementById('filter-kategori-instansi');
    if (elKat) elKat.value = state.kategori_instansi;
    const elJenis = document.getElementById('filter-jenis-formasi');
    if (elJenis) elJenis.value = state.jenis_formasi;
    const elKet = document.getElementById('filter-status-keketatan');
    if (elKet) elKet.value = state.status_keketatan;

    const btnZero = document.getElementById('btn-toggle-zero');
    if (btnZero) btnZero.classList.toggle('is-active', state.zero_applicant_only);
    const tickerZero = document.getElementById('card-zero-applicants');
    if (tickerZero) tickerZero.classList.toggle('is-active', state.zero_applicant_only);

    const sliderGaji = document.getElementById('filter-gaji-min-range');
    const labelGaji = document.getElementById('label-gaji-min');
    if (sliderGaji) sliderGaji.value = String(state.gaji_min);
    if (labelGaji) {
      labelGaji.textContent = state.gaji_min === 0 ? 'Semua (Rp 0)' : `≥ ${formatJuta(state.gaji_min)}`;
    }

    const elSort = document.getElementById('filter-sort-by');
    if (elSort) elSort.value = state.sort_by;
    const elPageSize = document.getElementById('table-page-size');
    if (elPageSize) elPageSize.value = String(state.limit);

    const hiddenInstansi = document.getElementById('filter-instansi-id');
    const inputInstansi = document.getElementById('filter-instansi-input');
    const btnClearInstansi = document.getElementById('btn-clear-instansi');
    if (hiddenInstansi) hiddenInstansi.value = state.instansi_id;
    if (inputInstansi && btnClearInstansi) {
      if (state.instansi_id !== 'ALL') {
        const match = allInstansi.find(i => String(i.instansi_id) === String(state.instansi_id));
        if (match) state.instansi_nama = match.nama_instansi;
        inputInstansi.value = state.instansi_nama || String(state.instansi_id);
        btnClearInstansi.classList.remove('is-hidden');
      } else {
        inputInstansi.value = '';
        btnClearInstansi.classList.add('is-hidden');
      }
    }

    const mobileCount = document.getElementById('mobile-filter-count');
    if (mobileCount) {
      const sec = countActiveSecondaryFilters();
      mobileCount.textContent = String(sec);
      mobileCount.classList.toggle('is-hidden', sec === 0);
    }

    updateInstansiPlaceholder();
  }

  // =========================================================================
  // 1. NATIONAL STATS & INTERACTIVE ANALYTICS DRAWER
  // =========================================================================
  async function loadStats() {
    try {
      const resp = await fetch(`${API_BASE}/api/stats`);
      if (!resp.ok) throw new Error(`Stats fetch failed (${resp.status})`);
      const data = await resp.json();
      statsCache = data;

      document.getElementById('kpi-total-formasi').textContent = Number(data.total_formasi || 0).toLocaleString('id-ID');
      document.getElementById('kpi-total-kuota').textContent = Number(data.total_kuota || 0).toLocaleString('id-ID');
      document.getElementById('kpi-total-pelamar').textContent = Number(data.total_pelamar || 0).toLocaleString('id-ID');
      document.getElementById('kpi-avg-rasio').textContent = `1 : ${data.avg_rasio_kompetisi || 0}`;
      document.getElementById('kpi-formasi-kosong').textContent = Number(data.total_formasi_kosong || 0).toLocaleString('id-ID');

      const medMin = formatJuta(data.gaji_median_min);
      const medMax = formatJuta(data.gaji_median_max);
      document.getElementById('kpi-median-gaji').textContent = `${medMin} – ${medMax}`;

      renderAnalyticsCards(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  }

  function renderAnalyticsCards(data) {
    if (!data) return;
    const totalFormasi = Math.max(1, Number(data.total_formasi || 1));

    const keketatanContainer = document.getElementById('analytics-keketatan-bars');
    if (keketatanContainer) {
      const keketatanOrder = [
        { key: 'Tanpa Pelamar', label: 'Tanpa Pelamar (0 Pelamar)', fillClass: 'fill-loose' },
        { key: 'Sangat Longgar', label: 'Sangat Longgar (≤ 1.0)', fillClass: 'fill-loose' },
        { key: 'Moderat', label: 'Moderat (1.1 – 15.0)', fillClass: 'fill-mod' },
        { key: 'Sangat Ketat', label: 'Sangat Ketat (> 15.0)', fillClass: 'fill-tight' }
      ];
      const kekMap = new Map((data.keketatan_stats || []).map(x => [x.status, x]));
      keketatanContainer.innerHTML = '';

      keketatanOrder.forEach(tier => {
        const stat = kekMap.get(tier.key) || { count: 0, kuota: 0, pelamar: 0 };
        const pct = (stat.count / totalFormasi) * 100;
        const isActive = state.status_keketatan === tier.key;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `dist-row-btn${isActive ? ' is-active' : ''}`;
        btn.innerHTML = `
          <div class="dist-row-top">
            <span style="font-weight:600;color:var(--color-text-primary);">${escapeHtml(tier.label)}</span>
            <span class="mono" style="color:var(--color-text-secondary);">
              <strong>${Number(stat.count || 0).toLocaleString('id-ID')}</strong>
              <span style="color:var(--color-text-muted);">(${pct.toFixed(1)}%)</span>
            </span>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill ${tier.fillClass}" style="width:${Math.max(pct, 1.5)}%"></div>
          </div>
          <div class="dist-row-sub">
            <span>Kuota: ${Number(stat.kuota || 0).toLocaleString('id-ID')}</span>
            <span>Pelamar: ${Number(stat.pelamar || 0).toLocaleString('id-ID')}</span>
          </div>
        `;
        btn.addEventListener('click', () => {
          const nextVal = state.status_keketatan === tier.key ? 'ALL' : tier.key;
          state.status_keketatan = nextVal;
          state.zero_applicant_only = nextVal === 'Tanpa Pelamar';
          state.page = 1;
          syncControlsFromState();
          syncStateToUrl();
          updateActiveChips();
          renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
          loadFormasiTable();
        });
        keketatanContainer.appendChild(btn);
      });
    }

    const jenisContainer = document.getElementById('analytics-jenis-bars');
    if (jenisContainer) {
      const golMeta = {
        'III/a': { label: 'Gol. III/a · S-1 / D-IV', jenjang: 'S-1' },
        'II/c': { label: 'Gol. II/c · Diploma III', jenjang: 'D-III' },
        'III/b': { label: 'Gol. III/b · S-2 / Profesi', jenjang: 'S-2' },
        'II/a': { label: 'Gol. II/a · SMA / SMK', jenjang: 'SMA/SMK' },
        'III/c': { label: 'Gol. III/c · S-3 / Spesialis', jenjang: 'S-3/Spesialis' }
      };
      const golList = [...(data.golongan_stats || [])].sort((a, b) => (b.count || 0) - (a.count || 0));
      jenisContainer.innerHTML = '';

      golList.forEach(item => {
        const pct = ((item.count || 0) / totalFormasi) * 100;
        const meta = golMeta[item.golongan] || { label: `Gol. ${item.golongan || '-'}`, jenjang: 'ALL' };
        const isActive = meta.jenjang !== 'ALL' && state.jenjang === meta.jenjang;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `dist-row-btn${isActive ? ' is-active' : ''}`;
        btn.innerHTML = `
          <div class="dist-row-top">
            <span style="font-weight:600;color:var(--color-text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(meta.label)}">${escapeHtml(meta.label)}</span>
            <span class="mono" style="color:var(--color-text-secondary);flex-shrink:0;">
              ${Number(item.count || 0).toLocaleString('id-ID')} <span style="color:var(--color-text-muted);">(${pct.toFixed(1)}%)</span>
            </span>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width:${Math.max(pct, 1.5)}%"></div>
          </div>
          <div class="dist-row-sub">
            <span>Kuota: ${Number(item.kuota || 0).toLocaleString('id-ID')}</span>
            <span>Pelamar: ${Number(item.pelamar || 0).toLocaleString('id-ID')}</span>
          </div>
        `;
        btn.addEventListener('click', () => {
          if (meta.jenjang === 'ALL') return;
          state.jenjang = state.jenjang === meta.jenjang ? 'ALL' : meta.jenjang;
          state.page = 1;
          syncControlsFromState();
          syncStateToUrl();
          updateActiveChips();
          renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
          loadFormasiTable();
        });
        jenisContainer.appendChild(btn);
      });
    }

    const totalInstansiEl = document.getElementById('analytics-instansi-total');
    if (totalInstansiEl) {
      totalInstansiEl.textContent = `${Number(data.total_instansi || 0).toLocaleString('id-ID')} Instansi`;
    }
    const katContainer = document.getElementById('analytics-instansi-kategori');
    if (katContainer) {
      const katMap = data.instansi_by_kategori || {};
      const katDefs = [
        { key: 'Pusat', label: 'Pusat (K/L)' },
        { key: 'Provinsi', label: 'Provinsi' },
        { key: 'Kabupaten/Kota', label: 'Kab / Kota' }
      ];
      katContainer.innerHTML = '';
      katDefs.forEach(k => {
        const cnt = katMap[k.key] || 0;
        const isActive = state.kategori_instansi === k.key;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `scope-stat-btn${isActive ? ' is-active' : ''}`;
        btn.innerHTML = `
          <div class="scope-stat-num">${Number(cnt).toLocaleString('id-ID')}</div>
          <div class="scope-stat-lbl">${escapeHtml(k.label)}</div>
        `;
        btn.title = `Filter instansi lingkup ${k.key}`;
        btn.addEventListener('click', () => {
          const nextKat = state.kategori_instansi === k.key ? 'ALL' : k.key;
          handleKategoriInstansiChange(nextKat);
        });
        katContainer.appendChild(btn);
      });
    }
  }

  function buildTopAnalyticsSignature() {
    const p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.jurusan_id) p.set('jurusan_id', String(state.jurusan_id));
    else if (state.jurusan) p.set('jurusan', state.jurusan);
    if (state.jenjang !== 'ALL') p.set('jenjang', state.jenjang);
    if (state.kategori_instansi !== 'ALL') p.set('kategori_instansi', state.kategori_instansi);
    if (state.instansi_id !== 'ALL') p.set('instansi_id', String(state.instansi_id));
    if (state.jenis_formasi !== 'ALL') p.set('jenis_formasi', state.jenis_formasi);
    if (state.status_keketatan !== 'ALL') p.set('status_keketatan', state.status_keketatan);
    if (state.zero_applicant_only) p.set('zero_applicant_only', 'true');
    if (state.gaji_min > 0) p.set('gaji_min', String(state.gaji_min));
    p.set('limit', '10');
    return p.toString();
  }

  async function loadTopAnalyticsIfOpen(force = false) {
    if (!isAnalyticsOpen) return;
    const sig = buildTopAnalyticsSignature();
    if (!force && sig === lastTopAnalyticsSignature) return;

    const jBox = document.getElementById('analytics-top-jurusan-bars');
    const iBox = document.getElementById('analytics-top-instansi-bars');
    if (!jBox || !iBox) return;

    if (topAnalyticsAbortController) topAnalyticsAbortController.abort();
    const controller = new AbortController();
    topAnalyticsAbortController = controller;

    if (!lastTopAnalyticsSignature) {
      jBox.innerHTML = '<div class="top-chart-empty">Memuat Top 10 program studi...</div>';
      iBox.innerHTML = '<div class="top-chart-empty">Memuat Top 10 instansi...</div>';
    }

    try {
      const resp = await fetch(`${API_BASE}/api/analytics/top?${sig}`, {
        signal: controller.signal
      });
      if (!resp.ok) throw new Error(`Top analytics failed (${resp.status})`);
      const data = await resp.json();
      lastTopAnalyticsSignature = sig;
      activeAnalyticsSnapshot = data;
      renderTopAnalyticsCharts(data);
      renderAnalyticsCards(data);
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Error loading top analytics:', err);
      jBox.innerHTML = '<div class="top-chart-empty">Gagal memuat grafik program studi.</div>';
      iBox.innerHTML = '<div class="top-chart-empty">Gagal memuat grafik instansi.</div>';
    }
  }

  function renderTopAnalyticsCharts(data) {
    const jBox = document.getElementById('analytics-top-jurusan-bars');
    const iBox = document.getElementById('analytics-top-instansi-bars');
    const jMeta = document.getElementById('top-jurusan-meta');
    const iMeta = document.getElementById('top-instansi-meta');
    if (!jBox || !iBox) return;

    const scopeNote = data && data.is_filtered ? 'Sesuai filter · klik untuk pilih' : 'Nasional · klik untuk pilih';
    if (jMeta) jMeta.textContent = scopeNote;
    if (iMeta) iMeta.textContent = scopeNote;

    const jurusanItems = (data && data.top_jurusan) || [];
    jBox.innerHTML = '';
    if (!jurusanItems.length) {
      jBox.innerHTML = '<div class="top-chart-empty">Tidak ada program studi pada kombinasi filter ini.</div>';
    } else {
      const maxKuotaJ = Math.max(...jurusanItems.map(x => x.total_kuota || 0), 1);
      jurusanItems.forEach((item, idx) => {
        const pct = Math.max(4, Math.round(((item.total_kuota || 0) / maxKuotaJ) * 100));
        const isSelected =
          (state.jurusan_id && String(state.jurusan_id) === String(item.jurusan_id)) ||
          (!state.jurusan_id && state.jurusan && state.jurusan.toUpperCase() === String(item.nama_jurusan).toUpperCase());
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `top-chart-btn${isSelected ? ' is-active' : ''}`;
        btn.title = `${item.nama_jurusan} (${item.jenjang || '-'}) — Klik untuk memfilter`;
        btn.innerHTML = `
          <div class="top-chart-head">
            <span class="top-chart-label-wrap">
              <span class="top-chart-rank">${String(idx + 1).padStart(2, '0')}</span>
              <span class="top-chart-name">${escapeHtml(item.nama_jurusan)}</span>
              <span class="field-badge">${escapeHtml(item.jenjang || '-')}</span>
            </span>
            <span class="top-chart-val">${Number(item.total_kuota || 0).toLocaleString('id-ID')}\u00A0Kursi</span>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width:${pct}%"></div>
          </div>
          <div class="top-chart-sub">
            <span>${Number(item.total_formasi || 0).toLocaleString('id-ID')}\u00A0formasi · ${Number(item.total_pelamar || 0).toLocaleString('id-ID')}\u00A0pelamar</span>
            <span style="white-space:nowrap;flex-shrink:0;">Maks\u00A0~${formatJuta(item.avg_gaji_max)}</span>
          </div>
        `;
        btn.addEventListener('click', () => {
          const inputJurusan = document.getElementById('filter-jurusan-input');
          const btnClearJurusan = document.getElementById('btn-clear-jurusan');
          if (isSelected) {
            state.jurusan_id = null;
            state.jurusan = '';
            if (inputJurusan) inputJurusan.value = '';
            if (btnClearJurusan) btnClearJurusan.classList.add('is-hidden');
          } else {
            state.jurusan_id = item.jurusan_id;
            state.jurusan = item.nama_jurusan;
            if (inputJurusan) inputJurusan.value = item.nama_jurusan;
            if (btnClearJurusan) btnClearJurusan.classList.remove('is-hidden');
          }
          state.page = 1;
          syncControlsFromState();
          updateActiveChips();
          lastTopAnalyticsSignature = null;
          loadFormasiTable();
        });
        jBox.appendChild(btn);
      });
    }

    const instansiItems = (data && data.top_instansi) || [];
    iBox.innerHTML = '';
    if (!instansiItems.length) {
      iBox.innerHTML = '<div class="top-chart-empty">Tidak ada instansi pada kombinasi filter ini.</div>';
    } else {
      const maxKuotaI = Math.max(...instansiItems.map(x => x.total_kuota || 0), 1);
      instansiItems.forEach((item, idx) => {
        const pct = Math.max(4, Math.round(((item.total_kuota || 0) / maxKuotaI) * 100));
        const isSelected = String(state.instansi_id) === String(item.instansi_id);
        const shortScope = item.kategori_instansi === 'Kabupaten/Kota' ? 'Kab/Kota' : (item.kategori_instansi || '-');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `top-chart-btn${isSelected ? ' is-active' : ''}`;
        btn.title = `${item.nama_instansi} (${shortScope}) — Klik untuk memfilter`;
        btn.innerHTML = `
          <div class="top-chart-head">
            <span class="top-chart-label-wrap">
              <span class="top-chart-rank">${String(idx + 1).padStart(2, '0')}</span>
              <span class="top-chart-name">${escapeHtml(item.nama_instansi)}</span>
              <span class="field-badge">${escapeHtml(shortScope)}</span>
            </span>
            <span class="top-chart-val">${Number(item.total_kuota || 0).toLocaleString('id-ID')}\u00A0Kursi</span>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width:${pct}%"></div>
          </div>
          <div class="top-chart-sub">
            <span>${Number(item.total_formasi || 0).toLocaleString('id-ID')}\u00A0formasi · ${Number(item.total_pelamar || 0).toLocaleString('id-ID')}\u00A0pelamar</span>
            <span style="white-space:nowrap;flex-shrink:0;">Maks\u00A0~${formatJuta(item.avg_gaji_max)}</span>
          </div>
        `;
        btn.addEventListener('click', () => {
          if (isSelected) {
            clearSelectedInstansi(true);
            lastTopAnalyticsSignature = null;
            loadTopAnalyticsIfOpen(true);
          } else {
            lastTopAnalyticsSignature = null;
            selectInstansiOption({
              instansi_id: item.instansi_id,
              nama_instansi: item.nama_instansi,
              kategori_instansi: item.kategori_instansi
            });
          }
        });
        iBox.appendChild(btn);
      });
    }
  }

  function updateDynamicSummary(summary, fallbackTotal = 0) {
    const s = summary || {};
    const totalFormasi = s.total_formasi !== undefined ? s.total_formasi : fallbackTotal;
    const elTotal = document.getElementById('summary-total-formasi');
    if (elTotal) elTotal.textContent = Number(totalFormasi || 0).toLocaleString('id-ID');
    const elKuota = document.getElementById('summary-total-kuota');
    if (elKuota) elKuota.textContent = s.total_kuota !== undefined ? Number(s.total_kuota).toLocaleString('id-ID') : '---';
    const elPelamar = document.getElementById('summary-total-pelamar');
    if (elPelamar) elPelamar.textContent = s.total_pelamar !== undefined ? Number(s.total_pelamar).toLocaleString('id-ID') : '---';
    const elRasio = document.getElementById('summary-avg-rasio');
    if (elRasio) elRasio.textContent = s.avg_rasio_kompetisi !== undefined ? `1 : ${s.avg_rasio_kompetisi}` : '1 : ---';
    const elKosong = document.getElementById('summary-formasi-kosong');
    if (elKosong) elKosong.textContent = s.total_formasi_kosong !== undefined ? Number(s.total_formasi_kosong).toLocaleString('id-ID') : '---';
  }

  function applyStrategicPreset(presetKey) {
    state.q = '';
    state.jurusan = '';
    state.jurusan_id = null;
    state.jenjang = 'ALL';
    state.kategori_instansi = 'ALL';
    state.instansi_id = 'ALL';
    state.instansi_nama = '';
    state.jenis_formasi = 'ALL';
    state.status_keketatan = 'ALL';
    state.zero_applicant_only = false;
    state.gaji_min = 0;
    state.sort_by = 'kuota_desc';
    state.page = 1;

    if (presetKey === 's1-zero') {
      state.jenjang = 'S-1';
      state.zero_applicant_only = true;
      state.status_keketatan = 'Tanpa Pelamar';
      state.sort_by = 'kuota_desc';
    } else if (presetKey === 'high-salary-loose') {
      state.gaji_min = 10000000;
      state.status_keketatan = 'Sangat Longgar';
      state.sort_by = 'gaji_max_desc';
    } else if (presetKey === 'pusat-loose') {
      state.kategori_instansi = 'Pusat';
      state.status_keketatan = 'Sangat Longgar';
      state.sort_by = 'rasio_asc';
    }

    syncControlsFromState();
    syncStateToUrl();
    updateActiveChips();
    if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
    loadFormasiTable();
  }

  // =========================================================================
  // 2. FILTER OPTIONS & CASCADING INSTANSI COMBOBOX
  // =========================================================================
  function getFilteredInstansiList() {
    if (state.kategori_instansi === 'ALL') return allInstansi;
    return allInstansi.filter(ins => ins.kategori_instansi === state.kategori_instansi);
  }

  function updateInstansiPlaceholder() {
    const filtered = getFilteredInstansiList();
    const inputInstansi = document.getElementById('filter-instansi-input');
    const countBadge = document.getElementById('instansi-count-badge');
    if (!inputInstansi || !countBadge) return;

    if (state.kategori_instansi === 'ALL') {
      inputInstansi.placeholder = `Cari dari ${filtered.length} instansi...`;
      countBadge.textContent = `${filtered.length} instansi`;
    } else {
      const scopeShort = state.kategori_instansi === 'Kabupaten/Kota' ? 'Kab/Kota' : state.kategori_instansi;
      inputInstansi.placeholder = `Cari dari ${filtered.length} instansi ${scopeShort}...`;
      countBadge.textContent = `${filtered.length} ${scopeShort}`;
    }
  }

  function renderInstansiDropdown(queryTerm = '') {
    const listEl = document.getElementById('instansi-autocomplete-list');
    if (!listEl) return;
    const filteredByScope = getFilteredInstansiList();
    const term = queryTerm.trim().toLowerCase();

    const matches = term
      ? filteredByScope.filter(ins => ins.nama_instansi.toLowerCase().includes(term))
      : filteredByScope;

    listEl.innerHTML = '';

    if (matches.length === 0) {
      listEl.innerHTML = '<div class="autocomplete-empty">Tidak ada instansi yang cocok</div>';
      listEl.classList.remove('is-hidden');
      return;
    }

    const maxShow = 80;
    matches.slice(0, maxShow).forEach(ins => {
      const div = document.createElement('div');
      const isSelected = String(state.instansi_id) === String(ins.instansi_id);
      div.className = `autocomplete-item${isSelected ? ' is-selected' : ''}`;
      const shortScope = ins.kategori_instansi === 'Kabupaten/Kota' ? 'Kab/Kota' : ins.kategori_instansi;
      div.innerHTML = `
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(ins.nama_instansi)}">${escapeHtml(ins.nama_instansi)}</span>
        <span class="field-badge">${escapeHtml(shortScope)}</span>
      `;
      div.addEventListener('click', () => selectInstansiOption(ins));
      listEl.appendChild(div);
    });

    if (matches.length > maxShow) {
      const note = document.createElement('div');
      note.className = 'autocomplete-empty';
      note.textContent = `Menampilkan ${maxShow} dari ${matches.length} instansi — ketik untuk mempersempit`;
      listEl.appendChild(note);
    }

    listEl.classList.remove('is-hidden');
  }

  function selectInstansiOption(ins) {
    state.instansi_id = String(ins.instansi_id);
    state.instansi_nama = ins.nama_instansi;
    state.page = 1;

    document.getElementById('filter-instansi-input').value = ins.nama_instansi;
    document.getElementById('filter-instansi-id').value = String(ins.instansi_id);
    document.getElementById('btn-clear-instansi').classList.remove('is-hidden');
    document.getElementById('instansi-autocomplete-list').classList.add('is-hidden');

    syncControlsFromState();
    syncStateToUrl();
    updateActiveChips();
    loadFormasiTable();
  }

  function clearSelectedInstansi(triggerReload = true) {
    state.instansi_id = 'ALL';
    state.instansi_nama = '';
    document.getElementById('filter-instansi-input').value = '';
    document.getElementById('filter-instansi-id').value = 'ALL';
    document.getElementById('btn-clear-instansi').classList.add('is-hidden');
    document.getElementById('instansi-autocomplete-list').classList.add('is-hidden');

    if (triggerReload) {
      state.page = 1;
      syncControlsFromState();
      syncStateToUrl();
      updateActiveChips();
      loadFormasiTable();
    }
  }

  function handleKategoriInstansiChange(newKategori) {
    state.kategori_instansi = newKategori;
    document.getElementById('filter-kategori-instansi').value = newKategori;

    if (state.instansi_id !== 'ALL' && newKategori !== 'ALL') {
      const currentAgency = allInstansi.find(i => String(i.instansi_id) === String(state.instansi_id));
      if (currentAgency && currentAgency.kategori_instansi !== newKategori) {
        clearSelectedInstansi(false);
      }
    }

    updateInstansiPlaceholder();
    state.page = 1;
    syncControlsFromState();
    syncStateToUrl();
    updateActiveChips();
    if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
    loadFormasiTable();
  }

  async function loadFilterOptions() {
    try {
      const resp = await fetch(`${API_BASE}/api/filters`);
      if (!resp.ok) throw new Error(`Filters fetch failed (${resp.status})`);
      const data = await resp.json();

      const selJenjang = document.getElementById('filter-jenjang');
      selJenjang.innerHTML = '<option value="ALL">Semua Jenjang</option>';
      (data.jenjang || []).forEach(j => {
        const opt = document.createElement('option');
        opt.value = j;
        opt.textContent = j;
        selJenjang.appendChild(opt);
      });

      const selJenis = document.getElementById('filter-jenis-formasi');
      selJenis.innerHTML = '<option value="ALL">Semua Jalur</option>';
      (data.jenis_formasi || []).forEach(jf => {
        const opt = document.createElement('option');
        opt.value = jf;
        opt.textContent = jf;
        selJenis.appendChild(opt);
      });

      allInstansi = data.instansi || [];
      syncControlsFromState();
      updateActiveChips();
    } catch (err) {
      console.error('Error loading filter options:', err);
    }
  }

  // =========================================================================
  // 3. FORMATION TABLE & MOBILE CARDS
  // =========================================================================
  async function loadFormasiTable() {
    const spinner = document.getElementById('table-loading-spinner');
    const tableBody = document.getElementById('table-body');
    const emptyState = document.getElementById('table-empty-state');

    if (tableAbortController) tableAbortController.abort();
    const controller = new AbortController();
    tableAbortController = controller;

    if (spinner) spinner.classList.remove('is-hidden');
    syncStateToUrl();
    loadTopAnalyticsIfOpen();

    try {
      const params = new URLSearchParams();
      if (state.q) params.set('q', state.q);
      if (state.jurusan_id) {
        params.set('jurusan_id', state.jurusan_id);
      } else if (state.jurusan) {
        params.set('jurusan', state.jurusan);
      }
      if (state.jenjang !== 'ALL') params.set('jenjang', state.jenjang);
      if (state.kategori_instansi !== 'ALL') params.set('kategori_instansi', state.kategori_instansi);
      if (state.instansi_id !== 'ALL') params.set('instansi_id', state.instansi_id);
      if (state.jenis_formasi !== 'ALL') params.set('jenis_formasi', state.jenis_formasi);
      if (state.status_keketatan !== 'ALL') params.set('status_keketatan', state.status_keketatan);
      if (state.zero_applicant_only) params.set('zero_applicant_only', 'true');
      if (state.gaji_min > 0) params.set('gaji_min', state.gaji_min);
      params.set('sort_by', state.sort_by);
      params.set('page', state.page);
      params.set('limit', state.limit);

      const resp = await fetch(`${API_BASE}/api/formasi?${params.toString()}`, {
        signal: controller.signal
      });
      if (!resp.ok) throw new Error(`Table fetch failed (${resp.status})`);
      const data = await resp.json();

      const matchCountEl = document.getElementById('filter-total-count');
      if (matchCountEl) matchCountEl.textContent = Number(data.total || 0).toLocaleString('id-ID');
      updateDynamicSummary(data.summary, data.total);

      if (!data.items || data.items.length === 0) {
        lastLoadedItems = [];
        tableBody.innerHTML = '';
        const cardsContainer = document.getElementById('mobile-cards-container');
        if (cardsContainer) cardsContainer.innerHTML = '';
        emptyState.classList.remove('is-hidden');
        document.getElementById('desktop-table-wrapper').classList.add('is-hidden');
        if (cardsContainer) cardsContainer.classList.add('is-hidden');
        renderPagination(0, 1, state.limit, 1);
        return;
      }

      emptyState.classList.add('is-hidden');
      data.items.forEach(it => loadedFormasiMap.set(String(it.formasi_id), it));
      lastLoadedItems = data.items;
      lastLoadedStartIdx = (data.page - 1) * data.limit + 1;
      applyTableViewVisibility();
      renderTableRows(lastLoadedItems, lastLoadedStartIdx);
      renderMobileCards(lastLoadedItems, lastLoadedStartIdx);
      renderPagination(data.total, data.page, data.limit, data.total_pages);
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Error loading formasi table:', err);
      showToast('Gagal memuat daftar formasi. Periksa koneksi lalu coba kembali.', 'warn');
    } finally {
      if (tableAbortController === controller && spinner) {
        spinner.classList.add('is-hidden');
      }
    }
  }

  function getScopeBadge(scope) {
    if (scope === 'Pusat') {
      return '<span class="badge badge-accent">Pusat</span>';
    }
    if (scope === 'Provinsi') {
      return '<span class="badge badge-neutral">Provinsi</span>';
    }
    return '<span class="badge badge-neutral">Kab/Kota</span>';
  }

  function getJenisBadge(jenis) {
    if (jenis === 'CUMLAUDE') {
      return '<span class="badge badge-accent">Cumlaude</span>';
    }
    if (jenis === 'PENYANDANG DISABILITAS') {
      return '<span class="badge badge-accent">Disabilitas</span>';
    }
    if (jenis && jenis.includes('PAPUA')) {
      return '<span class="badge badge-accent">Putra/Putri Papua</span>';
    }
    if (jenis && jenis !== 'UMUM') {
      return `<span class="badge badge-accent">${escapeHtml(jenis)}</span>`;
    }
    return '<span class="badge badge-neutral">Umum</span>';
  }

  function getKeketatanBadge(status, peluang) {
    if (status === 'Tanpa Pelamar') {
      return '<span class="badge badge-loose">0 Pelamar · 100%</span>';
    }
    if (status === 'Sangat Longgar') {
      return `<span class="badge badge-loose">Longgar · ${peluang}%</span>`;
    }
    if (status === 'Moderat') {
      return `<span class="badge badge-mod">Moderat · ${peluang}%</span>`;
    }
    return `<span class="badge badge-tight">Ketat · ${peluang}%</span>`;
  }

  function scrollToResultsSection() {
    const el = document.getElementById('section-table');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function applyTableViewVisibility() {
    const cardsBtn = document.getElementById('btn-view-cards');
    const tableBtn = document.getElementById('btn-view-table');
    const cardsEl = document.getElementById('mobile-cards-container');
    const tableWrapper = document.getElementById('desktop-table-wrapper');
    const hintEl = document.getElementById('mobile-table-scroll-hint');
    const emptyEl = document.getElementById('table-empty-state');
    const isEmpty = emptyEl && !emptyEl.classList.contains('is-hidden');

    if (cardsBtn && tableBtn) {
      cardsBtn.classList.toggle('is-active', tableViewMode === 'cards');
      tableBtn.classList.toggle('is-active', tableViewMode === 'table');
    }
    if (hintEl) {
      hintEl.classList.toggle('is-hidden', tableViewMode !== 'table');
    }
    if (!isEmpty && cardsEl && tableWrapper) {
      cardsEl.classList.toggle('is-hidden', tableViewMode !== 'cards');
      tableWrapper.classList.toggle('is-hidden', tableViewMode === 'cards');
    }
  }

  function setTableViewMode(mode, isUserAction = true) {
    if (isUserAction) userForcedViewMode = true;
    tableViewMode = mode === 'cards' ? 'cards' : 'table';
    applyTableViewVisibility();
  }

  function renderMajorTagsHtml(majors, safeId) {
    const list = majors || [];
    if (!list.length) {
      return '<span style="color:var(--color-text-muted);font-size:0.75rem;">Semua Jurusan Relevan</span>';
    }
    let html = '';
    list.slice(0, 2).forEach(m => {
      html += `<span class="major-tag">${escapeHtml(m)}</span>`;
    });
    if (list.length > 2) {
      html += `<button type="button" class="major-more-btn" data-open-detail="${safeId}">+${list.length - 2} prodi</button>`;
    }
    return html;
  }

  function renderTableRows(items, startIdx) {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    items.forEach((item, idx) => {
      const row = document.createElement('tr');
      const rowNum = startIdx + idx;
      const scopeBadge = getScopeBadge(item.kategori_instansi);
      const jenisBadge = getJenisBadge(item.jenis_formasi);
      const keketatanBadge = getKeketatanBadge(item.status_keketatan, item.peluang_lolos_pct);
      const bookmarked = isBookmarked(item.formasi_id);
      const safeId = escapeHtml(item.formasi_id);
      const majorHtml = renderMajorTagsHtml(item.jurusan_list, safeId);
      const locText = cleanLocation(item.lokasi_nm);

      row.innerHTML = `
        <td>
          <div style="display:flex;align-items:flex-start;gap:8px;">
            <span class="row-idx">${rowNum}.</span>
            <div>
              <div class="jabatan-title">${escapeHtml(item.jabatan_nm)}</div>
              <div class="jabatan-meta">
                ${jenisBadge}
                <span class="uuid-code">${safeId}</span>
              </div>
            </div>
          </div>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
            <span class="agency-name">${escapeHtml(item.nama_instansi)}</span>
            ${scopeBadge}
          </div>
          <div class="location-line" title="${escapeHtml(locText)}">
            ${ICONS.pin}
            <span>${escapeHtml(locText)}</span>
          </div>
        </td>
        <td>
          <div class="major-tag-list">${majorHtml}</div>
        </td>
        <td class="col-num">
          <div class="quota-num">${Number(item.jumlah_formasi || 0).toLocaleString('id-ID')}\u00A0Kursi</div>
          <div class="applicant-num">${Number(item.jumlah_pelamar || 0).toLocaleString('id-ID')}\u00A0Pelamar</div>
        </td>
        <td>
          <div class="ratio-num">1 : ${item.rasio_kompetisi}</div>
          <div style="margin-top:4px;">${keketatanBadge}</div>
        </td>
        <td>
          <div class="salary-range">${formatJuta(item.gaji_min)} – ${formatJuta(item.gaji_max)}</div>
          <div class="salary-sub">Gol. ${escapeHtml(item.golongan_awal || '-')} · Pokok 80% ${formatJuta(item.gaji_pokok_cpns_80)}</div>
        </td>
        <td class="col-center">
          <div class="row-actions">
            <button
              type="button"
              class="bookmark-btn${bookmarked ? ' is-saved' : ''}"
              data-bookmark-id="${safeId}"
              title="Simpan ke perbandingan"
              aria-label="Simpan formasi untuk dibandingkan"
            >${bookmarked ? ICONS.starFilled : ICONS.starOutline}</button>
            <button
              type="button"
              class="btn btn-primary btn-sm"
              data-open-detail="${safeId}"
            >${ICONS.eye}<span>Detail</span></button>
          </div>
        </td>
      `;
      tbody.appendChild(row);
    });
  }

  function renderMobileCards(items, startIdx) {
    const container = document.getElementById('mobile-cards-container');
    if (!container) return;
    container.innerHTML = '';

    items.forEach((item, idx) => {
      const card = document.createElement('article');
      card.className = 'formation-card';
      const rowNum = startIdx + idx;
      const scopeBadge = getScopeBadge(item.kategori_instansi);
      const jenisBadge = getJenisBadge(item.jenis_formasi);
      const keketatanBadge = getKeketatanBadge(item.status_keketatan, item.peluang_lolos_pct);
      const bookmarked = isBookmarked(item.formasi_id);
      const safeId = escapeHtml(item.formasi_id);
      const majorHtml = renderMajorTagsHtml(item.jurusan_list, safeId);
      const locText = cleanLocation(item.lokasi_nm);

      card.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div class="formation-card-top">
            <div style="min-width:0;">
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px;">
                <span class="row-idx">#${rowNum}</span>
                ${jenisBadge}
                ${scopeBadge}
              </div>
              <h3 class="jabatan-title">${escapeHtml(item.jabatan_nm)}</h3>
            </div>
            <button
              type="button"
              class="bookmark-btn${bookmarked ? ' is-saved' : ''}"
              data-bookmark-id="${safeId}"
              title="Simpan ke perbandingan"
              aria-label="Simpan formasi untuk dibandingkan"
            >${bookmarked ? ICONS.starFilled : ICONS.starOutline}</button>
          </div>

          <div>
            <div class="agency-name">${escapeHtml(item.nama_instansi)}</div>
            <div class="location-line">
              ${ICONS.pin}
              <span>${escapeHtml(locText)}</span>
            </div>
          </div>

          <div class="major-tag-list" style="max-width:none;">${majorHtml}</div>

          <div class="formation-card-metrics">
            <div>
              <div class="metric-pair-label">Kuota &amp; Pelamar</div>
              <div class="metric-pair-val">${Number(item.jumlah_formasi || 0).toLocaleString('id-ID')}\u00A0Kursi / ${Number(item.jumlah_pelamar || 0).toLocaleString('id-ID')}</div>
            </div>
            <div>
              <div class="metric-pair-label">Rasio Kompetisi</div>
              <div class="metric-pair-val">1 : ${item.rasio_kompetisi}</div>
            </div>
            <div style="grid-column:1 / -1;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
              <div>
                <div class="metric-pair-label">Gaji BKN (Gol. ${escapeHtml(item.golongan_awal || '-')})</div>
                <div class="metric-pair-val" style="white-space:nowrap;">${formatJuta(item.gaji_min)} – ${formatJuta(item.gaji_max)}</div>
              </div>
              ${keketatanBadge}
            </div>
          </div>
        </div>

        <button
          type="button"
          class="btn btn-primary"
          style="width:100%;"
          data-open-detail="${safeId}"
        >${ICONS.eye}<span>Lihat Detail &amp; Simulasi THP</span></button>
      `;
      container.appendChild(card);
    });
  }

  function renderPagination(total, page, limit, totalPages) {
    const pageStartEl = document.getElementById('page-start');
    const pageEndEl = document.getElementById('page-end');
    const pageTotalEl = document.getElementById('page-total');
    const controls = document.getElementById('pagination-controls');

    pageTotalEl.textContent = Number(total).toLocaleString('id-ID');

    if (total === 0) {
      pageStartEl.textContent = '0';
      pageEndEl.textContent = '0';
      controls.innerHTML = '';
      return;
    }

    const start = (page - 1) * limit + 1;
    const end = Math.min(page * limit, total);
    pageStartEl.textContent = Number(start).toLocaleString('id-ID');
    pageEndEl.textContent = Number(end).toLocaleString('id-ID');

    controls.innerHTML = '';

    function createNavBtn(svgHtml, title, disabled, targetPage) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'page-btn';
      btn.innerHTML = svgHtml;
      btn.title = title;
      btn.setAttribute('aria-label', title);
      btn.disabled = disabled;
      btn.addEventListener('click', () => {
        if (!disabled && state.page !== targetPage) {
          state.page = targetPage;
          loadFormasiTable();
          scrollToResultsSection();
        }
      });
      return btn;
    }

    controls.appendChild(createNavBtn(ICONS.chevFirst, 'Halaman Pertama', page === 1, 1));
    controls.appendChild(createNavBtn(ICONS.chevPrev, 'Halaman Sebelumnya', page === 1, page - 1));

    const windowSize = window.innerWidth < 480 ? 3 : 5;
    let startP = Math.max(1, page - Math.floor(windowSize / 2));
    const endP = Math.min(totalPages, startP + windowSize - 1);
    if (endP - startP + 1 < windowSize) {
      startP = Math.max(1, endP - windowSize + 1);
    }

    for (let p = startP; p <= endP; p += 1) {
      const btnPage = document.createElement('button');
      btnPage.type = 'button';
      btnPage.className = `page-btn${p === page ? ' is-active' : ''}`;
      btnPage.textContent = String(p);
      btnPage.addEventListener('click', () => {
        if (state.page !== p) {
          state.page = p;
          loadFormasiTable();
          scrollToResultsSection();
        }
      });
      controls.appendChild(btnPage);
    }

    controls.appendChild(createNavBtn(ICONS.chevNext, 'Halaman Selanjutnya', page === totalPages, page + 1));
    controls.appendChild(createNavBtn(ICONS.chevLast, 'Halaman Terakhir', page === totalPages, totalPages));
  }

  // =========================================================================
  // 4. DETAIL MODAL & INTERACTIVE THP SIMULATOR
  // =========================================================================
  function initThpSimulator(d) {
    const cpns80 = Number(d.gaji_pokok_cpns_80 || 2228560);
    const pns100 = Number(d.gaji_pokok_100 || Math.round(cpns80 / 0.8));
    const gol = d.golongan_awal || 'III/a';
    const uangMakanPerHari = gol.startsWith('IV') ? 41000 : gol.startsWith('III') ? 37000 : 35000;
    const uangMakanBulan = uangMakanPerHari * 22;

    let tukinEst = 0;
    if (d.gaji_min && d.gaji_min > cpns80 * 1.35) {
      tukinEst = d.gaji_min - cpns80;
    } else {
      tukinEst = d.tukin_min || 2100000;
    }

    const rawMin = d.tukin_min !== null && d.tukin_min !== undefined ? Number(d.tukin_min) : tukinEst;
    const rawMax = d.tukin_max !== null && d.tukin_max !== undefined ? Number(d.tukin_max) : tukinEst;
    const sliderMin = Math.min(rawMin, tukinEst);
    const sliderMax = Math.max(rawMax, tukinEst, sliderMin);

    thpSimState.isPns100 = false;
    thpSimState.keluarga = 'TK0';
    thpSimState.cpns80 = cpns80;
    thpSimState.pns100 = pns100;
    thpSimState.uangMakanBulan = uangMakanBulan;
    thpSimState.tukinMin = sliderMin;
    thpSimState.tukinMax = sliderMax;
    thpSimState.tukinBaseline = tukinEst;

    document.getElementById('thp-sim-keluarga').value = 'TK0';
    const slider = document.getElementById('thp-sim-tukin-slider');
    slider.min = String(sliderMin);
    slider.max = String(sliderMax);
    slider.step = sliderMax - sliderMin >= 200000 ? '50000' : '10000';
    slider.value = String(tukinEst);
    slider.disabled = sliderMax <= sliderMin;

    document.getElementById('thp-sim-tukin-min-lbl').textContent = `Min: ${formatJuta(sliderMin)}`;
    document.getElementById('thp-sim-tukin-max-lbl').textContent = `Maks: ${formatJuta(sliderMax)}`;

    setThpStatusPegawai(false, false);
    recalculateModalTHP();
  }

  function setThpStatusPegawai(isPns100, recalc = true) {
    thpSimState.isPns100 = Boolean(isPns100);
    const btnCpns = document.getElementById('btn-sim-cpns');
    const btnPns = document.getElementById('btn-sim-pns');
    if (btnCpns && btnPns) {
      btnCpns.classList.toggle('is-active', !thpSimState.isPns100);
      btnPns.classList.toggle('is-active', thpSimState.isPns100);
    }
    if (recalc) recalculateModalTHP();
  }

  function recalculateModalTHP() {
    const kelSelect = document.getElementById('thp-sim-keluarga');
    const tukinSlider = document.getElementById('thp-sim-tukin-slider');
    if (!kelSelect || !tukinSlider) return;

    thpSimState.keluarga = kelSelect.value;
    const tukinVal = Number(tukinSlider.value || 0);
    document.getElementById('thp-sim-tukin-label').textContent = formatRp(tukinVal);

    const activeGajiPokok = thpSimState.isPns100 ? thpSimState.pns100 : thpSimState.cpns80;
    const kelRates = { TK0: 0, K0: 0.1, K1: 0.12, K2: 0.14 };
    const kelLabels = {
      TK0: 'Tunjangan Keluarga:',
      K0: 'Tunj. Pasangan (10%):',
      K1: 'Tunj. Keluarga (K/1: 12%):',
      K2: 'Tunj. Keluarga (K/2: 14%):'
    };
    const kelRate = kelRates[thpSimState.keluarga] || 0;
    const tunjKeluarga = Math.round(activeGajiPokok * kelRate);

    const totalBruto = activeGajiPokok + tunjKeluarga + tukinVal + thpSimState.uangMakanBulan;
    const iuranBase = activeGajiPokok + tunjKeluarga;
    const potonganBpjs = Math.round(iuranBase * 0.01);
    const potonganTaspen = Math.round(iuranBase * 0.08);
    const totalPotongan = potonganBpjs + potonganTaspen;
    const totalNetto = totalBruto - totalPotongan;

    document.getElementById('modal-thp-badge').textContent = thpSimState.isPns100
      ? 'PNS Penuh (100% Gaji Pokok)'
      : 'Masa CPNS (80% Gaji Pokok)';
    document.getElementById('slip-label-gaji-pokok').textContent = thpSimState.isPns100
      ? 'Gaji Pokok PNS (100% PP 5/2024):'
      : 'Gaji Pokok CPNS (80% PP 5/2024):';

    document.getElementById('slip-gaji-pokok').textContent = formatRp(activeGajiPokok);

    const rowKel = document.getElementById('slip-row-tunj-keluarga');
    if (tunjKeluarga > 0) {
      rowKel.classList.remove('is-hidden');
      document.getElementById('slip-label-tunj-keluarga').textContent =
        kelLabels[thpSimState.keluarga] || 'Tunjangan Keluarga:';
      document.getElementById('slip-tunj-keluarga').textContent = `+ ${formatRp(tunjKeluarga)}`;
    } else {
      rowKel.classList.add('is-hidden');
    }

    document.getElementById('slip-tukin').textContent = `+ ${formatRp(tukinVal)}`;
    document.getElementById('slip-uang-makan').textContent = `+ ${formatRp(thpSimState.uangMakanBulan)}`;
    document.getElementById('slip-total-bruto').textContent = formatRp(totalBruto);

    document.getElementById('slip-bpjs').textContent = `- ${formatRp(potonganBpjs)}`;
    document.getElementById('slip-taspen').textContent = `- ${formatRp(potonganTaspen)}`;
    document.getElementById('slip-total-netto').textContent = `~\u00A0${formatRp(totalNetto)}\u00A0/\u00A0bln`;
    document.getElementById('modal-thp').textContent = `~\u00A0${formatRp(totalNetto)}\u00A0/\u00A0bln`;
  }

  function updateModalBookmarkButton(formasiId) {
    const btn = document.getElementById('btn-modal-bookmark');
    const icon = document.getElementById('modal-bookmark-icon');
    const label = document.getElementById('modal-bookmark-label');
    if (!btn || !icon || !label) return;

    const saved = isBookmarked(formasiId);
    icon.innerHTML = saved ? ICONS.starFilled : ICONS.starOutline;
    label.textContent = saved ? 'Tersimpan' : 'Simpan';
    btn.className = saved ? 'btn btn-accent-soft btn-sm' : 'btn btn-secondary btn-sm';
  }

  function syncBodyScrollLock() {
    const anyOpen = ['modal-detail', 'modal-crowdsource', 'modal-compare'].some(id => {
      const el = document.getElementById(id);
      return el && !el.classList.contains('is-hidden');
    });
    document.body.classList.toggle('overflow-hidden', anyOpen);
  }

  async function openDetailModal(formasiId) {
    const modal = document.getElementById('modal-detail');
    const loadingOverlay = document.getElementById('modal-detail-loading');

    activeDetailId = String(formasiId);
    syncStateToUrl();
    updateModalBookmarkButton(activeDetailId);

    modal.classList.remove('is-hidden');
    loadingOverlay.classList.remove('is-hidden');
    syncBodyScrollLock();

    if (detailAbortController) detailAbortController.abort();
    const controller = new AbortController();
    detailAbortController = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/formasi/${encodeURIComponent(formasiId)}`, {
        signal: controller.signal
      });
      if (!resp.ok) throw new Error(`Detail fetch failed (${resp.status})`);
      const d = await resp.json();

      currentDetailData = d;
      loadedFormasiMap.set(String(d.formasi_id), {
        ...d,
        jurusan_list: (d.majors || []).map(m => m.nama_jurusan)
      });

      currentDetailInstansi = d.nama_instansi || '';
      currentDetailRegulasi = d.regulasi_tukin || '';

      document.getElementById('modal-formasi-id').textContent = d.formasi_id;
      document.getElementById('modal-jenis-formasi').textContent = d.jenis_formasi || 'UMUM';
      document.getElementById('modal-jabatan-nm').textContent = d.jabatan_nm;
      document.getElementById('modal-instansi-nm').textContent = `${d.nama_instansi} (${d.kategori_instansi}) · Kode: ${d.kode_instansi || '-'}`;

      document.getElementById('modal-kuota').textContent = `${d.jumlah_formasi} Kursi`;
      document.getElementById('modal-kompetisi').textContent = `${Number(d.jumlah_pelamar || 0).toLocaleString('id-ID')} (1 : ${d.rasio_kompetisi})`;
      document.getElementById('modal-status-keketatan').textContent = `${d.status_keketatan} (${d.peluang_lolos_pct}% Peluang)`;
      document.getElementById('modal-golongan').textContent = `Golongan ${d.golongan_awal || '-'}`;
      document.getElementById('modal-gaji-pokok-80').textContent = `80% CPNS: ${formatRp(d.gaji_pokok_cpns_80)} · 100%: ${formatRp(d.gaji_pokok_100)}`;

      document.getElementById('modal-lokasi').textContent = cleanLocation(d.lokasi_nm);
      document.getElementById('modal-kategori-instansi').textContent = d.kategori_instansi;

      const tukinMinStr = d.tukin_min ? formatRp(d.tukin_min) : 'Sesuai Regulasi';
      const tukinMaxStr = d.tukin_max ? formatRp(d.tukin_max) : '';
      document.getElementById('modal-tukin-range').textContent = tukinMaxStr ? `${tukinMinStr} – ${tukinMaxStr}` : tukinMinStr;

      const reg = d.regulasi_tukin || 'Estimasi Standar Indikatif';
      document.getElementById('modal-tukin-regulasi').innerHTML = `
        <div style="font-weight:600;color:var(--color-text-primary);">${escapeHtml(reg)}</div>
        <div style="margin-top:6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px;">
          <span class="badge badge-mod">${ICONS.alert}<span>Estimasi Indikatif (Bukan Angka Mutlak)</span></span>
          <button type="button" class="btn btn-accent-soft btn-sm" id="btn-inline-crowdsource">
            ${ICONS.plus}<span>Kirim SK / Slip Tukin Riil</span>
          </button>
        </div>
        <p class="muted-note" style="margin-top:6px;">
          Data resmi SSCASN BKN hanya mencakup nama jabatan, instansi, lokasi, kualifikasi jurusan, kuota, jumlah pelamar, dan rentang gaji publikasi BKN. Nilai Tukin/TPP merupakan estimasi indikatif.
        </p>
      `;
      const inlineBtn = document.getElementById('btn-inline-crowdsource');
      if (inlineBtn) inlineBtn.addEventListener('click', openCrowdsourceModalFromDetail);

      document.getElementById('modal-thp-sscasn').textContent = `Publikasi BKN: ${formatRp(d.gaji_min)} – ${formatRp(d.gaji_max)}`;

      initThpSimulator(d);
      updateModalBookmarkButton(d.formasi_id);

      const majorsContainer = document.getElementById('modal-majors-list');
      majorsContainer.innerHTML = '';
      const majors = d.majors || [];
      document.getElementById('modal-majors-count').textContent = `${majors.length} Program Studi Memenuhi Syarat`;

      if (majors.length === 0) {
        majorsContainer.innerHTML = '<span style="color:var(--color-text-muted);">Terbuka untuk seluruh kualifikasi pendidikan yang relevan.</span>';
      } else {
        majors.forEach(m => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'major-filter-btn';
          btn.innerHTML = `
            <span>${escapeHtml(m.nama_jurusan)}</span>
            <span class="field-badge">${escapeHtml(m.jenjang)}</span>
          `;
          btn.title = `Filter tabel dengan jurusan: ${m.nama_jurusan}`;
          btn.addEventListener('click', () => applyMajorFilterFromModal(m.nama_jurusan, m.jurusan_id));
          majorsContainer.appendChild(btn);
        });
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Error fetching detail modal:', err);
      showToast('Gagal memuat rincian formasi. Silakan coba kembali.', 'warn');
      closeDetailModal();
    } finally {
      if (detailAbortController === controller) {
        loadingOverlay.classList.add('is-hidden');
      }
    }
  }

  function closeDetailModal() {
    if (detailAbortController) detailAbortController.abort();
    const modal = document.getElementById('modal-detail');
    if (modal) modal.classList.add('is-hidden');
    const loading = document.getElementById('modal-detail-loading');
    if (loading) loading.classList.add('is-hidden');
    activeDetailId = null;
    syncStateToUrl();
    syncBodyScrollLock();
  }

  async function copyDetailShareLink() {
    if (!activeDetailId) return;
    const params = buildFilterParams(false, true);
    const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    const btn = document.getElementById('btn-share-detail');
    const orig = btn.innerHTML;
    try {
      await copyToClipboard(url);
      btn.innerHTML = `${ICONS.check}<span>Tautan Tersalin</span>`;
      setTimeout(() => {
        btn.innerHTML = orig;
      }, 2200);
    } catch (_e) {
      showToast('Gagal menyalin otomatis. Salin URL langsung dari bilah alamat.', 'warn');
    }
  }

  // =========================================================================
  // 5. BOOKMARK & SIDE-BY-SIDE COMPARISON
  // =========================================================================
  function getBookmarks() {
    try {
      const raw = localStorage.getItem(BOOKMARK_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (_e) {
      return [];
    }
  }

  function saveBookmarks(list) {
    try {
      localStorage.setItem(BOOKMARK_STORAGE_KEY, JSON.stringify(list.slice(0, MAX_BOOKMARKS)));
    } catch (e) {
      console.error('Failed saving bookmarks:', e);
    }
    updateBookmarkUI();
  }

  function isBookmarked(formasiId) {
    return getBookmarks().some(b => String(b.formasi_id) === String(formasiId));
  }

  function toggleBookmark(formasiId) {
    const list = getBookmarks();
    const idx = list.findIndex(b => String(b.formasi_id) === String(formasiId));
    if (idx >= 0) {
      list.splice(idx, 1);
      saveBookmarks(list);
      showToast('Formasi dihapus dari daftar perbandingan.', 'info');
    } else {
      if (list.length >= MAX_BOOKMARKS) {
        showToast(`Maksimal ${MAX_BOOKMARKS} formasi dapat dibandingkan sekaligus.`, 'warn');
        return;
      }
      const item =
        loadedFormasiMap.get(String(formasiId)) ||
        (currentDetailData && String(currentDetailData.formasi_id) === String(formasiId) ? currentDetailData : null);
      if (!item) {
        showToast('Data formasi belum termuat untuk disimpan.', 'warn');
        return;
      }
      list.push(item);
      saveBookmarks(list);
      showToast('Formasi disimpan ke daftar perbandingan.', 'success');
    }
  }

  function toggleBookmarkFromModal() {
    if (!activeDetailId) return;
    toggleBookmark(activeDetailId);
    updateModalBookmarkButton(activeDetailId);
  }

  function removeBookmark(formasiId) {
    const list = getBookmarks().filter(b => String(b.formasi_id) !== String(formasiId));
    saveBookmarks(list);
    const compareModal = document.getElementById('modal-compare');
    if (compareModal && !compareModal.classList.contains('is-hidden')) {
      renderCompareTable(list);
    }
  }

  function clearAllBookmarks() {
    saveBookmarks([]);
    const compareModal = document.getElementById('modal-compare');
    if (compareModal && !compareModal.classList.contains('is-hidden')) {
      renderCompareTable([]);
    }
    showToast('Daftar perbandingan telah dikosongkan.', 'info');
  }

  function updateBookmarkUI() {
    const list = getBookmarks();
    const badge = document.getElementById('compare-count-badge');
    if (badge) badge.textContent = String(list.length);

    const savedIds = new Set(list.map(b => String(b.formasi_id)));
    document.querySelectorAll('[data-bookmark-id]').forEach(btn => {
      const fid = btn.getAttribute('data-bookmark-id');
      const active = savedIds.has(String(fid));
      btn.classList.toggle('is-saved', active);
      btn.innerHTML = active ? ICONS.starFilled : ICONS.starOutline;
    });

    if (activeDetailId) {
      updateModalBookmarkButton(activeDetailId);
    }
  }

  function computeEstimatedThp(item) {
    const cpns80 = Number(item.gaji_pokok_cpns_80 || 2228560);
    const gol = item.golongan_awal || 'III/a';
    const uangMakanPerHari = gol.startsWith('IV') ? 41000 : gol.startsWith('III') ? 37000 : 35000;
    const uangMakanBulan = uangMakanPerHari * 22;
    let tukinEst = 0;
    if (item.gaji_min && item.gaji_min > cpns80 * 1.35) {
      tukinEst = item.gaji_min - cpns80;
    } else {
      tukinEst = item.tukin_min || 2100000;
    }
    const bruto = cpns80 + tukinEst + uangMakanBulan;
    const pot = Math.round(cpns80 * 0.01) + Math.round(cpns80 * 0.08);
    return bruto - pot;
  }

  async function openCompareModal() {
    const modal = document.getElementById('modal-compare');
    const loadingEl = document.getElementById('compare-loading');
    modal.classList.remove('is-hidden');
    syncBodyScrollLock();

    let bookmarks = getBookmarks();
    if (bookmarks.length === 0) {
      loadingEl.classList.add('is-hidden');
      renderCompareTable([]);
      return;
    }

    renderCompareTable(bookmarks);

    const ids = bookmarks.map(b => b.formasi_id).filter(Boolean).slice(0, MAX_BOOKMARKS);
    if (ids.length > 0) {
      loadingEl.classList.remove('is-hidden');
      try {
        const resp = await fetch(`${API_BASE}/api/formasi-batch?ids=${encodeURIComponent(ids.join(','))}`);
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data.items) && data.items.length > 0) {
            const freshMap = new Map(data.items.map(it => [String(it.formasi_id), it]));
            bookmarks = bookmarks.map(b => freshMap.get(String(b.formasi_id)) || b);
            saveBookmarks(bookmarks);
            renderCompareTable(bookmarks);
          }
        }
      } catch (err) {
        console.warn('Batch refresh fallback to local bookmarks:', err);
      } finally {
        loadingEl.classList.add('is-hidden');
      }
    }
  }

  function closeCompareModal() {
    document.getElementById('modal-compare').classList.add('is-hidden');
    syncBodyScrollLock();
  }

  function renderCompareTable(items) {
    const emptyEl = document.getElementById('compare-empty-state');
    const containerEl = document.getElementById('compare-table-container');
    const tableEl = document.getElementById('compare-table');
    const clearBtn = document.getElementById('btn-clear-bookmarks');

    if (!items || items.length === 0) {
      emptyEl.classList.remove('is-hidden');
      containerEl.classList.add('is-hidden');
      if (clearBtn) clearBtn.classList.add('is-hidden');
      return;
    }

    emptyEl.classList.add('is-hidden');
    containerEl.classList.remove('is-hidden');
    if (clearBtn) clearBtn.classList.remove('is-hidden');

    const headerCols = items
      .map(
        it => `
        <th style="min-width:220px;background-color:var(--color-bg-recessed);text-align:left;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
            <div>
              <span class="uuid-code">${escapeHtml(it.formasi_id)}</span>
              <div style="font-size:0.875rem;font-weight:700;color:var(--color-text-primary);margin-top:4px;">${escapeHtml(it.jabatan_nm)}</div>
            </div>
            <button
              type="button"
              class="btn-icon"
              style="width:26px;height:26px;"
              data-remove-bookmark="${escapeHtml(it.formasi_id)}"
              title="Hapus dari perbandingan"
              aria-label="Hapus dari perbandingan"
            >${ICONS.close}</button>
          </div>
        </th>
      `
      )
      .join('');

    const rowsSpec = [
      {
        label: 'Instansi & Lingkup',
        render: it =>
          `<div style="font-weight:600;color:var(--color-text-primary);">${escapeHtml(it.nama_instansi)}</div><div style="margin-top:4px;">${getScopeBadge(it.kategori_instansi)}</div>`
      },
      {
        label: 'Unit Penempatan',
        render: it => `<span style="color:var(--color-text-secondary);">${escapeHtml(cleanLocation(it.lokasi_nm))}</span>`
      },
      {
        label: 'Jalur Formasi',
        render: it => getJenisBadge(it.jenis_formasi)
      },
      {
        label: 'Kuota Kursi',
        render: it => `<span class="mono" style="font-weight:700;color:var(--color-loose-ink);">${Number(it.jumlah_formasi || 0).toLocaleString('id-ID')} Kursi</span>`
      },
      {
        label: 'Pelamar MS',
        render: it => `<span class="mono" style="color:var(--color-text-primary);">${Number(it.jumlah_pelamar || 0).toLocaleString('id-ID')} Orang</span>`
      },
      {
        label: 'Rasio & Peluang',
        render: it =>
          `<div class="mono" style="font-weight:700;margin-bottom:4px;">1 : ${it.rasio_kompetisi}</div><div>${getKeketatanBadge(it.status_keketatan, it.peluang_lolos_pct)}</div>`
      },
      {
        label: 'Golongan Awal',
        render: it => `<span class="mono">Gol. ${escapeHtml(it.golongan_awal || '-')}</span>`
      },
      {
        label: 'Gaji Publikasi BKN',
        render: it => `<span class="mono" style="font-weight:600;">${formatJuta(it.gaji_min)} – ${formatJuta(it.gaji_max)}</span>`
      },
      {
        label: 'Simulasi THP (CPNS 80%)',
        render: it => `<span class="mono" style="font-weight:700;color:var(--color-accent-ink);">~\u00A0${formatRp(computeEstimatedThp(it))}\u00A0/\u00A0bln</span>`
      },
      {
        label: 'Kualifikasi Jurusan',
        render: it => {
          const majors = it.jurusan_list || [];
          if (!majors.length) {
            return `<span style="color:var(--color-text-muted);">${escapeHtml(it.pendidikan_raw || 'Semua Jurusan')}</span>`;
          }
          const shown = majors
            .slice(0, 4)
            .map(m => `<span class="major-tag">${escapeHtml(m)}</span>`)
            .join(' ');
          const extra =
            majors.length > 4
              ? `<span style="font-size:0.75rem;color:var(--color-accent-ink);font-weight:600;">+${majors.length - 4} lainnya</span>`
              : '';
          return `<div style="display:flex;flex-wrap:wrap;gap:4px;">${shown} ${extra}</div>`;
        }
      },
      {
        label: 'Tindakan',
        render: it => `
          <div style="display:flex;align-items:center;gap:6px;">
            <button type="button" class="btn btn-primary btn-sm" data-compare-open-detail="${escapeHtml(it.formasi_id)}">Buka Detail</button>
            <button type="button" class="btn btn-ghost btn-sm" data-remove-bookmark="${escapeHtml(it.formasi_id)}">Hapus</button>
          </div>
        `
      }
    ];

    const bodyRows = rowsSpec
      .map(
        spec => `
        <tr>
          <th class="compare-row-label">${spec.label}</th>
          ${items.map(it => `<td>${spec.render(it)}</td>`).join('')}
        </tr>
      `
      )
      .join('');

    tableEl.innerHTML = `
      <thead>
        <tr>
          <th class="compare-row-label">Parameter</th>
          ${headerCols}
        </tr>
      </thead>
      <tbody>
        ${bodyRows}
      </tbody>
    `;
  }

  // =========================================================================
  // 6. CROWDSOURCE TPP MODAL & ACTIVE CHIPS
  // =========================================================================
  function updateGoogleFormLink() {
    const instansi = encodeURIComponent(document.getElementById('crowd-instansi')?.value.trim() || '');
    const regulasi = encodeURIComponent(document.getElementById('crowd-regulasi')?.value.trim() || '');
    const linkJdih = encodeURIComponent(document.getElementById('crowd-link')?.value.trim() || '');

    const baseUrl =
      'https://docs.google.com/forms/d/e/1FAIpQLSfMM_mEoLRfZCrfdwgosMHSg24dnmDLgPzQnA2cP50OHnQxsw/viewform?usp=pp_url';
    const formUrl = `${baseUrl}&entry.1057785259=${instansi}&entry.621332457=${regulasi}&entry.595628026=${linkJdih}`;

    const gBtn = document.getElementById('link-google-form');
    if (gBtn) gBtn.href = formUrl;
  }

  function openCrowdsourceModal(namaInstansi = '', regulasi = '') {
    const modal = document.getElementById('modal-crowdsource');
    const inputInstansi = document.getElementById('crowd-instansi');
    const inputRegulasi = document.getElementById('crowd-regulasi');

    if (namaInstansi && inputInstansi) inputInstansi.value = namaInstansi;
    if (inputRegulasi) {
      if (regulasi && !regulasi.includes('Estimasi Kisaran') && !regulasi.includes('Estimasi Standar')) {
        inputRegulasi.value = regulasi;
      } else if (regulasi) {
        inputRegulasi.value = '';
      }
    }

    updateGoogleFormLink();
    modal.classList.remove('is-hidden');
    syncBodyScrollLock();
  }

  function openCrowdsourceModalFromDetail() {
    openCrowdsourceModal(currentDetailInstansi, currentDetailRegulasi);
  }

  function closeCrowdsourceModal() {
    document.getElementById('modal-crowdsource').classList.add('is-hidden');
    syncBodyScrollLock();
  }

  function copyCrowdReport() {
    const instansi = document.getElementById('crowd-instansi').value.trim() || '-';
    const regulasi = document.getElementById('crowd-regulasi').value.trim() || '-';
    const link = document.getElementById('crowd-link').value.trim() || '-';
    const notes = document.getElementById('crowd-notes').value.trim() || '-';

    const text = `LAPORAN DATA TPP DAERAH CPNS 2024:\n- Instansi: ${instansi}\n- Regulasi: ${regulasi}\n- Link JDIH: ${link}\n- Catatan: ${notes}`;

    copyToClipboard(text)
      .then(() => {
        const lbl = document.getElementById('btn-copy-label');
        const orig = lbl.textContent;
        lbl.textContent = 'Format Laporan Berhasil Disalin';
        setTimeout(() => {
          lbl.textContent = orig;
        }, 2500);
      })
      .catch(() => {
        showToast('Gagal menyalin otomatis. Silakan gunakan tombol Formulir Google di bawah.', 'warn');
      });
  }

  function applyMajorFilterFromModal(majorName, majorId) {
    state.jurusan = majorName;
    state.jurusan_id = majorId;
    state.page = 1;

    syncControlsFromState();
    updateActiveChips();
    closeDetailModal();
    loadFormasiTable();
  }

  function clearFilterByKey(key) {
    if (key === 'q') state.q = '';
    else if (key === 'jurusan') {
      state.jurusan = '';
      state.jurusan_id = null;
    } else if (key === 'jenjang') state.jenjang = 'ALL';
    else if (key === 'kategori_instansi') state.kategori_instansi = 'ALL';
    else if (key === 'instansi_id') {
      state.instansi_id = 'ALL';
      state.instansi_nama = '';
    } else if (key === 'jenis_formasi') state.jenis_formasi = 'ALL';
    else if (key === 'status_keketatan') {
      state.status_keketatan = 'ALL';
      state.zero_applicant_only = false;
    } else if (key === 'zero_applicant_only') {
      state.zero_applicant_only = false;
      if (state.status_keketatan === 'Tanpa Pelamar') state.status_keketatan = 'ALL';
    } else if (key === 'gaji_min') state.gaji_min = 0;

    state.page = 1;
    syncControlsFromState();
    syncStateToUrl();
    updateActiveChips();
    if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
    loadFormasiTable();
  }

  function updateActiveChips() {
    const container = document.getElementById('active-filter-chips');
    if (!container) return;
    container.innerHTML = '<span class="chips-label">Filter Aktif:</span>';

    const chips = [];
    if (state.q) chips.push({ key: 'q', label: `Kata kunci: "${state.q}"` });
    if (state.jurusan) chips.push({ key: 'jurusan', label: `Jurusan: ${state.jurusan}` });
    if (state.jenjang !== 'ALL') chips.push({ key: 'jenjang', label: `Jenjang: ${state.jenjang}` });
    if (state.kategori_instansi !== 'ALL') chips.push({ key: 'kategori_instansi', label: `Lingkup: ${state.kategori_instansi}` });
    if (state.instansi_id !== 'ALL') {
      const match = allInstansi.find(i => String(i.instansi_id) === String(state.instansi_id));
      const text = match?.nama_instansi || state.instansi_nama || state.instansi_id;
      chips.push({ key: 'instansi_id', label: `Instansi: ${text}` });
    }
    if (state.jenis_formasi !== 'ALL') chips.push({ key: 'jenis_formasi', label: `Jalur: ${state.jenis_formasi}` });
    if (state.zero_applicant_only) {
      chips.push({ key: 'zero_applicant_only', label: '0 Pelamar' });
    } else if (state.status_keketatan !== 'ALL') {
      chips.push({ key: 'status_keketatan', label: `Keketatan: ${state.status_keketatan}` });
    }
    if (state.gaji_min > 0) chips.push({ key: 'gaji_min', label: `Min: ${formatJuta(state.gaji_min)}` });

    if (chips.length === 0) {
      const emptyPill = document.createElement('span');
      emptyPill.className = 'filter-chip-muted';
      emptyPill.textContent = 'Seluruh Formasi';
      container.appendChild(emptyPill);
    } else {
      chips.forEach(c => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'filter-chip';
        btn.title = 'Klik untuk menghapus filter ini';
        btn.innerHTML = `<span>${escapeHtml(c.label)}</span>${ICONS.close}`;
        btn.addEventListener('click', () => clearFilterByKey(c.key));
        container.appendChild(btn);
      });
    }
  }

  // =========================================================================
  // 7. EVENT WIRING
  // =========================================================================
  function setupDashboardListeners() {
    document.addEventListener('click', e => {
      const detailTrigger = e.target.closest('[data-open-detail]');
      if (detailTrigger) {
        openDetailModal(detailTrigger.getAttribute('data-open-detail'));
        return;
      }
      const bookmarkTrigger = e.target.closest('[data-bookmark-id]');
      if (bookmarkTrigger) {
        toggleBookmark(bookmarkTrigger.getAttribute('data-bookmark-id'));
        return;
      }
      const removeBmTrigger = e.target.closest('[data-remove-bookmark]');
      if (removeBmTrigger) {
        removeBookmark(removeBmTrigger.getAttribute('data-remove-bookmark'));
        return;
      }
      const compareOpenDetail = e.target.closest('[data-compare-open-detail]');
      if (compareOpenDetail) {
        const fid = compareOpenDetail.getAttribute('data-compare-open-detail');
        closeCompareModal();
        openDetailModal(fid);
        return;
      }
      const presetBtn = e.target.closest('[data-preset]');
      if (presetBtn) {
        applyStrategicPreset(presetBtn.getAttribute('data-preset'));
      }
    });

    const inputQ = document.getElementById('filter-q');
    const btnClearQ = document.getElementById('btn-clear-q');
    inputQ.addEventListener(
      'input',
      debounce(e => {
        state.q = e.target.value.trim();
        state.page = 1;
        btnClearQ.classList.toggle('is-hidden', !state.q);
        syncControlsFromState();
        updateActiveChips();
        loadFormasiTable();
      }, 280)
    );
    btnClearQ.addEventListener('click', () => {
      inputQ.value = '';
      state.q = '';
      state.page = 1;
      btnClearQ.classList.add('is-hidden');
      syncControlsFromState();
      updateActiveChips();
      loadFormasiTable();
    });

    const inputJurusan = document.getElementById('filter-jurusan-input');
    const btnClearJurusan = document.getElementById('btn-clear-jurusan');
    const listJurusan = document.getElementById('jurusan-autocomplete-list');

    inputJurusan.addEventListener(
      'input',
      debounce(async e => {
        const term = e.target.value.trim();
        btnClearJurusan.classList.toggle('is-hidden', !term);
        state.jurusan = term;
        state.jurusan_id = null;
        state.page = 1;

        if (jurusanAbortController) jurusanAbortController.abort();

        if (term.length < 2) {
          listJurusan.classList.add('is-hidden');
          updateActiveChips();
          loadFormasiTable();
          return;
        }

        const controller = new AbortController();
        jurusanAbortController = controller;

        try {
          const params = new URLSearchParams({ q: term, limit: '35' });
          if (state.jenjang !== 'ALL') params.set('jenjang', state.jenjang);
          const r = await fetch(`${API_BASE}/api/filters/jurusan?${params.toString()}`, {
            signal: controller.signal
          });
          if (!r.ok) return;
          const items = await r.json();

          listJurusan.innerHTML = '';
          if (items.length === 0) {
            listJurusan.innerHTML = '<div class="autocomplete-empty">Tidak ada program studi ditemukan</div>';
          } else {
            items.forEach(it => {
              const div = document.createElement('div');
              div.className = 'autocomplete-item';
              const countMeta = it.total_formasi
                ? `<span class="mono" style="font-size:0.75rem;color:var(--color-text-muted);white-space:nowrap;">${Number(it.total_formasi).toLocaleString('id-ID')}</span>`
                : '';
              div.innerHTML = `
                <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(it.nama_jurusan)}">${escapeHtml(it.nama_jurusan)}</span>
                <span style="display:inline-flex;align-items:center;gap:6px;flex-shrink:0;">
                  ${countMeta}
                  <span class="field-badge">${escapeHtml(it.jenjang)}</span>
                </span>
              `;
              div.addEventListener('click', () => {
                inputJurusan.value = it.nama_jurusan;
                state.jurusan = it.nama_jurusan;
                state.jurusan_id = it.jurusan_id;
                state.page = 1;
                listJurusan.classList.add('is-hidden');
                btnClearJurusan.classList.remove('is-hidden');
                updateActiveChips();
                loadFormasiTable();
              });
              listJurusan.appendChild(div);
            });
          }
          listJurusan.classList.remove('is-hidden');
        } catch (err) {
          if (err.name === 'AbortError') return;
          console.error('Error autocompleting jurusan:', err);
        }
        updateActiveChips();
        loadFormasiTable();
      }, 240)
    );

    btnClearJurusan.addEventListener('click', () => {
      if (jurusanAbortController) jurusanAbortController.abort();
      inputJurusan.value = '';
      state.jurusan = '';
      state.jurusan_id = null;
      state.page = 1;
      btnClearJurusan.classList.add('is-hidden');
      listJurusan.classList.add('is-hidden');
      updateActiveChips();
      loadFormasiTable();
    });

    const inputInstansi = document.getElementById('filter-instansi-input');
    const btnClearInstansi = document.getElementById('btn-clear-instansi');
    const listInstansi = document.getElementById('instansi-autocomplete-list');

    inputInstansi.addEventListener('focus', () => {
      const currentSelected = state.instansi_id !== 'ALL' && inputInstansi.value === state.instansi_nama;
      renderInstansiDropdown(currentSelected ? '' : inputInstansi.value);
    });

    inputInstansi.addEventListener('input', e => {
      const term = e.target.value;
      btnClearInstansi.classList.toggle('is-hidden', !term.trim() && state.instansi_id === 'ALL');
      if (!term.trim() && state.instansi_id !== 'ALL') {
        clearSelectedInstansi(true);
        renderInstansiDropdown('');
        return;
      }
      renderInstansiDropdown(term);
    });

    btnClearInstansi.addEventListener('click', () => clearSelectedInstansi(true));

    document.addEventListener('click', e => {
      if (!inputJurusan.contains(e.target) && !listJurusan.contains(e.target)) {
        listJurusan.classList.add('is-hidden');
      }
      const instansiWrapper = document.getElementById('instansi-combobox-wrapper');
      if (instansiWrapper && !instansiWrapper.contains(e.target)) {
        listInstansi.classList.add('is-hidden');
        if (state.instansi_id !== 'ALL') {
          inputInstansi.value = state.instansi_nama || '';
        } else {
          inputInstansi.value = '';
          btnClearInstansi.classList.add('is-hidden');
        }
      }
    });

    document.getElementById('filter-jenjang').addEventListener('change', e => {
      state.jenjang = e.target.value;
      state.page = 1;
      syncControlsFromState();
      updateActiveChips();
      loadFormasiTable();
    });

    document.getElementById('filter-kategori-instansi').addEventListener('change', e => {
      handleKategoriInstansiChange(e.target.value);
    });

    document.getElementById('filter-jenis-formasi').addEventListener('change', e => {
      state.jenis_formasi = e.target.value;
      state.page = 1;
      syncControlsFromState();
      updateActiveChips();
      if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
      loadFormasiTable();
    });

    document.getElementById('filter-status-keketatan').addEventListener('change', e => {
      state.status_keketatan = e.target.value;
      state.zero_applicant_only = e.target.value === 'Tanpa Pelamar';
      state.page = 1;
      syncControlsFromState();
      updateActiveChips();
      if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
      loadFormasiTable();
    });

    function toggleZeroApplicants() {
      state.zero_applicant_only = !state.zero_applicant_only;
      state.status_keketatan = state.zero_applicant_only ? 'Tanpa Pelamar' : 'ALL';
      state.page = 1;
      syncControlsFromState();
      updateActiveChips();
      if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
      loadFormasiTable();
    }

    document.getElementById('btn-toggle-zero').addEventListener('click', toggleZeroApplicants);
    document.getElementById('card-zero-applicants').addEventListener('click', toggleZeroApplicants);
    const summaryZeroBtn = document.getElementById('summary-zero-btn');
    if (summaryZeroBtn) summaryZeroBtn.addEventListener('click', toggleZeroApplicants);

    // Mobile secondary filters toggle
    const btnMobileFilters = document.getElementById('btn-toggle-mobile-filters');
    const workbenchPanel = document.getElementById('workbench-panel');
    if (btnMobileFilters && workbenchPanel) {
      btnMobileFilters.addEventListener('click', () => {
        const expanded = workbenchPanel.classList.toggle('is-expanded-mobile');
        btnMobileFilters.setAttribute('aria-expanded', String(expanded));
      });
    }

    // Analytics drawer toggle (Lazy-loads Top 10 only when opened)
    const btnToggleAnalytics = document.getElementById('btn-toggle-analytics');
    const analyticsBody = document.getElementById('analytics-cards-body');
    const analyticsToggleLabel = document.getElementById('analytics-toggle-label');
    const analyticsChevron = document.getElementById('analytics-toggle-chevron');
    btnToggleAnalytics.addEventListener('click', () => {
      const isHidden = analyticsBody.classList.toggle('is-hidden');
      isAnalyticsOpen = !isHidden;
      analyticsToggleLabel.innerHTML = isHidden
        ? 'Grafik<span class="hide-xs"> &amp; Top 10</span>'
        : 'Tutup<span class="hide-xs"> Grafik</span>';
      if (analyticsChevron) analyticsChevron.classList.toggle('is-open', isAnalyticsOpen);
      btnToggleAnalytics.setAttribute('aria-expanded', String(isAnalyticsOpen));
      if (isAnalyticsOpen) {
        loadTopAnalyticsIfOpen(true);
      }
    });

    const sliderGaji = document.getElementById('filter-gaji-min-range');
    const labelGaji = document.getElementById('label-gaji-min');
    sliderGaji.addEventListener('input', e => {
      const val = Number(e.target.value);
      state.gaji_min = val;
      labelGaji.textContent = val === 0 ? 'Semua (Rp 0)' : `≥ ${formatJuta(val)}`;
    });
    sliderGaji.addEventListener('change', () => {
      state.page = 1;
      syncControlsFromState();
      updateActiveChips();
      loadFormasiTable();
    });
    document.querySelectorAll('.preset-gaji').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = Number(btn.dataset.val);
        sliderGaji.value = String(val);
        state.gaji_min = val;
        state.page = 1;
        syncControlsFromState();
        updateActiveChips();
        loadFormasiTable();
      });
    });

    document.getElementById('filter-sort-by').addEventListener('change', e => {
      state.sort_by = e.target.value;
      state.page = 1;
      syncControlsFromState();
      loadFormasiTable();
    });
    document.getElementById('table-page-size').addEventListener('change', e => {
      state.limit = Number(e.target.value);
      state.page = 1;
      loadFormasiTable();
    });

    document.getElementById('btn-view-cards').addEventListener('click', () => setTableViewMode('cards'));
    document.getElementById('btn-view-table').addEventListener('click', () => setTableViewMode('table'));

    document.getElementById('btn-copy-filter-link').addEventListener('click', async () => {
      const params = buildFilterParams(true, true);
      const qs = params.toString();
      const url = qs
        ? `${window.location.origin}${window.location.pathname}?${qs}`
        : `${window.location.origin}${window.location.pathname}`;
      const btn = document.getElementById('btn-copy-filter-link');
      const orig = btn.innerHTML;
      try {
        await copyToClipboard(url);
        btn.innerHTML = `${ICONS.check}<span>Tersalin</span>`;
        setTimeout(() => {
          btn.innerHTML = orig;
        }, 2200);
      } catch (_err) {
        showToast('Gagal menyalin tautan filter.', 'warn');
      }
    });

    function resetAllFilters() {
      state.q = '';
      state.jurusan = '';
      state.jurusan_id = null;
      state.jenjang = 'ALL';
      state.kategori_instansi = 'ALL';
      state.instansi_id = 'ALL';
      state.instansi_nama = '';
      state.jenis_formasi = 'ALL';
      state.status_keketatan = 'ALL';
      state.zero_applicant_only = false;
      state.gaji_min = 0;
      state.sort_by = 'kuota_desc';
      state.page = 1;
      activeAnalyticsSnapshot = null;

      syncControlsFromState();
      syncStateToUrl();
      updateActiveChips();
      if (activeAnalyticsSnapshot || statsCache) renderAnalyticsCards(activeAnalyticsSnapshot || statsCache);
      loadFormasiTable();
    }

    document.getElementById('btn-reset-filters').addEventListener('click', resetAllFilters);
    const btnEmptyReset = document.getElementById('btn-empty-reset');
    if (btnEmptyReset) btnEmptyReset.addEventListener('click', resetAllFilters);

    document.getElementById('btn-export-csv').addEventListener('click', () => {
      const params = new URLSearchParams();
      if (state.q) params.set('q', state.q);
      if (state.jurusan_id) params.set('jurusan_id', state.jurusan_id);
      else if (state.jurusan) params.set('jurusan', state.jurusan);
      if (state.jenjang !== 'ALL') params.set('jenjang', state.jenjang);
      if (state.kategori_instansi !== 'ALL') params.set('kategori_instansi', state.kategori_instansi);
      if (state.instansi_id !== 'ALL') params.set('instansi_id', state.instansi_id);
      if (state.jenis_formasi !== 'ALL') params.set('jenis_formasi', state.jenis_formasi);
      if (state.status_keketatan !== 'ALL') params.set('status_keketatan', state.status_keketatan);
      if (state.zero_applicant_only) params.set('zero_applicant_only', 'true');
      if (state.gaji_min > 0) params.set('gaji_min', state.gaji_min);
      params.set('sort_by', state.sort_by);
      window.location.href = `${API_BASE}/api/export?${params.toString()}`;
    });

    document.getElementById('btn-open-compare').addEventListener('click', openCompareModal);
    document.getElementById('btn-open-crowdsource').addEventListener('click', () => openCrowdsourceModal());
    const btnDisclaimerCrowd = document.getElementById('btn-disclaimer-crowdsource');
    if (btnDisclaimerCrowd) btnDisclaimerCrowd.addEventListener('click', () => openCrowdsourceModal());

    document.getElementById('btn-close-modal').addEventListener('click', closeDetailModal);
    document.getElementById('btn-footer-close-detail').addEventListener('click', closeDetailModal);
    document.getElementById('btn-modal-bookmark').addEventListener('click', toggleBookmarkFromModal);
    document.getElementById('btn-share-detail').addEventListener('click', copyDetailShareLink);
    document.getElementById('btn-lapor-tukin').addEventListener('click', openCrowdsourceModalFromDetail);
    document.getElementById('btn-sim-cpns').addEventListener('click', () => setThpStatusPegawai(false));
    document.getElementById('btn-sim-pns').addEventListener('click', () => setThpStatusPegawai(true));
    document.getElementById('thp-sim-keluarga').addEventListener('change', recalculateModalTHP);
    document.getElementById('thp-sim-tukin-slider').addEventListener('input', recalculateModalTHP);

    document.getElementById('btn-clear-bookmarks').addEventListener('click', clearAllBookmarks);
    document.getElementById('btn-close-compare').addEventListener('click', closeCompareModal);
    document.getElementById('btn-footer-close-compare').addEventListener('click', closeCompareModal);

    document.getElementById('btn-close-crowdsource').addEventListener('click', closeCrowdsourceModal);
    document.getElementById('btn-footer-close-crowdsource').addEventListener('click', closeCrowdsourceModal);
    document.getElementById('btn-copy-crowd').addEventListener('click', copyCrowdReport);
    ['crowd-instansi', 'crowd-regulasi', 'crowd-link'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', updateGoogleFormLink);
    });

    const modalDetail = document.getElementById('modal-detail');
    const modalCrowd = document.getElementById('modal-crowdsource');
    const modalCompare = document.getElementById('modal-compare');

    modalDetail.addEventListener('click', e => {
      if (e.target === modalDetail) closeDetailModal();
    });
    modalCrowd.addEventListener('click', e => {
      if (e.target === modalCrowd) closeCrowdsourceModal();
    });
    modalCompare.addEventListener('click', e => {
      if (e.target === modalCompare) closeCompareModal();
    });

    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape') return;
      if (!modalCrowd.classList.contains('is-hidden')) closeCrowdsourceModal();
      else if (!modalCompare.classList.contains('is-hidden')) closeCompareModal();
      else if (!modalDetail.classList.contains('is-hidden')) closeDetailModal();
    });
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  function syncThemeButtons() {
    const isLight = getCurrentTheme() === 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      const nextLabel = isLight ? 'Dark Mode' : 'Light Mode';
      const shortLabel = isLight ? 'Dark' : 'Light';
      btn.innerHTML = `${isLight ? ICONS.moon : ICONS.sun}<span class="hide-xs">${shortLabel}</span>`;
      btn.title = `Switch to ${nextLabel}`;
      btn.setAttribute('aria-label', `Switch to ${nextLabel}`);
    });
  }

  function setTheme(nextTheme) {
    const resolved = nextTheme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', resolved);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, resolved);
    } catch (_e) {
      // Ignore storage restriction
    }
    syncThemeButtons();
  }

  function setupSharedInteractions() {
    syncThemeButtons();

    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      btn.addEventListener('click', () => {
        setTheme(getCurrentTheme() === 'light' ? 'dark' : 'light');
      });
    });

    document.querySelectorAll('[data-copy-nmid]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const nmid = btn.getAttribute('data-copy-nmid') || 'ID1025421073475';
        const orig = btn.innerHTML;
        try {
          await copyToClipboard(nmid);
          btn.innerHTML = `${ICONS.check}<span>Tersalin</span>`;
          setTimeout(() => {
            btn.innerHTML = orig;
          }, 2000);
        } catch (_e) {
          showToast(`NMID: ${nmid}`, 'info');
        }
      });
    });

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', e => {
        const targetId = anchor.getAttribute('href').slice(1);
        const targetEl = targetId ? document.getElementById(targetId) : null;
        if (targetEl) {
          e.preventDefault();
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });

    let lastScrollY = window.scrollY;
    let ticking = false;
    const header = document.getElementById('main-header');
    if (!header) return;

    window.addEventListener(
      'scroll',
      () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            const currentScrollY = window.scrollY;
            if (currentScrollY <= 60) {
              header.classList.remove('header-hidden');
            } else if (currentScrollY > lastScrollY && currentScrollY > 120) {
              header.classList.add('header-hidden');
            } else if (currentScrollY < lastScrollY) {
              header.classList.remove('header-hidden');
            }
            lastScrollY = currentScrollY;
            ticking = false;
          });
          ticking = true;
        }
      },
      { passive: true }
    );
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setupSharedInteractions();

    if (!document.getElementById('section-table')) return;

    const initialOpenCharts = new URLSearchParams(window.location.search).get('charts') === '1';
    const initialDetailId = initStateFromUrl();
    tableViewMode = window.innerWidth < 768 ? 'cards' : 'table';
    window.addEventListener('resize', () => {
      if (!userForcedViewMode) {
        const expected = window.innerWidth < 768 ? 'cards' : 'table';
        if (tableViewMode !== expected) setTableViewMode(expected, false);
      }
    });
    syncControlsFromState();
    updateActiveChips();
    updateBookmarkUI();
    setupDashboardListeners();
    applyTableViewVisibility();

    if (initialOpenCharts) {
      const btnToggle = document.getElementById('btn-toggle-analytics');
      if (btnToggle && !isAnalyticsOpen) btnToggle.click();
    }

    await Promise.all([loadStats(), loadFilterOptions(), loadFormasiTable()]);

    if (initialDetailId) {
      openDetailModal(initialDetailId);
    }
  });
})();
