/**
 * SSCASN CPNS 2026 Explorer — Frontend Controller
 * Strict No-Hallucination UI: renders missing 2026 fields (pelamar, rasio, keketatan,
 * jenis_formasi, gaji_min/max BKN) strictly as '—' / 'Belum tersedia' without fake 0s.
 */
(function () {
  'use strict';

  const API_BASE = '/api/2026';
  const BOOKMARK_STORAGE_KEY = 'cpns2026_bookmarks_v1';
  const CHECKLIST_STORAGE_KEY = 'cpns2026_checklist_v1';
  const THEME_STORAGE_KEY = 'cpns2024_theme';
  const MAX_BOOKMARKS = 4;

  const state = {
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 1,
    totalKuotaFiltered: 0,
    q: '',
    instansi: '',
    jurusan: '',
    eselon1: '',
    jabatan: '',
    lokasi: '',
    jenjang: '',
    jenis_formasi: '',
    min_kuota: '',
    keketatan_2024: '',
    sort_by: 'no_urut',
    only_saved: false,
    analyticsOpen: false,
    viewMode: window.innerWidth < 768 ? 'cards' : 'table',
    hasApplicantData: false,
    hasSalaryData: false,
    distinctInstansi: 13,
    bookmarks: [],
    currentItems: [],
    activeDetail: null,
    detailCache: new Map(),
    detailAbortController: null,
    tableAbortController: null,
    analyticsAbortController: null,
    jurusanAbortController: null,
    compareAbortController: null,
    lastFocusedEl: null,
    toastTimer: null,
  };

  let qTimer = null;
  let lokTimer = null;
  let jurusanTimer = null;
  let jurTableTimer = null;

  function cancelFilterTimers() {
    clearTimeout(qTimer);
    clearTimeout(lokTimer);
    clearTimeout(jurusanTimer);
    clearTimeout(jurTableTimer);
    if (state.jurusanAbortController) {
      state.jurusanAbortController.abort();
      state.jurusanAbortController = null;
    }
  }

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(val) {
    if (val === null || val === undefined) return '';
    return String(val)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatInt(val) {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
    return Number(val).toLocaleString('id-ID');
  }

  function formatRp(val) {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
    return 'Rp ' + Math.round(Number(val)).toLocaleString('id-ID');
  }

  function formatQuota(val) {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
    return formatInt(val) + ' kursi';
  }

  function formatSalaryRange(minVal, maxVal) {
    if (!minVal || minVal <= 0) return '—';
    if (maxVal && maxVal > minVal) return formatRp(minVal) + ' – ' + formatRp(maxVal);
    return formatRp(minVal);
  }

  function renderKeketatan2024Badge(status) {
    if (!status) return '';
    const cls = status.includes('Longgar')
      ? 'badge-loose'
      : status.includes('Ketat')
      ? 'badge-tight'
      : status === 'Tanpa Pelamar'
      ? 'badge-neutral'
      : 'badge-mod';
    return '<span class="badge ' + cls + '">' + escapeHtml(status) + '</span>';
  }

  function formatRasio2024(item) {
    if (!item || item.kursi_2024 === null || item.kursi_2024 === undefined) return '';
    if (!item.pelamar_2024 || item.pelamar_2024 <= 0) return '0 pelamar';
    return '1 : ' + Number(item.rasio_2024).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function renderCompare2024Cell(item) {
    if (item.kursi_2024 === null || item.kursi_2024 === undefined) {
      return '<div class="compare-2024-sub" style="margin-top:0;">Tidak ada pembanding di 2024</div>';
    }
    const rasioText = formatRasio2024(item);
    return (
      '<div class="quota-num" style="font-size:0.8rem;">' +
      formatInt(item.kursi_2024) +
      ' kursi • ' +
      formatInt(item.pelamar_2024) +
      ' pelamar</div>' +
      '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-top:4px;">' +
      renderKeketatan2024Badge(item.status_keketatan_2024) +
      '<span class="applicant-num">' +
      escapeHtml(rasioText) +
      '</span></div>' +
      '<div class="compare-2024-sub" title="' +
      escapeHtml(item.match_label_2024 || '') +
      '">' +
      escapeHtml(item.match_label_2024 || '') +
      '</div>'
    );
  }

  function showToast(msg, tone) {
    const banner = $('toast-banner');
    const txt = $('toast-message');
    if (!banner || !txt) return;
    txt.textContent = msg;
    banner.className = 'toast-banner' + (tone ? ' tone-' + tone : '');
    banner.classList.remove('hidden');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => banner.classList.add('hidden'), 2800);
  }

  function loadBookmarks() {
    try {
      const raw = localStorage.getItem(BOOKMARK_STORAGE_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      state.bookmarks = Array.isArray(arr) ? arr.slice(0, MAX_BOOKMARKS) : [];
    } catch (e) {
      state.bookmarks = [];
    }
    updateBookmarkBadges();
  }

  function saveBookmarks() {
    try {
      localStorage.setItem(BOOKMARK_STORAGE_KEY, JSON.stringify(state.bookmarks));
    } catch (e) {}
    updateBookmarkBadges();
  }

  function updateBookmarkBadges() {
    const badge = $('compare-count-badge');
    const presetCnt = $('preset-bookmark-count');
    const count = state.bookmarks.length;
    if (badge) {
      badge.textContent = String(count);
      badge.classList.toggle('hidden', count === 0);
    }
    if (presetCnt) {
      presetCnt.textContent = String(count);
    }
  }

  function toggleBookmark(formasiId) {
    const idx = state.bookmarks.indexOf(formasiId);
    if (idx >= 0) {
      state.bookmarks.splice(idx, 1);
      saveBookmarks();
      showToast('Dihapus dari daftar Bandingkan.', 'warn');
    } else {
      if (state.bookmarks.length >= MAX_BOOKMARKS) {
        showToast('Maksimal 4 formasi dapat dibandingkan sekaligus.', 'warn');
        return;
      }
      state.bookmarks.push(formasiId);
      saveBookmarks();
      showToast('Disimpan untuk dibandingkan (' + state.bookmarks.length + '/4).', 'success');
    }
    renderCurrentView();
    updateDetailBookmarkBtn();
    if (state.only_saved) {
      loadFormasiTable();
    }
  }

  function updateDetailBookmarkBtn() {
    const btn = $('btn-detail-bookmark');
    if (!btn || !state.activeDetail) return;
    const saved = state.bookmarks.includes(state.activeDetail.formasi_id);
    btn.textContent = saved ? 'Hapus dari Bandingkan' : 'Simpan ke Bandingkan';
  }

  async function apiGet(path, params, options) {
    const url = new URL(API_BASE + path, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && String(v).trim() !== '') {
          url.searchParams.set(k, String(v));
        }
      });
    }
    const fetchOpts = {};
    if (options && options.signal) {
      fetchOpts.signal = options.signal;
    }
    const res = await fetch(url.toString(), fetchOpts);
    if (!res.ok) {
      throw new Error('HTTP ' + res.status);
    }
    return res.json();
  }

  function buildActiveQueryParams() {
    return {
      q: state.q,
      instansi: state.instansi,
      jurusan: state.jurusan,
      eselon1: state.eselon1,
      jabatan: state.jabatan,
      lokasi: state.lokasi,
      jenjang: state.jenjang,
      jenis_formasi: state.jenis_formasi,
      min_kuota: state.min_kuota,
      keketatan_2024: state.keketatan_2024,
      sort_by: state.sort_by,
    };
  }

  async function loadStats() {
    try {
      const d = await apiGet('/stats');
      state.hasApplicantData = !!d.has_applicant_data;
      state.hasSalaryData = !!d.has_salary_data;
      state.distinctInstansi = Number(d.distinct_instansi) || 13;
      $('kpi-total-rows').textContent = formatInt(d.total_formasi_rows);
      $('kpi-total-kuota').textContent = formatInt(d.total_kuota) + ' kursi';
      $('kpi-total-instansi').textContent = formatInt(d.distinct_instansi) + ' instansi';
      $('kpi-total-pelamar').textContent = d.has_applicant_data ? formatInt(d.total_pelamar) : '—';
      if ($('btn-preset-all')) {
        $('btn-preset-all').textContent = 'Semua (' + formatInt(d.total_formasi_rows) + ')';
      }
      if ($('analytics-jabatan-meta')) {
        $('analytics-jabatan-meta').textContent = 'Total ' + formatInt(d.total_kuota) + ' kursi';
      }
      if ($('telemetry-active-instansi') && !state.instansi) {
        $('telemetry-active-instansi').textContent = 'Semua Instansi (' + formatInt(d.distinct_instansi) + ' K/L)';
      }
      $('kpi-median-gaji').textContent =
        d.has_salary_data && d.median_gaji_min
          ? formatRp(d.median_gaji_min)
          : '—';
      $('kpi-avg-rasio').textContent =
        d.has_applicant_data && d.avg_rasio !== null ? '1 : ' + d.avg_rasio : '—';
    } catch (err) {
      showToast('Gagal memuat statistik ringkasan 2026.', 'warn');
    }
  }

  async function loadFilters() {
    try {
      const f = await apiGet('/filters');
      const instSel = $('filter-instansi');
      if (instSel) {
        const curInst = instSel.value;
        const instList = f.instansi_summary || (f.instansi || []).map((nm) => ({ instansi_nm: nm, total_kuota: null }));
        instSel.innerHTML = '<option value="">Semua Instansi (' + instList.length + ')</option>';
        instList.forEach((item) => {
          const opt = document.createElement('option');
          opt.value = item.instansi_nm;
          if (item.known_kuota_cnt === 0) {
            opt.textContent = item.instansi_nm + ' (' + formatInt(item.formasi_count) + ' baris • kuota —)';
          } else {
            opt.textContent = item.total_kuota !== null
              ? item.instansi_nm + ' (' + formatInt(item.total_kuota) + ' kursi)'
              : item.instansi_nm;
          }
          instSel.appendChild(opt);
        });
        instSel.value = curInst;
        if ($('badge-instansi-count')) {
          $('badge-instansi-count').textContent = instList.length + ' instansi';
        }
      }

      const eselSel = $('filter-eselon1');
      if (eselSel) {
        const cur = eselSel.value;
        eselSel.innerHTML = '<option value="">Semua Unit Eselon I (' + f.unit_eselon1.length + ')</option>';
        f.unit_eselon1.forEach((item) => {
          const opt = document.createElement('option');
          opt.value = item.unit_eselon1;
          opt.textContent = item.known_kuota_cnt === 0
            ? item.unit_eselon1 + ' (' + formatInt(item.formasi_count) + ' baris • kuota —)'
            : item.unit_eselon1 + ' (' + formatInt(item.total_kuota) + ' kursi)';
          eselSel.appendChild(opt);
        });
        eselSel.value = cur;
        if ($('badge-eselon1-count')) {
          $('badge-eselon1-count').textContent = f.unit_eselon1.length + ' unit';
        }
      }

      const jabSel = $('filter-jabatan');
      if (jabSel) {
        const cur = jabSel.value;
        jabSel.innerHTML = '<option value="">Semua Jabatan (' + f.jabatan.length + ')</option>';
        f.jabatan.forEach((item) => {
          const opt = document.createElement('option');
          opt.value = item.jabatan_nm;
          opt.textContent = item.known_kuota_cnt === 0
            ? item.jabatan_nm + ' (' + formatInt(item.formasi_count) + ' • kuota —)'
            : item.jabatan_nm + ' (' + formatInt(item.total_kuota) + ')';
          jabSel.appendChild(opt);
        });
        jabSel.value = cur;
        if ($('badge-jabatan-count')) {
          $('badge-jabatan-count').textContent = f.jabatan.length + ' jabatan';
        }
      }

      const jenjSel = $('filter-jenjang');
      if (jenjSel) {
        const cur = jenjSel.value;
        jenjSel.innerHTML = '<option value="">Semua Jenjang</option>';
        f.jenjang.forEach((j) => {
          const opt = document.createElement('option');
          opt.value = j;
          opt.textContent = j;
          jenjSel.appendChild(opt);
        });
        jenjSel.value = cur;
      }

      const jenisSel = $('filter-jenis-formasi');
      if (jenisSel) {
        const curJenis = jenisSel.value;
        const jList = f.jenis_formasi || [];
        if (f.has_jenis_formasi && jList.length) {
          jenisSel.disabled = false;
          jenisSel.style.opacity = '';
          jenisSel.style.cursor = '';
          jenisSel.innerHTML = '<option value="">Semua Jalur</option>';
          jList.forEach((jf) => {
            const opt = document.createElement('option');
            opt.value = jf;
            opt.textContent = jf;
            jenisSel.appendChild(opt);
          });
          jenisSel.value = curJenis;
        } else {
          jenisSel.disabled = true;
          jenisSel.style.opacity = '0.58';
          jenisSel.style.cursor = 'not-allowed';
          jenisSel.innerHTML = '<option value="">— Belum rilis</option>';
        }
      }

      const k24Sel = $('filter-keketatan-2024');
      if (k24Sel) {
        const curK24 = k24Sel.value;
        const k24List = f.status_keketatan_2024 || [];
        k24Sel.innerHTML = '<option value="">Semua Pembanding 2024</option>';
        k24List.forEach((item) => {
          const opt = document.createElement('option');
          opt.value = item.status;
          opt.textContent = item.status + ' (' + formatInt(item.formasi_count) + ' baris)';
          k24Sel.appendChild(opt);
        });
        if ((f.unmatched_2024_count || 0) > 0) {
          const optNone = document.createElement('option');
          optNone.value = '__NONE__';
          optNone.textContent = 'Tanpa Pembanding 2024 (' + formatInt(f.unmatched_2024_count) + ' baris)';
          k24Sel.appendChild(optNone);
        }
        k24Sel.value = curK24;
      }
    } catch (err) {
      showToast('Gagal memuat daftar filter CPNS 2026.', 'warn');
    }
  }

  function handleJurusanInput(val) {
    clearTimeout(jurusanTimer);
    if (state.jurusanAbortController) {
      state.jurusanAbortController.abort();
      state.jurusanAbortController = null;
    }
    jurusanTimer = setTimeout(async () => {
      const pop = $('jurusan-popover');
      if (!pop) return;
      const controller = new AbortController();
      state.jurusanAbortController = controller;
      try {
        const items = await apiGet('/filters/jurusan', { q: val, limit: 25 }, { signal: controller.signal });
        if (state.jurusanAbortController !== controller) return;
        if (!items.length) {
          pop.innerHTML = '<div class="autocomplete-empty">Program studi tidak ditemukan</div>';
        } else {
          pop.innerHTML = items
            .map(
              (it) =>
                '<button type="button" role="option" class="autocomplete-item" data-val="' +
                escapeHtml(it.jurusan_nm) +
                '">' +
                '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
                escapeHtml(it.jurusan_nm) +
                '</span>' +
                '<span class="num" style="font-size:0.75rem;color:var(--color-accent-ink);">' +
                formatInt(it.total_kuota) +
                ' kursi</span></button>'
            )
            .join('');
        }
        pop.classList.remove('hidden');
      } catch (e) {
        if (e && e.name === 'AbortError') return;
        pop.classList.add('hidden');
      }
    }, 180);
  }

  function updateClearButtons() {
    if ($('btn-clear-q')) $('btn-clear-q').classList.toggle('hidden', !state.q);
    if ($('btn-clear-jurusan')) $('btn-clear-jurusan').classList.toggle('hidden', !state.jurusan);
    if ($('btn-clear-lokasi')) $('btn-clear-lokasi').classList.toggle('hidden', !state.lokasi);
  }

  function syncPresetHighlight() {
    document.querySelectorAll('.preset-chip').forEach((btn) => {
      const p = btn.getAttribute('data-preset');
      let active = false;
      if (p === 'saved') {
        active = state.only_saved;
      } else if (!state.only_saved) {
        if (p === 'all' && !state.instansi && !state.jenjang && !state.jenis_formasi && !state.min_kuota && !state.keketatan_2024 && !state.eselon1 && !state.jabatan && !state.jurusan && !state.q && !state.lokasi) {
          active = true;
        } else if (p === 'sma' && state.jenjang === 'SMA/SMK') {
          active = true;
        } else if (p === 's1' && state.jenjang === 'D-IV/S-1') {
          active = true;
        } else if (p === 'd3' && state.jenjang === 'D-III') {
          active = true;
        } else if (p === 'big_kuota' && String(state.min_kuota) === '10') {
          active = true;
        }
      }
      btn.classList.toggle('is-active', active);
    });
  }

  function renderActiveChips() {
    const bar = $('active-chips-bar');
    const list = $('active-chips-list');
    if (!bar || !list) return;

    const chips = [];
    if (state.only_saved) {
      chips.push({ key: 'saved', label: 'Mode: Tersimpan (' + state.bookmarks.length + ')' });
    } else {
      if (state.q) chips.push({ key: 'q', label: 'Cari: "' + state.q + '"' });
      if (state.instansi) chips.push({ key: 'instansi', label: 'Instansi: ' + state.instansi });
      if (state.jurusan) chips.push({ key: 'jurusan', label: 'Prodi: ' + state.jurusan });
      if (state.eselon1) chips.push({ key: 'eselon1', label: 'Unit: ' + state.eselon1 });
      if (state.jabatan) chips.push({ key: 'jabatan', label: 'Jabatan: ' + state.jabatan });
      if (state.lokasi) chips.push({ key: 'lokasi', label: 'Penempatan: ' + state.lokasi });
      if (state.jenjang) chips.push({ key: 'jenjang', label: 'Jenjang: ' + state.jenjang });
      if (state.jenis_formasi) chips.push({ key: 'jenis_formasi', label: 'Jalur: ' + state.jenis_formasi });
      if (state.min_kuota) chips.push({ key: 'min_kuota', label: 'Alokasi >= ' + state.min_kuota });
      if (state.keketatan_2024) {
        chips.push({
          key: 'keketatan_2024',
          label: 'Keketatan 2024: ' + (state.keketatan_2024 === '__NONE__' ? 'Tanpa Pembanding' : state.keketatan_2024),
        });
      }
    }
    if ($('telemetry-active-instansi')) {
      $('telemetry-active-instansi').textContent = state.only_saved
        ? 'Mode Tersimpan (' + state.bookmarks.length + ')'
        : state.instansi || 'Semua Instansi (' + formatInt(state.distinctInstansi) + ' K/L)';
    }

    if (!chips.length) {
      bar.classList.add('hidden');
      list.innerHTML = '';
      return;
    }
    bar.classList.remove('hidden');
    list.innerHTML = chips
      .map(
        (c) =>
          '<button type="button" class="filter-chip" data-clear-key="' +
          escapeHtml(c.key) +
          '">' +
          '<span>' +
          escapeHtml(c.label) +
          '</span><span aria-hidden="true">×</span></button>'
      )
      .join('');
  }

  function sortSavedItems(items, sortBy) {
    const arr = items.slice();
    const numAsc = (a, b, fn) => {
      const va = fn(a);
      const vb = fn(b);
      if (va === null || va === undefined) return vb === null || vb === undefined ? 0 : 1;
      if (vb === null || vb === undefined) return -1;
      return va - vb;
    };
    const numDesc = (a, b, fn) => {
      const va = fn(a);
      const vb = fn(b);
      if (va === null || va === undefined) return vb === null || vb === undefined ? 0 : 1;
      if (vb === null || vb === undefined) return -1;
      return vb - va;
    };
    if (sortBy === 'kuota_desc') arr.sort((a, b) => numDesc(a, b, (x) => x.jumlah_formasi));
    else if (sortBy === 'kuota_asc') arr.sort((a, b) => numAsc(a, b, (x) => x.jumlah_formasi));
    else if (sortBy === 'jabatan_asc') arr.sort((a, b) => String(a.jabatan_nm || '').localeCompare(String(b.jabatan_nm || '')));
    else if (sortBy === 'eselon1_asc') arr.sort((a, b) => String(a.unit_eselon1 || '').localeCompare(String(b.unit_eselon1 || '')));
    else if (sortBy === 'gaji_desc') arr.sort((a, b) => numDesc(a, b, (x) => x.gaji_max));
    else if (sortBy === 'rasio_2024_asc') arr.sort((a, b) => numAsc(a, b, (x) => x.rasio_2024));
    else if (sortBy === 'rasio_2024_desc') arr.sort((a, b) => numDesc(a, b, (x) => x.rasio_2024));
    return arr;
  }

  function pruneOrphanedBookmarks(returnedItems) {
    if (!Array.isArray(returnedItems)) return;
    const validSet = new Set(returnedItems.map((it) => it.formasi_id));
    const pruned = state.bookmarks.filter((id) => validSet.has(id));
    if (pruned.length !== state.bookmarks.length) {
      state.bookmarks = pruned;
      saveBookmarks();
    }
  }

  async function loadFormasiTable() {
    if (state.tableAbortController) {
      state.tableAbortController.abort();
    }
    const controller = new AbortController();
    state.tableAbortController = controller;

    const loader = $('table-loading-indicator');
    if (loader) loader.classList.remove('hidden');
    updateClearButtons();
    syncPresetHighlight();
    renderActiveChips();

    try {
      if (state.only_saved) {
        if (!state.bookmarks.length) {
          state.currentItems = [];
          state.total = 0;
          state.totalKuotaFiltered = 0;
          state.totalPages = 1;
        } else {
          const items = await apiGet('/formasi-batch', { ids: state.bookmarks.join(',') }, { signal: controller.signal });
          if (state.tableAbortController !== controller) return;
          pruneOrphanedBookmarks(items);
          const sorted = sortSavedItems(items, state.sort_by);
          state.currentItems = sorted;
          state.total = sorted.length;
          state.totalKuotaFiltered = sorted.reduce((acc, it) => acc + (it.jumlah_formasi || 0), 0);
          state.totalPages = 1;
          renderActiveChips();
        }
      } else {
        const res = await apiGet(
          '/formasi',
          {
            ...buildActiveQueryParams(),
            page: state.page,
            limit: state.limit,
          },
          { signal: controller.signal }
        );
        if (state.tableAbortController !== controller) return;
        state.currentItems = res.items || [];
        state.total = res.total || 0;
        state.totalKuotaFiltered = res.total_kuota_filtered || 0;
        state.totalPages = res.total_pages || 1;
      }

      $('telemetry-filtered-rows').textContent = formatInt(state.total);
      $('telemetry-filtered-kuota').textContent = formatInt(state.totalKuotaFiltered);
      renderCurrentView();
      renderPagination();
      if (state.analyticsOpen && !state.only_saved) {
        loadAnalytics();
      }
    } catch (err) {
      if (err && err.name === 'AbortError') return;
      showToast('Gagal memuat daftar formasi CPNS 2026.', 'warn');
    } finally {
      if (loader && state.tableAbortController === controller) loader.classList.add('hidden');
    }
  }

  function renderMajorTagsHtml(majors, formasiId) {
    if (!majors || !majors.length) return '<span class="muted-note">—</span>';
    const shown = majors.slice(0, 3);
    const hiddenCount = majors.length - shown.length;
    let html = '<div class="major-tag-list">';
    shown.forEach((m) => {
      html += '<span class="major-tag">' + escapeHtml(m) + '</span>';
    });
    if (hiddenCount > 0) {
      html +=
        '<button type="button" class="major-more-btn" data-open-detail="' +
        escapeHtml(formasiId) +
        '">+' +
        hiddenCount +
        ' lainnya</button>';
    }
    html += '</div>';
    return html;
  }

  function renderKeketatanBadge(item) {
    if (item.status_keketatan) {
      const cls =
        item.status_keketatan === 'Longgar'
          ? 'badge-loose'
          : item.status_keketatan === 'Ketat'
          ? 'badge-tight'
          : 'badge-mod';
      return '<span class="badge ' + cls + '">' + escapeHtml(item.status_keketatan) + '</span>';
    }
    return '<span class="badge badge-neutral" title="Menunggu data pendaftar SSCASN 2026">—</span>';
  }

  function renderCurrentView() {
    const emptyEl = $('empty-state');
    const tableWrap = $('table-view-wrap');
    const cardsWrap = $('cards-view-wrap');
    const pagBar = $('pagination-bar');
    const scrollNotice = $('mobile-scroll-notice');

    if (!state.currentItems.length) {
      emptyEl.classList.remove('hidden');
      tableWrap.classList.add('hidden');
      cardsWrap.classList.add('hidden');
      pagBar.classList.add('hidden');
      if (scrollNotice) scrollNotice.classList.add('hidden');
      return;
    }

    emptyEl.classList.add('hidden');
    pagBar.classList.remove('hidden');

    const isCards = state.viewMode === 'cards';
    $('btn-view-table').classList.toggle('is-active', !isCards);
    $('btn-view-cards').classList.toggle('is-active', isCards);
    $('btn-view-table').setAttribute('aria-pressed', String(!isCards));
    $('btn-view-cards').setAttribute('aria-pressed', String(isCards));

    tableWrap.classList.toggle('hidden', isCards);
    cardsWrap.classList.toggle('hidden', !isCards);
    if (scrollNotice) scrollNotice.classList.toggle('hidden', isCards);

    if (isCards) {
      renderMobileCards();
    } else {
      renderTableRows();
    }
  }

  function renderTableRows() {
    const tbody = $('table-tbody');
    tbody.innerHTML = state.currentItems
      .map((item) => {
        const saved = state.bookmarks.includes(item.formasi_id);
        const hasQuota = item.jumlah_formasi !== null && item.jumlah_formasi !== undefined;
        const pelamarSub = !hasQuota
          ? 'Kuota belum rilis'
          : (item.jumlah_pelamar !== null && item.jumlah_pelamar !== undefined
              ? formatInt(item.jumlah_pelamar) + ' pelamar'
              : 'Pelamar: —');
        const isSscasnSalary = (item.sumber_dokumen || '').includes('SSCASN');
        const gajiHtml =
          item.gaji_min && item.gaji_min > 0
            ? '<div class="salary-range">' + formatSalaryRange(item.gaji_min, item.gaji_max) + '</div><div class="salary-sub" style="color:var(--color-accent-ink);">' + (isSscasnSalary ? 'Resmi BKN' : 'Resmi Instansi') + '</div>'
            : '<div class="salary-range" style="color:var(--color-text-muted);">—</div><div class="salary-sub">Belum rilis</div>';
        const jalurHtml = item.jenis_formasi
          ? '<span class="badge badge-accent">' + escapeHtml(item.jenis_formasi) + '</span>'
          : '<span class="badge badge-neutral">Jalur: —</span>';

        return (
          '<tr>' +
          '<td class="row-idx">#' +
          escapeHtml(item.no_urut) +
          '</td>' +
          '<td>' +
          '<div class="jabatan-title">' +
          escapeHtml(item.jabatan_nm) +
          '</div>' +
          '<div class="agency-name" style="margin-top:3px;">' +
          escapeHtml(item.unit_eselon1) +
          '</div>' +
          '<div class="jabatan-meta">' +
          '<span class="badge badge-accent">' +
          escapeHtml(item.jenjang) +
          '</span>' +
          jalurHtml +
          '<code class="uuid-code">' +
          escapeHtml(item.formasi_id) +
          '</code>' +
          '</div>' +
          '</td>' +
          '<td>' +
          '<div class="agency-name">' +
          escapeHtml(item.instansi_nm) +
          ' (' +
          escapeHtml(item.kategori_instansi) +
          ')</div>' +
          '<div class="location-line">' +
          escapeHtml(item.lokasi_nm) +
          '</div>' +
          '</td>' +
          '<td>' +
          renderMajorTagsHtml(item.jurusan_list, item.formasi_id) +
          '</td>' +
          '<td class="col-num">' +
          '<div class="quota-num">' +
          formatQuota(item.jumlah_formasi) +
          '</div>' +
          '<div class="applicant-num">' +
          escapeHtml(pelamarSub) +
          '</div>' +
          '</td>' +
          '<td class="col-center">' +
          renderKeketatanBadge(item) +
          '</td>' +
          '<td>' +
          renderCompare2024Cell(item) +
          '</td>' +
          '<td>' +
          gajiHtml +
          '</td>' +
          '<td class="col-center">' +
          '<div class="row-actions">' +
          '<button type="button" class="bookmark-btn ' +
          (saved ? 'is-saved' : '') +
          '" data-toggle-bookmark="' +
          escapeHtml(item.formasi_id) +
          '" title="' +
          (saved ? 'Hapus dari Bandingkan' : 'Simpan ke Bandingkan') +
          '" aria-label="Simpan formasi" aria-pressed="' +
          String(saved) +
          '">★</button>' +
          '<button type="button" class="btn btn-secondary btn-sm" data-open-detail="' +
          escapeHtml(item.formasi_id) +
          '">Detail</button>' +
          '</div>' +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function renderMobileCards() {
    const wrap = $('cards-view-wrap');
    wrap.innerHTML = state.currentItems
      .map((item) => {
        const saved = state.bookmarks.includes(item.formasi_id);
        const jalurBadge = item.jenis_formasi
          ? ' <span class="badge badge-neutral">' + escapeHtml(item.jenis_formasi) + '</span>'
          : '';
        return (
          '<article class="formation-card">' +
          '<div>' +
          '<div class="formation-card-top">' +
          '<div>' +
          '<span class="row-idx">#' +
          escapeHtml(item.no_urut) +
          '</span> ' +
          '<span class="badge badge-accent">' +
          escapeHtml(item.jenjang) +
          '</span>' +
          jalurBadge +
          '<h3 class="jabatan-title" style="margin-top:6px;">' +
          escapeHtml(item.jabatan_nm) +
          '</h3>' +
          '</div>' +
          '<button type="button" class="bookmark-btn ' +
          (saved ? 'is-saved' : '') +
          '" data-toggle-bookmark="' +
          escapeHtml(item.formasi_id) +
          '" aria-label="Simpan formasi" aria-pressed="' +
          String(saved) +
          '">★</button>' +
          '</div>' +
          '<div class="agency-name" style="margin-top:4px;font-weight:600;color:var(--color-text-primary);">' +
          escapeHtml(item.instansi_nm) +
          '</div>' +
          '<div class="agency-name" style="margin-top:2px;">' +
          escapeHtml(item.unit_eselon1) +
          '</div>' +
          '<div class="location-line">' +
          escapeHtml(item.lokasi_nm) +
          '</div>' +
          '<div style="margin-top:8px;">' +
          renderMajorTagsHtml(item.jurusan_list, item.formasi_id) +
          '</div>' +
          '<div style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--color-border-subtle);font-size:0.78rem;">' +
          '<span style="color:var(--color-text-muted);font-weight:600;">Pembanding 2024: </span>' +
          (item.kursi_2024 !== null && item.kursi_2024 !== undefined
            ? '<strong>' + formatInt(item.kursi_2024) + ' kursi</strong> • <strong>' + formatInt(item.pelamar_2024) + ' pelamar</strong> (' + escapeHtml(item.status_keketatan_2024 || '') + ', ' + escapeHtml(formatRasio2024(item)) + ')'
            : '<span class="muted-note">Tidak ada pembanding di 2024</span>') +
          '</div>' +
          '</div>' +
          '<div>' +
          '<div class="formation-card-metrics">' +
          '<div><div class="metric-pair-label">Alokasi CPNS</div><div class="metric-pair-val">' +
          formatQuota(item.jumlah_formasi) +
          '</div></div>' +
          '<div><div class="metric-pair-label">Pelamar / Rasio</div><div class="metric-pair-val">' +
          (item.jumlah_pelamar !== null ? formatInt(item.jumlah_pelamar) : '— (Belum rilis)') +
          '</div></div>' +
          '<div><div class="metric-pair-label">Gaji Resmi</div><div class="metric-pair-val">' +
          formatSalaryRange(item.gaji_min, item.gaji_max) +
          '</div></div>' +
          '<div style="display:flex;align-items:flex-end;justify-content:flex-end;">' +
          '<button type="button" class="btn btn-secondary btn-sm" data-open-detail="' +
          escapeHtml(item.formasi_id) +
          '">Lihat Detail</button>' +
          '</div>' +
          '</div>' +
          '</div>' +
          '</article>'
        );
      })
      .join('');
  }

  function renderPagination() {
    const sum = $('pagination-summary');
    const ctrl = $('pagination-controls');
    if (state.only_saved) {
      sum.textContent = 'Menampilkan ' + state.total + ' formasi tersimpan';
      ctrl.innerHTML = '';
      return;
    }
    const start = state.total === 0 ? 0 : (state.page - 1) * state.limit + 1;
    const end = Math.min(state.total, state.page * state.limit);
    sum.textContent =
      'Menampilkan ' + formatInt(start) + '–' + formatInt(end) + ' dari ' + formatInt(state.total) + ' baris';

    if (state.totalPages <= 1) {
      ctrl.innerHTML = '';
      return;
    }

    const pages = [];
    pages.push(1);
    for (let p = Math.max(2, state.page - 2); p <= Math.min(state.totalPages - 1, state.page + 2); p++) {
      pages.push(p);
    }
    if (state.totalPages > 1) pages.push(state.totalPages);
    const uniq = Array.from(new Set(pages)).sort((a, b) => a - b);

    let html =
      '<button type="button" class="page-btn" aria-label="Halaman sebelumnya" data-page="' +
      Math.max(1, state.page - 1) +
      '"' +
      (state.page <= 1 ? ' disabled' : '') +
      '>‹</button>';

    let prev = 0;
    uniq.forEach((p) => {
      if (p - prev > 1) html += '<span style="padding:0 4px;">…</span>';
      html +=
        '<button type="button" class="page-btn ' +
        (p === state.page ? 'is-active' : '') +
        '" data-page="' +
        p +
        '">' +
        p +
        '</button>';
      prev = p;
    });

    html +=
      '<button type="button" class="page-btn" aria-label="Halaman berikutnya" data-page="' +
      Math.min(state.totalPages, state.page + 1) +
      '"' +
      (state.page >= state.totalPages ? ' disabled' : '') +
      '>›</button>';

    ctrl.innerHTML = html;
  }

  async function loadAnalytics() {
    if (state.analyticsAbortController) {
      state.analyticsAbortController.abort();
    }
    const controller = new AbortController();
    state.analyticsAbortController = controller;
    try {
      const d = await apiGet('/analytics/top', buildActiveQueryParams(), { signal: controller.signal });
      if (state.analyticsAbortController !== controller) return;
      const topJur = d.top_jurusan || [];
      const topEs1 = d.top_eselon1 || [];
      const topJab = d.top_jabatan || [];
      const jenj = d.jenjang_dist || [];
      const totalKuota = Math.max(1, d.total_kuota || 1);

      $('chart-top-jurusan').innerHTML = topJur.length
        ? topJur
            .map(
              (it, idx) =>
                '<button type="button" class="top-chart-btn ' +
                (state.jurusan === it.jurusan_nm ? 'is-active' : '') +
                '" data-chart-jurusan="' +
                escapeHtml(it.jurusan_nm) +
                '">' +
                '<div class="top-chart-head">' +
                '<div class="top-chart-label-wrap"><span class="top-chart-rank">#' +
                (idx + 1) +
                '</span><span class="top-chart-name">' +
                escapeHtml(it.jurusan_nm) +
                '</span></div>' +
                '<span class="top-chart-val">' +
                formatInt(it.total_kuota) +
                ' kursi</span>' +
                '</div>' +
                '<div class="top-chart-sub"><span>' +
                formatInt(it.formasi_count) +
                ' formasi</span><span>Pelamar: ' +
                (it.total_pelamar !== null ? formatInt(it.total_pelamar) : '—') +
                '</span></div></button>'
            )
            .join('')
        : '<div class="top-chart-empty">Tidak ada data jurusan.</div>';

      $('chart-top-eselon1').innerHTML = topEs1.length
        ? topEs1
            .map(
              (it, idx) =>
                '<button type="button" class="top-chart-btn ' +
                (state.eselon1 === it.unit_eselon1 ? 'is-active' : '') +
                '" data-chart-eselon1="' +
                escapeHtml(it.unit_eselon1) +
                '">' +
                '<div class="top-chart-head">' +
                '<div class="top-chart-label-wrap"><span class="top-chart-rank">#' +
                (idx + 1) +
                '</span><span class="top-chart-name">' +
                escapeHtml(it.unit_eselon1) +
                '</span></div>' +
                '<span class="top-chart-val">' +
                formatInt(it.total_kuota) +
                ' kursi</span>' +
                '</div>' +
                '<div class="top-chart-sub"><span>' +
                formatInt(it.formasi_count) +
                ' baris</span><span>' +
                ((it.total_kuota / totalKuota) * 100).toFixed(1) +
                '%</span></div></button>'
            )
            .join('')
        : '<div class="top-chart-empty">Tidak ada data unit.</div>';

      $('chart-top-jabatan').innerHTML = topJab
        .map((it) => {
          const pct = ((it.total_kuota / totalKuota) * 100).toFixed(1);
          return (
            '<button type="button" class="dist-row-btn ' +
            (state.jabatan === it.jabatan_nm ? 'is-active' : '') +
            '" data-chart-jabatan="' +
            escapeHtml(it.jabatan_nm) +
            '">' +
            '<div class="dist-row-top"><span style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
            escapeHtml(it.jabatan_nm) +
            '</span><strong class="num">' +
            formatInt(it.total_kuota) +
            '</strong></div>' +
            '<div class="dist-bar-track"><div class="dist-bar-fill" style="width:' +
            Math.max(4, Number(pct)) +
            '%;"></div></div>' +
            '<div class="dist-row-sub"><span>' +
            formatInt(it.formasi_count) +
            ' baris</span><span>' +
            pct +
            '%</span></div></button>'
          );
        })
        .join('');

      $('dist-jenjang').innerHTML = jenj
        .map((it) => {
          const pct = ((it.total_kuota / totalKuota) * 100).toFixed(1);
          return (
            '<button type="button" class="dist-row-btn ' +
            (state.jenjang === it.jenjang ? 'is-active' : '') +
            '" data-chart-jenjang="' +
            escapeHtml(it.jenjang) +
            '">' +
            '<div class="dist-row-top"><span style="font-weight:600;">' +
            escapeHtml(it.jenjang) +
            '</span><strong class="num">' +
            formatInt(it.total_kuota) +
            ' kursi</strong></div>' +
            '<div class="dist-bar-track"><div class="dist-bar-fill fill-loose" style="width:' +
            Math.max(4, Number(pct)) +
            '%;"></div></div>' +
            '<div class="dist-row-sub"><span>' +
            formatInt(it.formasi_count) +
            ' formasi</span><span>' +
            pct +
            '%</span></div></button>'
          );
        })
        .join('');

      const distKetEl = $('dist-keketatan');
      if (distKetEl) {
        const k26 = d.keketatan_dist || [];
        const k24 = d.keketatan_2024_dist || [];
        const totalRows = Math.max(1, d.total_rows || 1);
        if (d.has_applicant_data && k26.length) {
          distKetEl.innerHTML = k26
            .map((it) => {
              const pct = ((it.formasi_count / totalRows) * 100).toFixed(1);
              const fillCls =
                it.status_keketatan === 'Sangat Longgar' || it.status_keketatan === 'Tanpa Pelamar'
                  ? 'fill-loose'
                  : it.status_keketatan === 'Moderat'
                    ? 'fill-mod'
                    : 'fill-tight';
              return (
                '<div class="dist-row-btn" style="cursor:default;">' +
                '<div class="dist-row-top"><span style="font-weight:600;">' +
                escapeHtml(it.status_keketatan) +
                '</span><strong class="num">' +
                formatInt(it.formasi_count) +
                ' baris</strong></div>' +
                '<div class="dist-bar-track"><div class="dist-bar-fill ' +
                fillCls +
                '" style="width:' +
                Math.max(4, Number(pct)) +
                '%;"></div></div>' +
                '<div class="dist-row-sub"><span>' +
                formatInt(it.total_kuota) +
                ' kursi</span><span>' +
                pct +
                '%</span></div></div>'
              );
            })
            .join('');
        } else {
          const note =
            '<div style="font-size:0.75rem; color:var(--color-text-muted); margin-bottom:2px;">' +
            'Pelamar 2026 belum rilis (<strong>—</strong>). Acuan tingkat keketatan 2024:' +
            '</div>';
          if (!k24.length) {
            distKetEl.innerHTML =
              note + '<div class="top-chart-empty">Tidak ada data keketatan pembanding 2024 pada filter ini.</div>';
          } else {
            distKetEl.innerHTML =
              note +
              k24
                .map((it) => {
                  const pct = ((it.formasi_count / totalRows) * 100).toFixed(1);
                  const st = it.status_keketatan_2024 || '';
                  const fVal = it.filter_value || '';
                  let fillCls = '';
                  let extraStyle = '';
                  if (fVal === '__NONE__') {
                    extraStyle = 'background-color: var(--color-text-muted);';
                  } else if (st === 'Tanpa Pelamar' || st.includes('Longgar')) {
                    fillCls = 'fill-loose';
                  } else if (st === 'Moderat') {
                    fillCls = 'fill-mod';
                  } else {
                    fillCls = 'fill-tight';
                  }
                  const rasioHint =
                    it.avg_rasio_2024 !== null && it.avg_rasio_2024 !== undefined
                      ? 'Rerata 1:' + it.avg_rasio_2024
                      : formatInt(it.total_kuota) + ' kursi';
                  return (
                    '<button type="button" class="dist-row-btn ' +
                    (state.keketatan_2024 === fVal ? 'is-active' : '') +
                    '" data-chart-keketatan24="' +
                    escapeHtml(fVal) +
                    '">' +
                    '<div class="dist-row-top"><span style="font-weight:600;">' +
                    escapeHtml(st) +
                    '</span><strong class="num">' +
                    formatInt(it.formasi_count) +
                    ' baris</strong></div>' +
                    '<div class="dist-bar-track"><div class="dist-bar-fill ' +
                    fillCls +
                    '" style="width:' +
                    Math.max(4, Number(pct)) +
                    '%;' +
                    extraStyle +
                    '"></div></div>' +
                    '<div class="dist-row-sub"><span>' +
                    escapeHtml(rasioHint) +
                    '</span><span>' +
                    pct +
                    '%</span></div></button>'
                  );
                })
                .join('');
          }
        }
      }
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      showToast('Gagal memuat analitik CPNS 2026.', 'warn');
    }
  }

  function isPlainObject(val) {
    return !!val && typeof val === 'object' && !Array.isArray(val);
  }

  function hashChecklistText(prefix, text) {
    const norm = String(text || '').toLowerCase().replace(/\s+/g, ' ').trim();
    let h = 2166136261;
    for (let i = 0; i < norm.length; i++) {
      h ^= norm.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return prefix + '_' + (h >>> 0).toString(36);
  }

  function isSafeHttpUrl(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url.trim());
  }

  function loadChecklistMap() {
    try {
      const raw = localStorage.getItem(CHECKLIST_STORAGE_KEY);
      const obj = raw ? JSON.parse(raw) : {};
      return isPlainObject(obj) ? obj : {};
    } catch (e) {
      return {};
    }
  }

  function saveChecklistMap(map) {
    try {
      localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(map));
    } catch (e) {}
  }

  function getFormasiChecklist(formasiId) {
    const all = loadChecklistMap();
    const cur = all[formasiId];
    return isPlainObject(cur) ? cur : {};
  }

  function setFormasiChecklistItem(formasiId, key, checked) {
    const all = loadChecklistMap();
    if (!isPlainObject(all[formasiId])) {
      all[formasiId] = {};
    }
    if (checked) {
      all[formasiId][key] = true;
    } else {
      delete all[formasiId][key];
      if (!Object.keys(all[formasiId]).length) {
        delete all[formasiId];
      }
    }
    saveChecklistMap(all);
  }

  function clearFormasiChecklist(formasiId) {
    const all = loadChecklistMap();
    delete all[formasiId];
    saveChecklistMap(all);
  }

  function updateChecklistProgress(formasiId) {
    const body = $('detail-req-checklist-body');
    const prog = $('detail-req-progress');
    if (!body || !prog) return;
    const boxes = Array.from(body.querySelectorAll('input[type="checkbox"][data-check-key]'));
    const total = boxes.length;
    const done = boxes.filter((b) => b.checked).length;
    prog.textContent = done + ' / ' + total + ' siap';
    prog.className = 'badge ' + (total > 0 && done === total ? 'badge-loose' : 'badge-accent');
  }

  function renderRequirementsPanel(item) {
    const panel = $('detail-req-panel');
    if (!panel) return;
    const p = item && item.persyaratan_daftar ? item.persyaratan_daftar : null;
    if (!p) {
      panel.classList.add('hidden');
      return;
    }
    panel.classList.remove('hidden');

    const isComplete = p.status_pengumuman === 'lengkap';
    const badge = $('detail-req-status-badge');
    if (badge) {
      badge.className = 'badge ' + (isComplete ? 'badge-loose' : 'badge-mod');
      badge.textContent = isComplete ? 'Pengumuman Lengkap 2026' : 'Menunggu Pengumuman Resmi';
    }
    if ($('detail-req-nomor')) {
      $('detail-req-nomor').textContent = p.nomor_pengumuman || '—';
    }

    const linksEl = $('detail-req-links');
    if (linksEl) {
      const links = [];
      if (isSafeHttpUrl(p.portal_resmi)) {
        links.push(
          '<a href="' +
            escapeHtml(p.portal_resmi.trim()) +
            '" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm">Portal Instansi ↗</a>'
        );
      }
      if (isSafeHttpUrl(p.portal_sscasn)) {
        links.push(
          '<a href="' +
            escapeHtml(p.portal_sscasn.trim()) +
            '" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">Daftar SSCASN ↗</a>'
        );
      }
      linksEl.innerHTML = links.join('');
    }

    const pendingEl = $('detail-req-pending-notice');
    if (pendingEl) {
      if (!isComplete) {
        pendingEl.classList.remove('hidden');
        pendingEl.textContent =
          p.catatan_penting ||
          'Pengumuman pendaftaran resmi CPNS 2026 untuk instansi ini belum diterbitkan. Syarat usia, IPK, dan daftar berkas tidak ditebak dan akan diperbarui otomatis setelah pengumuman resmi terbit.';
      } else {
        pendingEl.classList.add('hidden');
        pendingEl.textContent = '';
      }
    }

    const schedEl = $('detail-req-schedule-strip');
    if (schedEl) {
      const sched = Array.isArray(p.jadwal_ringkas) ? p.jadwal_ringkas : [];
      if (sched.length) {
        schedEl.classList.remove('hidden');
        schedEl.innerHTML = sched
          .map(
            (s) =>
              '<div class="req-schedule-pill">' +
              '<span class="req-schedule-pill-stage">' +
              escapeHtml(s.tahap) +
              '</span>' +
              '<span class="req-schedule-pill-date">' +
              escapeHtml(s.tanggal) +
              '</span></div>'
          )
          .join('');
      } else {
        schedEl.classList.add('hidden');
        schedEl.innerHTML = '';
      }
    }

    const rulesEl = $('detail-req-rules-grid');
    if (rulesEl) {
      const cards = [];
      if (p.usia_formasi || p.usia_ringkas) {
        const val = p.usia_formasi ? p.usia_formasi + ' (formasi ini)' : p.usia_ringkas;
        const sub = p.usia_formasi && p.usia_ringkas ? 'Ketentuan instansi: ' + p.usia_ringkas : '';
        cards.push({ label: 'Batas Usia Pelamar', val, sub, full: false });
      }
      if (p.ipk_minimal || p.akreditasi) {
        cards.push({
          label: 'IPK / Nilai & Akreditasi',
          val: p.ipk_minimal || '—',
          sub: p.akreditasi || '',
          full: false,
        });
      }
      if (p.syarat_bahasa) {
        cards.push({ label: 'Syarat Bahasa Inggris', val: p.syarat_bahasa, sub: '', full: false });
      }
      if (p.syarat_fisik_khusus) {
        cards.push({
          label: 'Syarat Fisik & Kondisi Khusus',
          val: p.syarat_fisik_khusus,
          sub: '',
          full: !p.syarat_bahasa,
        });
      }
      if (p.tahapan_skb) {
        cards.push({
          label: 'Tahapan & Bobot SKB',
          val: p.tahapan_skb,
          sub: p.ikatan_dinas ? 'Ikatan Dinas / Mutasi: ' + p.ikatan_dinas : '',
          full: true,
        });
      } else if (p.ikatan_dinas) {
        cards.push({ label: 'Ikatan Dinas & Mutasi', val: p.ikatan_dinas, sub: '', full: true });
      }

      if (cards.length) {
        rulesEl.classList.remove('hidden');
        rulesEl.innerHTML = cards
          .map(
            (c) =>
              '<div class="req-rule-card' +
              (c.full ? ' is-full' : '') +
              '">' +
              '<div class="req-rule-label">' +
              escapeHtml(c.label) +
              '</div>' +
              '<div class="req-rule-val">' +
              escapeHtml(c.val) +
              '</div>' +
              (c.sub ? '<div class="req-rule-sub">' + escapeHtml(c.sub) + '</div>' : '') +
              '</div>'
          )
          .join('');
      } else {
        rulesEl.classList.add('hidden');
        rulesEl.innerHTML = '';
      }
    }

    const jdWrap = $('detail-req-jobdesc-wrap');
    const jdText = $('detail-req-jobdesc-text');
    if (jdWrap && jdText) {
      if (p.jobdesc) {
        jdWrap.classList.remove('hidden');
        jdWrap.open = false;
        jdText.textContent = p.jobdesc;
      } else {
        jdWrap.classList.add('hidden');
        jdText.textContent = '';
      }
    }

    const clWrap = $('detail-req-checklist-wrap');
    const clBody = $('detail-req-checklist-body');
    if (clWrap && clBody) {
      const savedMap = getFormasiChecklist(item.formasi_id);
      const groups = [];
      const sscasnDocs = Array.isArray(p.berkas_formasi_sscasn) ? p.berkas_formasi_sscasn : [];
      if (sscasnDocs.length) {
        groups.push({
          title: 'Dokumen Unggah Resmi di Portal SSCASN (Khusus Formasi Ini)',
          special: false,
          items: sscasnDocs.map((d) => ({
            key: hashChecklistText('sscasn', d.nama),
            text: d.nama,
            tag: d.wajib ? 'Wajib' : 'Opsional',
            isWajib: !!d.wajib,
          })),
        });
      }
      const jalurDocs = Array.isArray(p.berkas_khusus_jalur) ? p.berkas_khusus_jalur : [];
      if (jalurDocs.length) {
        groups.push({
          title: 'Berkas Tambahan Jalur ' + (p.jalur_aktif || 'Khusus'),
          special: true,
          items: jalurDocs.map((txt) => ({
            key: hashChecklistText('jalur', txt),
            text: txt,
            tag: 'Jalur Khusus',
            isWajib: true,
          })),
        });
      }
      const instDocs = Array.isArray(p.berkas_wajib_instansi) ? p.berkas_wajib_instansi : [];
      if (instDocs.length) {
        groups.push({
          title: sscasnDocs.length
            ? 'Ringkasan Kelengkapan Pengumuman Instansi (Panduan PDF)'
            : 'Berkas Persyaratan Resmi Pengumuman Instansi',
          special: false,
          items: instDocs.map((txt) => ({
            key: hashChecklistText('inst', txt),
            text: txt,
            tag: '',
            isWajib: true,
          })),
        });
      }

      if (groups.length) {
        clWrap.classList.remove('hidden');
        clBody.innerHTML = groups
          .map((g) => {
            const listHtml = g.items
              .map((it) => {
                const isChecked = !!savedMap[it.key];
                const tagHtml = it.tag
                  ? '<span class="req-check-tag ' +
                    (it.isWajib ? 'is-wajib' : 'is-opsional') +
                    '">' +
                    escapeHtml(it.tag) +
                    '</span>'
                  : '';
                return (
                  '<label class="req-check-item' +
                  (g.special ? ' is-special' : '') +
                  (isChecked ? ' is-checked' : '') +
                  '">' +
                  '<input type="checkbox" class="req-check-box" data-check-key="' +
                  escapeHtml(it.key) +
                  '"' +
                  (isChecked ? ' checked' : '') +
                  ' />' +
                  '<span class="req-check-text">' +
                  tagHtml +
                  escapeHtml(it.text) +
                  '</span></label>'
                );
              })
              .join('');
            return (
              '<div><div class="req-group-title">' +
              escapeHtml(g.title) +
              '</div><div class="req-check-list">' +
              listHtml +
              '</div></div>'
            );
          })
          .join('');
        updateChecklistProgress(item.formasi_id);
      } else {
        clWrap.classList.add('hidden');
        clBody.innerHTML = '';
      }
    }

    const catEl = $('detail-req-catatan');
    if (catEl) {
      if (isComplete && p.catatan_penting) {
        catEl.classList.remove('hidden');
        catEl.textContent = 'Catatan resmi: ' + p.catatan_penting;
      } else {
        catEl.classList.add('hidden');
        catEl.textContent = '';
      }
    }
  }

  function recalculateSimulation() {
    const item = state.activeDetail;
    if (!item) return;

    const sliderVal = Number($('sim-tukin-pct').value || 50) / 100;
    const status = $('sim-status').value;
    const kel = $('sim-keluarga').value;
    const lblMap = { 0: 'Min (Pelaksana)', 0.5: 'Mid', 1: 'Max' };
    $('sim-tukin-label').textContent = lblMap[sliderVal] || Math.round(sliderVal * 100) + '%';

    const gapok100 = Number(item.gapok_pp5_100 || 2184000);
    const gapok = status === 'cpns' ? Math.round(gapok100 * 0.8) : gapok100;

    let spousePct = 0;
    let kids = 0;
    if (kel === 'k0') spousePct = 0.1;
    if (kel === 'k1') { spousePct = 0.1; kids = 1; }
    if (kel === 'k2') { spousePct = 0.1; kids = 2; }

    const tunjPasangan = Math.round(gapok * spousePct);
    const tunjAnak = Math.round(gapok * (0.02 * kids));
    const jiwaCount = 1 + (spousePct > 0 ? 1 : 0) + kids;
    const tunjBeras = jiwaCount * 72420;
    const totalKeluarga = tunjPasangan + tunjAnak + tunjBeras;

    const tMin = Number(item.tukin_min || 2575000);
    const tMax = Number(item.tukin_max || 46950000);
    const tukin = Math.round(tMin + (tMax - tMin) * sliderVal);

    const kotor = gapok + totalKeluarga + tukin;
    const iwp = Math.round((gapok + tunjPasangan + tunjAnak) * 0.1);
    const bersih = kotor - iwp;

    $('slip-gapok').textContent = formatRp(gapok);
    $('slip-tunj-keluarga').textContent = formatRp(totalKeluarga);
    $('slip-tukin').textContent = formatRp(tukin);
    $('slip-kotor').textContent = formatRp(kotor);
    $('slip-pot-iwp').textContent = '- ' + formatRp(iwp);
    $('slip-bersih').textContent = formatRp(bersih);
  }

  async function openDetailModal(formasiId) {
    const backdrop = $('modal-detail');
    const loading = $('modal-detail-loading');
    const loadingLabel = loading ? loading.querySelector('span') : null;
    if (backdrop.classList.contains('hidden')) {
      state.lastFocusedEl = document.activeElement;
    }
    backdrop.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    const modalBody = backdrop.querySelector('.modal-body');
    if (modalBody) modalBody.scrollTop = 0;

    if (state.detailAbortController) {
      state.detailAbortController.abort();
    }
    const controller = new AbortController();
    state.detailAbortController = controller;

    let didTimeout = false;
    let slowTimer = null;
    let timeoutTimer = null;
    const cached = state.detailCache.get(formasiId);
    if (!cached) {
      if (loadingLabel) loadingLabel.textContent = 'Memuat detail formasi...';
      loading.classList.remove('hidden');
      slowTimer = setTimeout(() => {
        if (loadingLabel && state.detailAbortController === controller) {
          loadingLabel.textContent = 'Menghubungi server (mungkin sedang bangun / sibuk)...';
        }
      }, 3500);
      timeoutTimer = setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, 25000);
    } else {
      loading.classList.add('hidden');
    }

    try {
      const item =
        cached || (await apiGet('/formasi/' + encodeURIComponent(formasiId), null, { signal: controller.signal }));
      if (!cached) {
        if (state.detailCache.size >= 100) {
          const oldestKey = state.detailCache.keys().next().value;
          state.detailCache.delete(oldestKey);
        }
        state.detailCache.set(formasiId, item);
      }
      if (state.detailAbortController !== controller) return;
      state.activeDetail = item;
      $('modal-detail-badge').textContent = item.status_keketatan
        ? item.status_keketatan
        : 'Menunggu rilis pelamar SSCASN';
      $('modal-detail-title').textContent = item.jabatan_nm;
      $('modal-detail-sub').textContent = item.instansi_nm + ' • ' + item.unit_eselon1;

      $('detail-kpi-kuota').textContent = formatQuota(item.jumlah_formasi);
      $('detail-kpi-rasio').textContent =
        item.jumlah_pelamar !== null && item.jumlah_pelamar !== undefined
          ? formatInt(item.jumlah_pelamar) +
            (item.rasio_kompetisi !== null && item.rasio_kompetisi !== undefined ? ' (' + item.rasio_kompetisi + ')' : '')
          : '—';
      $('detail-kpi-gaji').textContent = formatSalaryRange(item.gaji_min, item.gaji_max);
      if ($('detail-kpi-gaji-sub')) {
        const isSscasnSalary = (item.sumber_dokumen || '').includes('SSCASN');
        $('detail-kpi-gaji-sub').textContent =
          item.gaji_min > 0 ? (isSscasnSalary ? 'Resmi BKN (SSCASN)' : 'Pengumuman Instansi') : 'Belum dipublikasikan';
      }
      $('detail-kpi-no').textContent = 'No. ' + item.no_urut;
      if ($('detail-kpi-sumber')) {
        $('detail-kpi-sumber').textContent = item.sumber_dokumen || '—';
      }

      const fmtNum = (val, dec = 2) => {
        if (val === null || val === undefined) return '—';
        return Number(val).toLocaleString('id-ID', {
          minimumFractionDigits: dec,
          maximumFractionDigits: dec,
        });
      };

      const skd2026Note =
        'Acuan Ambang Batas SKD 2026 (KepmenPANRB No. 674/2026): Umum TWK ≥ 65 · TIU ≥ 80 · TKP ≥ 166; Cum Laude & Diaspora ≥ 311 (TIU ≥ 85); Disabilitas & Papua ≥ 286 (TIU ≥ 60).';
      const scoresGrid = $('detail-compare-2024-scores-grid');

      if ($('detail-compare-2024-text') && $('detail-compare-2024-badge')) {
        if (item.kursi_2024 !== null && item.kursi_2024 !== undefined) {
          const peluangStr = Number(item.peluang_2024_pct || 0).toLocaleString('id-ID', { maximumFractionDigits: 2 });
          $('detail-compare-2024-badge').className = 'badge ' + (
            (item.status_keketatan_2024 || '').includes('Longgar') ? 'badge-loose'
              : (item.status_keketatan_2024 || '').includes('Ketat') ? 'badge-tight'
              : item.status_keketatan_2024 === 'Tanpa Pelamar' ? 'badge-neutral' : 'badge-mod'
          );
          $('detail-compare-2024-badge').textContent = item.status_keketatan_2024 || '—';
          $('detail-compare-2024-text').textContent =
            'Di CPNS 2024 (' + (item.match_label_2024 || 'Posisi sejenis') + '): ada ' +
            formatInt(item.kursi_2024) + ' kursi dan ' + formatInt(item.pelamar_2024) +
            ' pelamar, dengan keketatan ' + (item.status_keketatan_2024 || '—') +
            ' (rasio ' + formatRasio2024(item) + ', peluang ' + peluangStr + '%).';
        } else {
          $('detail-compare-2024-badge').className = 'badge badge-neutral';
          $('detail-compare-2024-badge').textContent = 'Tidak ada di 2024';
          $('detail-compare-2024-text').textContent =
            'Tidak ada pembanding di 2024 — tidak ditemukan formasi atau jabatan yang sama pada instansi ini di database SSCASN CPNS 2024.';
        }
      }

      const has2024Scores =
        item.nilai_akhir_2024_median !== null && item.nilai_akhir_2024_median !== undefined;
      if (scoresGrid) {
        if (has2024Scores) {
          scoresGrid.classList.remove('hidden');
          $('detail-score-2024-na').textContent = 'Median ' + fmtNum(item.nilai_akhir_2024_median, 3);
          $('detail-score-2024-na-sub').textContent =
            'Min ' + fmtNum(item.nilai_akhir_2024_min, 3) + ' · Maks ' + fmtNum(item.nilai_akhir_2024_max, 3);
          $('detail-score-2024-skd').textContent = 'Median ' + fmtNum(item.skd_2024_lulus_median, 1);
          $('detail-score-2024-skd-sub').textContent =
            'Min ' + formatInt(item.skd_2024_lulus_min) + ' · Maks ' + formatInt(item.skd_2024_lulus_max);
          $('detail-score-2024-skb-floor').textContent =
            item.skd_2024_skb_min !== null && item.skd_2024_skb_min !== undefined
              ? 'SKD ≥ ' + formatInt(item.skd_2024_skb_min)
              : '—';
          $('detail-score-2024-skb-floor-sub').textContent =
            item.n_peserta_skb_2024 !== null && item.n_peserta_skb_2024 !== undefined
              ? formatInt(item.n_peserta_skb_2024) + ' peserta ikut SKB'
              : '—';
          $('detail-score-2024-skb').textContent = 'Median ' + fmtNum(item.skb_2024_lulus_median, 2);
          $('detail-score-2024-skb-sub').textContent =
            'Min ' + fmtNum(item.skb_2024_lulus_min, 2) + ' · ' + formatInt(item.n_lulus_2024) + ' lulus P/L';
        } else {
          scoresGrid.classList.add('hidden');
        }
      }

      if ($('detail-compare-2024-nilai-note')) {
        if (has2024Scores) {
          $('detail-compare-2024-nilai-note').textContent =
            'Sumber nilai resmi 2024: ' + (item.sumber_nilai_2024 || 'Hasil Integrasi SKD–SKB BKN') + '. ' + skd2026Note;
        } else if (item.kursi_2024 !== null && item.kursi_2024 !== undefined && item.sumber_nilai_2024) {
          $('detail-compare-2024-nilai-note').textContent =
            'Pada formasi pembanding 2024 ini tidak terdapat peserta lulus akhir (P/L) pada lampiran hasil integrasi (' +
            item.sumber_nilai_2024 + '). ' + skd2026Note;
        } else {
          $('detail-compare-2024-nilai-note').textContent = skd2026Note;
        }
      }

      $('detail-eselon1').textContent = item.unit_eselon1;
      $('detail-jenis').textContent = item.jenis_formasi || '— (Tidak dirinci pada dokumen)';
      $('detail-lokasi').textContent = item.lokasi_nm;
      $('detail-jenjang').textContent = item.jenjang;
      $('thp-golongan-pill').textContent = 'Gol. ' + item.golongan_kode + ' (Acuan PP 5/2024)';
      if ($('sim-tukin-source-note')) {
        $('sim-tukin-source-note').textContent = item.tukin_sumber || 'Perpres Tukin Instansi';
      }
      if ($('slip-tukin-label')) {
        $('slip-tukin-label').textContent = 'Tukin ' + (item.instansi_nm || 'Instansi') + ' (Acuan)';
      }

      const cloud = $('detail-majors-cloud');
      cloud.innerHTML = (item.jurusan_list || [])
        .map(
          (m) =>
            '<button type="button" class="major-filter-btn" data-pick-jurusan="' +
            escapeHtml(m) +
            '">' +
            escapeHtml(m) +
            '</button>'
        )
        .join('');

      renderRequirementsPanel(item);
      updateDetailBookmarkBtn();
      recalculateSimulation();
      if ($('btn-close-detail')) $('btn-close-detail').focus();
    } catch (e) {
      if (state.detailAbortController !== controller) return;
      if (controller.signal.aborted && !didTimeout) return;
      showToast(
        didTimeout
          ? 'Server terlalu lama merespons (timeout). Silakan coba klik ulang.'
          : 'Gagal memuat detail formasi.',
        'warn'
      );
      closeModal('modal-detail');
    } finally {
      if (slowTimer) clearTimeout(slowTimer);
      if (timeoutTimer) clearTimeout(timeoutTimer);
      if (state.detailAbortController === controller) {
        loading.classList.add('hidden');
      }
    }
  }

  async function openCompareModal() {
    const backdrop = $('modal-compare');
    const body = $('compare-body');
    if (backdrop.classList.contains('hidden')) {
      state.lastFocusedEl = document.activeElement;
    }
    backdrop.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');

    if (state.compareAbortController) {
      state.compareAbortController.abort();
      state.compareAbortController = null;
    }

    if (!state.bookmarks.length) {
      body.innerHTML =
        '<div class="empty-state" style="padding:28px;"><p class="empty-desc">Belum ada formasi yang disimpan. Klik ikon ★ di daftar tabel untuk menyimpan hingga 4 formasi.</p></div>';
      if ($('btn-close-compare')) $('btn-close-compare').focus();
      return;
    }

    const controller = new AbortController();
    state.compareAbortController = controller;
    body.innerHTML = '<div style="padding:24px;text-align:center;">Memuat perbandingan...</div>';
    try {
      const items = await apiGet('/formasi-batch', { ids: state.bookmarks.join(',') }, { signal: controller.signal });
      if (state.compareAbortController !== controller) return;
      pruneOrphanedBookmarks(items);
      if (!items.length) {
        body.innerHTML = '<div class="empty-state"><p class="empty-desc">Formasi tersimpan tidak ditemukan.</p></div>';
        return;
      }
      const cols = items
        .map(
          (it) =>
            '<th><div style="font-size:0.75rem;color:var(--color-accent-ink);font-weight:600;">' +
            escapeHtml(it.instansi_nm) +
            '</div><div style="font-weight:700;margin-top:2px;">#' +
            escapeHtml(it.no_urut) +
            ' ' +
            escapeHtml(it.jabatan_nm) +
            '</div><div style="font-size:0.75rem;color:var(--color-text-muted);font-weight:500;">' +
            escapeHtml(it.unit_eselon1) +
            '</div></th>'
        )
        .join('');

      function rowHtml(lbl, fn) {
        return (
          '<tr><th class="compare-row-label">' +
          escapeHtml(lbl) +
          '</th>' +
          items.map((it) => '<td>' + fn(it) + '</td>').join('') +
          '</tr>'
        );
      }

      body.innerHTML =
        '<div class="compare-scroll"><table class="compare-table"><thead><tr><th class="compare-row-label">Atribut</th>' +
        cols +
        '</tr></thead><tbody>' +
        rowHtml('Unit Penempatan', (it) => escapeHtml(it.lokasi_nm)) +
        rowHtml('Jenjang', (it) => '<span class="badge badge-accent">' + escapeHtml(it.jenjang) + '</span>') +
        rowHtml('Kualifikasi Pendidikan', (it) => escapeHtml(it.pendidikan_nm)) +
        rowHtml('Alokasi CPNS', (it) => '<strong class="num">' + formatQuota(it.jumlah_formasi) + '</strong>') +
        rowHtml('Jalur Formasi', (it) => (it.jenis_formasi ? escapeHtml(it.jenis_formasi) : '<span class="muted-note">— (Belum rilis)</span>')) +
        rowHtml('Jumlah Pelamar', (it) => (it.jumlah_pelamar !== null ? formatInt(it.jumlah_pelamar) : '<span class="muted-note">— (Belum rilis)</span>')) +
        rowHtml('Gaji Resmi', (it) => (it.gaji_min > 0 ? '<span class="num">' + formatSalaryRange(it.gaji_min, it.gaji_max) + '</span>' : '<span class="muted-note">— (Belum rilis)</span>')) +
        rowHtml('Pembanding CPNS 2024', (it) => (
          it.kursi_2024 !== null && it.kursi_2024 !== undefined
            ? '<span class="num">' + formatInt(it.kursi_2024) + ' kursi • ' + formatInt(it.pelamar_2024) + ' pelamar</span> (' + escapeHtml(it.status_keketatan_2024 || '') + ', ' + escapeHtml(formatRasio2024(it)) + ')'
            : '<span class="muted-note">Tidak ada pembanding di 2024</span>'
        )) +
        rowHtml('Simulasi Gapok CPNS 80%', (it) => '<span class="num">' + formatRp(it.gapok_cpns_80) + ' (Gol. ' + escapeHtml(it.golongan_kode) + ')</span>') +
        rowHtml('Tukin Instansi (Regulasi)', (it) => (it.tukin_min && it.tukin_max ? '<span class="num">' + formatRp(it.tukin_min) + ' – ' + formatRp(it.tukin_max) + '</span>' : '<span class="muted-note">—</span>')) +
        '</tbody></table></div>';
      if ($('btn-close-compare')) $('btn-close-compare').focus();
    } catch (e) {
      if (state.compareAbortController !== controller || (e && e.name === 'AbortError')) return;
      body.innerHTML = '<div class="empty-state"><p class="empty-desc">Gagal memuat data perbandingan.</p></div>';
    }
  }

  function closeModal(id) {
    if (id === 'modal-detail' && state.detailAbortController) {
      state.detailAbortController.abort();
      state.detailAbortController = null;
    }
    if (id === 'modal-compare' && state.compareAbortController) {
      state.compareAbortController.abort();
      state.compareAbortController = null;
    }
    const el = $(id);
    if (!el) return;
    const wasVisible = !el.classList.contains('hidden');
    el.classList.add('hidden');
    if (id === 'modal-detail' && $('modal-detail-loading')) {
      $('modal-detail-loading').classList.add('hidden');
    }
    if ($('modal-detail').classList.contains('hidden') && $('modal-compare').classList.contains('hidden')) {
      document.body.classList.remove('overflow-hidden');
      if (wasVisible && state.lastFocusedEl && typeof state.lastFocusedEl.focus === 'function') {
        try { state.lastFocusedEl.focus(); } catch (e) {}
        state.lastFocusedEl = null;
      }
    }
  }

  function resetAllFilters(skipLoad) {
    cancelFilterTimers();
    if ($('jurusan-popover')) $('jurusan-popover').classList.add('hidden');
    state.page = 1;
    state.only_saved = false;
    state.q = '';
    state.instansi = '';
    state.jurusan = '';
    state.eselon1 = '';
    state.jabatan = '';
    state.lokasi = '';
    state.jenjang = '';
    state.jenis_formasi = '';
    state.min_kuota = '';
    state.keketatan_2024 = '';
    state.sort_by = 'no_urut';

    $('filter-q').value = '';
    if ($('filter-instansi')) $('filter-instansi').value = '';
    $('filter-jurusan').value = '';
    $('filter-eselon1').value = '';
    $('filter-jabatan').value = '';
    $('filter-lokasi').value = '';
    $('filter-jenjang').value = '';
    if ($('filter-jenis-formasi')) $('filter-jenis-formasi').value = '';
    $('filter-min-kuota').value = '';
    if ($('filter-keketatan-2024')) $('filter-keketatan-2024').value = '';
    $('filter-sort').value = 'no_urut';
    if (!skipLoad) {
      loadFormasiTable();
    }
  }

  function updateThemeUi(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
    const lbl = $('theme-label-text');
    const btn = $('btn-theme-toggle');
    if (lbl) lbl.textContent = theme === 'dark' ? 'Terang' : 'Gelap';
    if (btn) btn.setAttribute('aria-label', theme === 'dark' ? 'Ganti ke mode terang' : 'Ganti ke mode gelap');
  }

  function bindEvents() {
    updateThemeUi(document.documentElement.getAttribute('data-theme') || 'dark');

    $('btn-theme-toggle').addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = cur === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch (e) {}
      updateThemeUi(next);
    });

    $('btn-toggle-mobile-filters').addEventListener('click', () => {
      const panel = $('workbench-panel');
      const expanded = panel.classList.toggle('is-expanded-mobile');
      $('btn-toggle-mobile-filters').setAttribute('aria-expanded', String(expanded));
      $('mobile-filter-toggle-label').textContent = expanded ? 'Tutup Filter' : 'Filter Lengkap';
    });

    $('btn-toggle-analytics').addEventListener('click', () => {
      state.analyticsOpen = !state.analyticsOpen;
      $('analytics-drawer').classList.toggle('hidden', !state.analyticsOpen);
      $('btn-toggle-analytics').setAttribute('aria-expanded', String(state.analyticsOpen));
      if (state.analyticsOpen) loadAnalytics();
    });

    $('btn-reset-filters').addEventListener('click', () => resetAllFilters(false));
    $('btn-empty-reset').addEventListener('click', () => resetAllFilters(false));

    $('btn-export-csv').addEventListener('click', () => {
      if (state.only_saved && !state.bookmarks.length) {
        showToast('Tidak ada formasi tersimpan untuk diekspor.', 'warn');
        return;
      }
      const url = new URL(API_BASE + '/export', window.location.origin);
      if (state.only_saved && state.bookmarks.length) {
        url.searchParams.set('ids', state.bookmarks.join(','));
      } else {
        Object.entries(buildActiveQueryParams()).forEach(([k, v]) => {
          if (v !== undefined && v !== null && String(v).trim() !== '') {
            url.searchParams.set(k, String(v));
          }
        });
      }
      window.location.href = url.toString();
    });

    $('filter-q').addEventListener('input', (e) => {
      state.q = e.target.value;
      state.only_saved = false;
      state.page = 1;
      clearTimeout(qTimer);
      qTimer = setTimeout(loadFormasiTable, 260);
    });
    $('btn-clear-q').addEventListener('click', () => {
      clearTimeout(qTimer);
      state.q = '';
      state.page = 1;
      $('filter-q').value = '';
      loadFormasiTable();
    });

    $('filter-lokasi').addEventListener('input', (e) => {
      state.lokasi = e.target.value;
      state.only_saved = false;
      state.page = 1;
      clearTimeout(lokTimer);
      lokTimer = setTimeout(loadFormasiTable, 260);
    });
    $('btn-clear-lokasi').addEventListener('click', () => {
      clearTimeout(lokTimer);
      state.lokasi = '';
      state.page = 1;
      $('filter-lokasi').value = '';
      loadFormasiTable();
    });

    const jurInput = $('filter-jurusan');
    jurInput.addEventListener('input', (e) => {
      state.jurusan = e.target.value;
      state.only_saved = false;
      state.page = 1;
      handleJurusanInput(e.target.value);
      clearTimeout(jurTableTimer);
      jurTableTimer = setTimeout(loadFormasiTable, 300);
    });
    jurInput.addEventListener('focus', () => handleJurusanInput(jurInput.value));
    $('btn-clear-jurusan').addEventListener('click', () => {
      cancelFilterTimers();
      state.jurusan = '';
      state.page = 1;
      jurInput.value = '';
      $('jurusan-popover').classList.add('hidden');
      loadFormasiTable();
    });

    $('jurusan-popover').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-val]');
      if (!btn) return;
      cancelFilterTimers();
      state.jurusan = btn.getAttribute('data-val') || '';
      jurInput.value = state.jurusan;
      state.only_saved = false;
      state.page = 1;
      $('jurusan-popover').classList.add('hidden');
      loadFormasiTable();
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#filter-jurusan') && !e.target.closest('#jurusan-popover')) {
        $('jurusan-popover').classList.add('hidden');
      }
    });

    if ($('filter-instansi')) {
      $('filter-instansi').addEventListener('change', (e) => {
        state.instansi = e.target.value;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
      });
    }
    $('filter-eselon1').addEventListener('change', (e) => {
      state.eselon1 = e.target.value;
      state.only_saved = false;
      state.page = 1;
      loadFormasiTable();
    });
    $('filter-jabatan').addEventListener('change', (e) => {
      state.jabatan = e.target.value;
      state.only_saved = false;
      state.page = 1;
      loadFormasiTable();
    });
    $('filter-jenjang').addEventListener('change', (e) => {
      state.jenjang = e.target.value;
      state.only_saved = false;
      state.page = 1;
      loadFormasiTable();
    });
    if ($('filter-jenis-formasi')) {
      $('filter-jenis-formasi').addEventListener('change', (e) => {
        state.jenis_formasi = e.target.value;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
      });
    }
    $('filter-min-kuota').addEventListener('change', (e) => {
      state.min_kuota = e.target.value;
      state.only_saved = false;
      state.page = 1;
      loadFormasiTable();
    });
    if ($('filter-keketatan-2024')) {
      $('filter-keketatan-2024').addEventListener('change', (e) => {
        state.keketatan_2024 = e.target.value;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
      });
    }
    $('filter-sort').addEventListener('change', (e) => {
      state.sort_by = e.target.value;
      state.page = 1;
      loadFormasiTable();
    });

    document.querySelector('.quick-presets-cluster').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-preset]');
      if (!btn) return;
      const p = btn.getAttribute('data-preset');
      if (p === 'saved') {
        state.only_saved = !state.only_saved;
        state.page = 1;
        loadFormasiTable();
        return;
      }
      resetAllFilters(true);
      if (p === 'sma') {
        state.jenjang = 'SMA/SMK';
        $('filter-jenjang').value = 'SMA/SMK';
      } else if (p === 's1') {
        state.jenjang = 'D-IV/S-1';
        $('filter-jenjang').value = 'D-IV/S-1';
      } else if (p === 'd3') {
        state.jenjang = 'D-III';
        $('filter-jenjang').value = 'D-III';
      } else if (p === 'big_kuota') {
        state.min_kuota = '10';
        $('filter-min-kuota').value = '10';
      }
      loadFormasiTable();
    });

    $('active-chips-list').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-clear-key]');
      if (!btn) return;
      cancelFilterTimers();
      const key = btn.getAttribute('data-clear-key');
      if (key === 'saved') state.only_saved = false;
      else if (key === 'q') { state.q = ''; $('filter-q').value = ''; }
      else if (key === 'instansi') { state.instansi = ''; if ($('filter-instansi')) $('filter-instansi').value = ''; }
      else if (key === 'jurusan') { state.jurusan = ''; $('filter-jurusan').value = ''; }
      else if (key === 'eselon1') { state.eselon1 = ''; $('filter-eselon1').value = ''; }
      else if (key === 'jabatan') { state.jabatan = ''; $('filter-jabatan').value = ''; }
      else if (key === 'lokasi') { state.lokasi = ''; $('filter-lokasi').value = ''; }
      else if (key === 'jenjang') { state.jenjang = ''; $('filter-jenjang').value = ''; }
      else if (key === 'jenis_formasi') { state.jenis_formasi = ''; if ($('filter-jenis-formasi')) $('filter-jenis-formasi').value = ''; }
      else if (key === 'min_kuota') { state.min_kuota = ''; $('filter-min-kuota').value = ''; }
      else if (key === 'keketatan_2024') { state.keketatan_2024 = ''; if ($('filter-keketatan-2024')) $('filter-keketatan-2024').value = ''; }
      state.page = 1;
      loadFormasiTable();
    });

    $('analytics-drawer').addEventListener('click', (e) => {
      const jBtn = e.target.closest('[data-chart-jurusan]');
      if (jBtn) {
        const val = jBtn.getAttribute('data-chart-jurusan');
        state.jurusan = state.jurusan === val ? '' : val;
        $('filter-jurusan').value = state.jurusan;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
        return;
      }
      const eBtn = e.target.closest('[data-chart-eselon1]');
      if (eBtn) {
        const val = eBtn.getAttribute('data-chart-eselon1');
        state.eselon1 = state.eselon1 === val ? '' : val;
        $('filter-eselon1').value = state.eselon1;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
        return;
      }
      const jabBtn = e.target.closest('[data-chart-jabatan]');
      if (jabBtn) {
        const val = jabBtn.getAttribute('data-chart-jabatan');
        state.jabatan = state.jabatan === val ? '' : val;
        $('filter-jabatan').value = state.jabatan;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
        return;
      }
      const jenjBtn = e.target.closest('[data-chart-jenjang]');
      if (jenjBtn) {
        const val = jenjBtn.getAttribute('data-chart-jenjang');
        state.jenjang = state.jenjang === val ? '' : val;
        $('filter-jenjang').value = state.jenjang;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
        return;
      }
      const k24Btn = e.target.closest('[data-chart-keketatan24]');
      if (k24Btn) {
        const val = k24Btn.getAttribute('data-chart-keketatan24');
        state.keketatan_2024 = state.keketatan_2024 === val ? '' : val;
        if ($('filter-keketatan-2024')) $('filter-keketatan-2024').value = state.keketatan_2024;
        state.only_saved = false;
        state.page = 1;
        loadFormasiTable();
      }
    });

    $('btn-view-table').addEventListener('click', () => { state.viewMode = 'table'; renderCurrentView(); });
    $('btn-view-cards').addEventListener('click', () => { state.viewMode = 'cards'; renderCurrentView(); });
    $('page-size-select').addEventListener('change', (e) => {
      state.limit = Number(e.target.value) || 20;
      state.page = 1;
      loadFormasiTable();
    });

    $('pagination-controls').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-page]');
      if (!btn || btn.disabled) return;
      state.page = Number(btn.getAttribute('data-page')) || 1;
      loadFormasiTable();
      $('section-table').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    $('section-table').addEventListener('click', (e) => {
      const bm = e.target.closest('[data-toggle-bookmark]');
      if (bm) {
        toggleBookmark(bm.getAttribute('data-toggle-bookmark'));
        return;
      }
      const det = e.target.closest('[data-open-detail]');
      if (det) {
        openDetailModal(det.getAttribute('data-open-detail'));
      }
    });

    $('btn-close-detail').addEventListener('click', () => closeModal('modal-detail'));
    $('btn-detail-close-footer').addEventListener('click', () => closeModal('modal-detail'));

    if ($('detail-req-checklist-body')) {
      $('detail-req-checklist-body').addEventListener('change', (e) => {
        const cb = e.target.closest('input[type="checkbox"][data-check-key]');
        if (!cb || !state.activeDetail) return;
        const key = cb.getAttribute('data-check-key');
        setFormasiChecklistItem(state.activeDetail.formasi_id, key, cb.checked);
        const label = cb.closest('.req-check-item');
        if (label) label.classList.toggle('is-checked', cb.checked);
        updateChecklistProgress(state.activeDetail.formasi_id);
      });
    }

    if ($('btn-reset-checklist')) {
      $('btn-reset-checklist').addEventListener('click', () => {
        if (!state.activeDetail) return;
        clearFormasiChecklist(state.activeDetail.formasi_id);
        const body = $('detail-req-checklist-body');
        if (body) {
          body.querySelectorAll('input[type="checkbox"][data-check-key]').forEach((cb) => {
            cb.checked = false;
            const lbl = cb.closest('.req-check-item');
            if (lbl) lbl.classList.remove('is-checked');
          });
        }
        updateChecklistProgress(state.activeDetail.formasi_id);
        showToast('Checklist berkas untuk formasi ini direset.', 'warn');
      });
    }
    $('btn-detail-bookmark').addEventListener('click', () => {
      if (state.activeDetail) toggleBookmark(state.activeDetail.formasi_id);
    });
    $('detail-majors-cloud').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-pick-jurusan]');
      if (!btn) return;
      state.jurusan = btn.getAttribute('data-pick-jurusan') || '';
      $('filter-jurusan').value = state.jurusan;
      state.only_saved = false;
      state.page = 1;
      closeModal('modal-detail');
      loadFormasiTable();
    });

    $('sim-tukin-pct').addEventListener('input', recalculateSimulation);
    $('sim-status').addEventListener('change', recalculateSimulation);
    $('sim-keluarga').addEventListener('change', recalculateSimulation);

    $('btn-open-compare').addEventListener('click', openCompareModal);
    $('btn-close-compare').addEventListener('click', () => closeModal('modal-compare'));
    $('btn-compare-close-footer').addEventListener('click', () => closeModal('modal-compare'));
    $('btn-clear-bookmarks').addEventListener('click', () => {
      state.bookmarks = [];
      saveBookmarks();
      openCompareModal();
      if (state.only_saved) loadFormasiTable();
      else renderCurrentView();
    });

    [$('modal-detail'), $('modal-compare')].forEach((backdrop) => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal(backdrop.id);
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if ($('jurusan-popover') && !$('jurusan-popover').classList.contains('hidden')) {
          cancelFilterTimers();
          $('jurusan-popover').classList.add('hidden');
        }
        closeModal('modal-detail');
        closeModal('modal-compare');
        return;
      }
      if (e.key === 'Tab') {
        const openModal = !$('modal-detail').classList.contains('hidden')
          ? $('modal-detail')
          : !$('modal-compare').classList.contains('hidden')
          ? $('modal-compare')
          : null;
        if (openModal) {
          const focusables = Array.from(
            openModal.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [tabindex]:not([tabindex="-1"])')
          ).filter((el) => el.offsetParent !== null);
          if (focusables.length) {
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }
      }
    });

    $('btn-copy-nmid').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText('ID1025421073475');
        showToast('NMID QRIS berhasil disalin.', 'success');
      } catch (e) {
        showToast('Salin manual NMID: ID1025421073475', 'warn');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadBookmarks();
    bindEvents();
    loadStats();
    loadFilters();
    loadFormasiTable();
  });
})();
