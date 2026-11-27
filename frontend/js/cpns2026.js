/**
 * SSCASN CPNS 2026 Explorer — Frontend Controller
 * Strict No-Hallucination UI: renders missing 2026 fields (pelamar, rasio, keketatan,
 * jenis_formasi, gaji_min/max BKN) strictly as '—' / 'Belum tersedia' without fake 0s.
 */
(function () {
  'use strict';

  const API_BASE = '/api/2026';
  const BOOKMARK_STORAGE_KEY = 'cpns2026_bookmarks_v1';
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
    bookmarks: [],
    currentItems: [],
    activeDetail: null,
    toastTimer: null,
  };

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

  async function apiGet(path, params) {
    const url = new URL(API_BASE + path, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && String(v).trim() !== '') {
          url.searchParams.set(k, String(v));
        }
      });
    }
    const res = await fetch(url.toString());
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

  let jurusanTimer = null;
  function handleJurusanInput(val) {
    clearTimeout(jurusanTimer);
    jurusanTimer = setTimeout(async () => {
      const pop = $('jurusan-popover');
      if (!pop) return;
      try {
        const items = await apiGet('/filters/jurusan', { q: val, limit: 25 });
        if (!items.length) {
          pop.innerHTML = '<div class="autocomplete-empty">Program studi tidak ditemukan</div>';
        } else {
          pop.innerHTML = items
            .map(
              (it) =>
                '<button type="button" class="autocomplete-item" data-val="' +
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
    if (state.only_saved) chips.push({ key: 'saved', label: 'Mode: Tersimpan (' + state.bookmarks.length + ')' });
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
    if ($('telemetry-active-instansi')) {
      $('telemetry-active-instansi').textContent = state.instansi || 'Semua Instansi Terverifikasi';
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

  async function loadFormasiTable() {
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
          const items = await apiGet('/formasi-batch', { ids: state.bookmarks.join(',') });
          state.currentItems = items;
          state.total = items.length;
          state.totalKuotaFiltered = items.reduce((acc, it) => acc + (it.jumlah_formasi || 0), 0);
          state.totalPages = 1;
        }
      } else {
        const res = await apiGet('/formasi', {
          ...buildActiveQueryParams(),
          page: state.page,
          limit: state.limit,
        });
        state.currentItems = res.items || [];
        state.total = res.total || 0;
        state.totalKuotaFiltered = res.total_kuota_filtered || 0;
        state.totalPages = res.total_pages || 1;
      }

      $('telemetry-filtered-rows').textContent = formatInt(state.total);
      $('telemetry-filtered-kuota').textContent = formatInt(state.totalKuotaFiltered);
      renderCurrentView();
      renderPagination();
      if (state.analyticsOpen) {
        loadAnalytics();
      }
    } catch (err) {
      showToast('Gagal memuat daftar formasi CPNS 2026.', 'warn');
    } finally {
      if (loader) loader.classList.add('hidden');
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

    if (!state.currentItems.length) {
      emptyEl.classList.remove('hidden');
      tableWrap.classList.add('hidden');
      cardsWrap.classList.add('hidden');
      pagBar.classList.add('hidden');
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
          '" aria-label="Simpan formasi">★</button>' +
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
          '<h3 class="jabatan-title" style="margin-top:6px;">' +
          escapeHtml(item.jabatan_nm) +
          '</h3>' +
          '</div>' +
          '<button type="button" class="bookmark-btn ' +
          (saved ? 'is-saved' : '') +
          '" data-toggle-bookmark="' +
          escapeHtml(item.formasi_id) +
          '" aria-label="Simpan formasi">★</button>' +
          '</div>' +
          '<div class="agency-name" style="margin-top:4px;">' +
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
      '<button type="button" class="page-btn" data-page="' +
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
      '<button type="button" class="page-btn" data-page="' +
      Math.min(state.totalPages, state.page + 1) +
      '"' +
      (state.page >= state.totalPages ? ' disabled' : '') +
      '>›</button>';

    ctrl.innerHTML = html;
  }

  async function loadAnalytics() {
    try {
      const d = await apiGet('/analytics/top', buildActiveQueryParams());
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
      showToast('Gagal memuat analitik CPNS 2026.', 'warn');
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
    backdrop.classList.remove('hidden');
    loading.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');

    try {
      const item = await apiGet('/formasi/' + encodeURIComponent(formasiId));
      state.activeDetail = item;
      $('modal-detail-badge').textContent = item.status_keketatan
        ? item.status_keketatan
        : 'Menunggu rilis pelamar SSCASN';
      $('modal-detail-title').textContent = item.jabatan_nm;
      $('modal-detail-sub').textContent = item.instansi_nm + ' • ' + item.unit_eselon1;

      $('detail-kpi-kuota').textContent = formatQuota(item.jumlah_formasi);
      $('detail-kpi-rasio').textContent =
        item.jumlah_pelamar !== null ? formatInt(item.jumlah_pelamar) + ' (' + item.rasio_kompetisi + ')' : '—';
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

      updateDetailBookmarkBtn();
      recalculateSimulation();
    } catch (e) {
      showToast('Gagal memuat detail formasi.', 'warn');
      closeModal('modal-detail');
    } finally {
      loading.classList.add('hidden');
    }
  }

  async function openCompareModal() {
    const backdrop = $('modal-compare');
    const body = $('compare-body');
    backdrop.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');

    if (!state.bookmarks.length) {
      body.innerHTML =
        '<div class="empty-state" style="padding:28px;"><p class="empty-desc">Belum ada formasi yang disimpan. Klik ikon ★ di daftar tabel untuk menyimpan hingga 4 formasi.</p></div>';
      return;
    }

    body.innerHTML = '<div style="padding:24px;text-align:center;">Memuat perbandingan...</div>';
    try {
      const items = await apiGet('/formasi-batch', { ids: state.bookmarks.join(',') });
      if (!items.length) {
        body.innerHTML = '<div class="empty-state"><p class="empty-desc">Formasi tersimpan tidak ditemukan.</p></div>';
        return;
      }
      const cols = items
        .map(
          (it) =>
            '<th><div style="font-weight:700;">#' +
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
    } catch (e) {
      body.innerHTML = '<div class="empty-state"><p class="empty-desc">Gagal memuat data perbandingan.</p></div>';
    }
  }

  function closeModal(id) {
    const el = $(id);
    if (!el) return;
    el.classList.add('hidden');
    if ($('modal-detail').classList.contains('hidden') && $('modal-compare').classList.contains('hidden')) {
      document.body.classList.remove('overflow-hidden');
    }
  }

  function resetAllFilters() {
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
    loadFormasiTable();
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

    $('btn-reset-filters').addEventListener('click', resetAllFilters);
    $('btn-empty-reset').addEventListener('click', resetAllFilters);

    $('btn-export-csv').addEventListener('click', () => {
      const url = new URL(API_BASE + '/export', window.location.origin);
      Object.entries(buildActiveQueryParams()).forEach(([k, v]) => {
        if (v !== undefined && v !== null && String(v).trim() !== '') {
          url.searchParams.set(k, String(v));
        }
      });
      window.location.href = url.toString();
    });

    let qTimer = null;
    $('filter-q').addEventListener('input', (e) => {
      state.q = e.target.value;
      state.only_saved = false;
      state.page = 1;
      clearTimeout(qTimer);
      qTimer = setTimeout(loadFormasiTable, 260);
    });
    $('btn-clear-q').addEventListener('click', () => {
      state.q = '';
      state.page = 1;
      $('filter-q').value = '';
      loadFormasiTable();
    });

    let lokTimer = null;
    $('filter-lokasi').addEventListener('input', (e) => {
      state.lokasi = e.target.value;
      state.only_saved = false;
      state.page = 1;
      clearTimeout(lokTimer);
      lokTimer = setTimeout(loadFormasiTable, 260);
    });
    $('btn-clear-lokasi').addEventListener('click', () => {
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
      loadFormasiTable();
    });
    jurInput.addEventListener('focus', () => handleJurusanInput(jurInput.value));
    $('btn-clear-jurusan').addEventListener('click', () => {
      state.jurusan = '';
      state.page = 1;
      jurInput.value = '';
      $('jurusan-popover').classList.add('hidden');
      loadFormasiTable();
    });

    $('jurusan-popover').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-val]');
      if (!btn) return;
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
      resetAllFilters();
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
        closeModal('modal-detail');
        closeModal('modal-compare');
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
