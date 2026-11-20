/* 이중재의 투자노트 — 해시 라우팅 단일 페이지. data/*.json 을 읽어 그린다. */
(function () {
  const app = document.getElementById('app');
  const cache = {};
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (v, d = 2) => v == null || isNaN(v) ? '—' : Number(v).toLocaleString('ko-KR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const cls = v => v == null ? 'fl' : v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
  const arrow = v => v == null ? '' : v > 0 ? '▲' : v < 0 ? '▼' : '';
  const pct = v => v == null ? '<span class="fl">—</span>' : `<span class="${cls(v)}">${arrow(v)}${v > 0 ? '+' : ''}${fmt(v)}%</span>`;
  const eok = v => {
    if (v == null) return '—';
    const e = v / 1e8;
    return Math.abs(e) >= 10000 ? `${fmt(e / 10000, 2)}조` : `${fmt(e, 0)}억`;
  };
  const ymd = s => s && s.length === 8 ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6)}` : (s || '');

  async function data(name) {
    if (cache[name]) return cache[name];
    try {
      const r = await fetch(`data/${name}.json?v=${Date.now()}`);
      if (!r.ok) throw new Error(r.status);
      return (cache[name] = await r.json());
    } catch (e) { return (cache[name] = null); }
  }

  function spark(arr, w = 200, h = 34) {
    if (!arr || arr.length < 2) return '';
    const mn = Math.min(...arr), mx = Math.max(...arr), rg = mx - mn || 1;
    const pts = arr.map((v, i) => `${(i / (arr.length - 1) * w).toFixed(1)},${(h - 3 - (v - mn) / rg * (h - 6)).toFixed(1)}`).join(' ');
    const col = arr[arr.length - 1] >= arr[0] ? 'var(--up)' : 'var(--dn)';
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><polyline fill="none" stroke="${col}" stroke-width="1.6" points="${pts}"/></svg>`;
  }

  function tile(q, digits = 2) {
    if (!q || q.error) return `<div class="card tile"><div class="lb">${esc(q?.name)}</div><div class="v fl">—</div><div class="c fl">수집 실패</div></div>`;
    return `<div class="card tile"><div class="lb">${esc(q.name)} <span class="badge">${esc(q.date || '')}</span></div>
      <div class="v">${fmt(q.close, digits)}</div>
      <div class="c ${cls(q.pct)}">${arrow(q.pct)}${fmt(Math.abs(q.chg ?? 0), digits)} (${q.pct > 0 ? '+' : ''}${fmt(q.pct)}%)${q.wk != null ? ` <span class="fl">· 1주 ${q.wk > 0 ? '+' : ''}${fmt(q.wk)}%</span>` : ''}</div>
      ${spark(q.spark)}</div>`;
  }

  function quoteTable(list, digits = 2) {
    if (!Array.isArray(list) || !list.length) return '<div class="empty">데이터 없음</div>';
    return `<div class="scroll"><table class="tbl"><thead><tr><th>항목</th><th class="n">종가</th><th class="n">등락률</th><th class="n">1주</th><th>기준일</th></tr></thead><tbody>${list.map(q => q.error ? `<tr><td>${esc(q.name)}</td><td class="n" colspan="4">수집 실패</td></tr>` : `<tr><td>${esc(q.name)}</td><td class="n">${fmt(q.close, digits)}</td><td class="n">${pct(q.pct)}</td><td class="n">${pct(q.wk)}</td><td>${esc(q.date)}</td></tr>`).join('')}</tbody></table></div>`;
  }

  function flowChart(it) {
    if (!it || it.error || !it.closes?.length) return `<div class="empty">${esc(it?.name || '')} 분봉 데이터가 아직 없습니다</div>`;
    const W = 520, H = 120, P = 26, a = it.closes, mn = Math.min(...a, it.low), mx = Math.max(...a, it.high), rg = mx - mn || 1;
    const x = i => P + i / (a.length - 1) * (W - P - 6), y = v => 8 + (mx - v) / rg * (H - 26);
    const pts = a.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const col = it.close >= it.open ? 'var(--up)' : 'var(--dn)';
    const ticks = [0, Math.floor(a.length / 2), a.length - 1];
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(it.name)} 5분봉 흐름">
      <line x1="${P}" x2="${W - 6}" y1="${y(it.open)}" y2="${y(it.open)}" stroke="var(--muted)" stroke-dasharray="3 3" stroke-width="1"/>
      <text class="axis" x="2" y="${y(it.open) + 3}">시가</text>
      <polyline fill="none" stroke="${col}" stroke-width="1.8" points="${pts}"/>
      ${ticks.map(i => `<text class="axis" x="${x(i) - 12}" y="${H - 4}">${esc(it.times[i])}</text>`).join('')}
    </svg>`;
  }

  const views = {};

  views.home = async () => {
    const [m, e, mv, b] = await Promise.all([data('market'), data('earnings'), data('movers'), data('briefs')]);
    const kr = m?.kr || [], us = m?.us || [];
    const surge = (e?.reports || []).filter(r => r.surge).slice(0, 6);
    const ups = (mv?.up || []).slice(0, 6);
    const brief = b?.items?.[0];
    const flows = (m?.intraday || []).filter(x => !x.error);
    return `<div class="page-head"><h1>오늘의 시장 노트</h1><span class="stamp">시세 갱신 ${esc(m?.updated || '—')} · 공시 갱신 ${esc(e?.updated || '—')}</span></div>
    ${m?.note ? `<p class="note" style="margin:-8px 0 12px">${esc(m.note)}</p>` : ''}
    <div class="grid g4">${[...kr, ...us.slice(0, 2)].map(q => tile(q)).join('')}</div>
    <div class="grid g2" style="margin-top:14px">
      <section class="card"><h2>장중 흐름 판정</h2>${flows.length ? `<table class="tbl"><tbody>${flows.map(f => `<tr><td>${esc(f.name)}</td><td class="verdict ${f.verdict.includes('강') && !f.verdict.includes('후약') ? 'up' : f.verdict.includes('후약') || f.verdict.includes('약세') ? 'dn' : ''}">${esc(f.verdict)}</td><td class="n">종가 위치 ${f.pos ?? '—'}%</td></tr>`).join('')}</tbody></table><p class="note"><a href="#flow">5분봉 차트 보기</a></p>` : '<div class="empty">첫 자동 갱신 후 표시됩니다</div>'}</section>
      <section class="card"><h2>오늘의 아침 브리핑</h2>${brief ? `<p><a href="${esc(brief.file)}" target="_blank" rel="noopener">${esc(brief.title)}</a> <span class="badge">PDF</span></p><p class="note">국내·미국·글로벌·교양을 한 문서로. <a href="#briefs">지난 브리핑</a></p>` : '<div class="empty">브리핑 PDF가 아직 없습니다</div>'}</section>
      <section class="card"><h2>실적 급증 종목 <span class="badge">DART</span></h2>${surge.length ? `<table class="tbl"><tbody>${surge.map(r => `<tr><td>${r.file ? `<a href="${esc(r.file)}">${esc(r.corp_name)}</a>` : esc(r.corp_name)}<br><span class="note">${esc(r.period)}</span></td><td>${r.flags.map(f => `<span class="chip ${f.includes('적자') ? 'cold' : 'hot'}">${esc(f)}</span>`).join('')}</td><td class="n">${eok(r.op)}</td></tr>`).join('')}</tbody></table><p class="note"><a href="#earnings">전체 실적 공시 보기</a></p>` : '<div class="empty">조건에 맞는 종목이 아직 없습니다</div>'}</section>
      <section class="card"><h2>전일 강세종목</h2>${ups.length ? `<table class="tbl"><tbody>${ups.map(s => `<tr><td>${esc(s.name)} <span class="badge">${s.market === 'KOSPI' ? '코스피' : '코스닥'}</span></td><td class="n">${fmt(s.close, 0)}</td><td class="n">${pct(s.pct)}</td></tr>`).join('')}</tbody></table><p class="note">${esc(mv?.filter || '')} · <a href="#movers">더 보기</a></p>` : '<div class="empty">첫 자동 갱신 후 표시됩니다</div>'}</section>
    </div>`;
  };

  views.briefs = async () => {
    const b = await data('briefs');
    const items = b?.items || [];
    return `<div class="page-head"><h1>아침 통합 브리핑</h1><span class="stamp">${items.length}건</span></div>
    <section class="card">${items.length ? `<table class="tbl"><thead><tr><th>날짜</th><th>문서</th></tr></thead><tbody>${items.map(i => `<tr><td class="n" style="text-align:left">${esc(i.date)}</td><td><a href="${esc(i.file)}" target="_blank" rel="noopener">${esc(i.title)}</a></td></tr>`).join('')}</tbody></table>` : '<div class="empty">briefs 폴더에 PDF를 올리면 여기 자동으로 표시됩니다</div>'}
    <p class="note">GitHub 저장소의 briefs 폴더에 PDF를 올리면 다음 갱신 때 목록에 추가됩니다.</p></section>`;
  };

  views.earnings = async () => {
    const e = await data('earnings');
    if (!e) return '<div class="empty">실적 데이터가 아직 없습니다</div>';
    const tab = sessionTab('earn', 'surge');
    const reps = e.reports || [], feed = e.feed || [];
    let body = '';
    if (tab === 'surge' || tab === 'all') {
      const list = tab === 'surge' ? reps.filter(r => r.surge) : reps;
      body = list.length ? `<div class="scroll"><table class="tbl"><thead><tr><th>종목</th><th>기간</th><th class="n">영업이익</th><th class="n">직전 분기</th><th class="n">전년 동기</th><th>신호</th><th>접수</th></tr></thead><tbody>${list.map(r => `<tr><td>${r.file ? `<a href="${esc(r.file)}">${esc(r.corp_name)}</a>` : esc(r.corp_name)} <span class="badge">${r.corp_cls === 'Y' ? '코스피' : '코스닥'}</span></td><td>${esc(r.period)}</td><td class="n">${eok(r.op)}</td><td class="n">${eok(r.op_prev)}</td><td class="n">${eok(r.op_yoy)}</td><td>${(r.flags || []).map(f => `<span class="chip ${f.includes('적자') ? 'cold' : 'hot'}">${esc(f)}</span>`).join('') || '<span class="chip muted">—</span>'}</td><td>${ymd(r.rcept_dt)}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">해당 종목이 없습니다</div>';
    } else {
      const list = feed.filter(f => tab === 'prelim' ? f.kind === '잠정실적' : f.kind !== '잠정실적');
      body = list.length ? `<div class="scroll"><table class="tbl"><thead><tr><th>접수</th><th>회사</th><th>공시</th></tr></thead><tbody>${list.slice(0, 200).map(f => `<tr><td>${ymd(f.rcept_dt)}</td><td>${esc(f.corp_name)} <span class="badge">${f.corp_cls === 'Y' ? '코스피' : '코스닥'}</span></td><td><a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${esc(f.rcept_no)}" target="_blank" rel="noopener">${esc(f.report_nm)}</a></td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">공시가 없습니다</div>';
    }
    const btn = (k, l, n) => `<button type="button" data-tab="earn:${k}" aria-pressed="${tab === k}">${l} <span class="fl">${n}</span></button>`;
    return `<div class="page-head"><h1>실적발표 종목</h1><span class="stamp">DART 갱신 ${esc(e.updated || '—')} · ${esc(e.status || '')}</span></div>
    <section class="card"><div class="tabs">${btn('surge', '실적 급증', reps.filter(r => r.surge).length)}${btn('all', '정기보고서 전체', reps.length)}${btn('prelim', '잠정실적 공시', feed.filter(f => f.kind === '잠정실적').length)}${btn('feed', '보고서 접수 목록', feed.filter(f => f.kind !== '잠정실적').length)}</div>
    ${body}
    <p class="note">급증 기준: ${esc(e.criteria || '')}. 급증 종목은 회사명을 누르면 자동 생성 리포트가 열립니다. 영업이익은 3개월 기준.</p></section>`;
  };

  views.movers = async () => {
    const mv = await data('movers');
    if (!mv || mv.error) return '<div class="empty">강세종목 데이터가 아직 없습니다 — 첫 자동 갱신 후 표시됩니다</div>';
    const t = (list, title) => `<section class="card"><h2>${title}</h2>${list?.length ? `<div class="scroll"><table class="tbl"><thead><tr><th>종목</th><th class="n">종가</th><th class="n">등락률</th><th class="n">거래대금</th><th class="n">시총</th></tr></thead><tbody>${list.map(s => `<tr><td>${esc(s.name)} <span class="badge">${s.market === 'KOSPI' ? '코스피' : '코스닥'}</span></td><td class="n">${fmt(s.close, 0)}</td><td class="n">${pct(s.pct)}</td><td class="n">${fmt(s.amount_eok, 0)}억</td><td class="n">${fmt(s.marcap_jo, 2)}조</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">데이터 없음</div>'}</section>`;
    const f = mv.flows || {};
    const flowRow = k => f[k] ? `<tr><td>${k === 'KOSPI' ? '코스피' : '코스닥'}</td>${['개인', '외국인', '기관', '기타법인'].map(n => `<td class="n ${cls(f[k][n])}">${f[k][n] > 0 ? '+' : ''}${fmt(f[k][n], 0)}</td>`).join('')}<td>${esc(f[k].date)}</td></tr>` : '';
    const br = mv.breadth || {};
    return `<div class="page-head"><h1>강세종목·수급</h1><span class="stamp">갱신 ${esc(mv.updated || '—')}</span></div>
    <div class="grid g2">
      <section class="card"><h2>투자자별 순매수 (억원)</h2>${f.KOSPI || f.KOSDAQ ? `<div class="scroll"><table class="tbl"><thead><tr><th>시장</th><th class="n">개인</th><th class="n">외국인</th><th class="n">기관</th><th class="n">기타법인</th><th>기준일</th></tr></thead><tbody>${flowRow('KOSPI')}${flowRow('KOSDAQ')}</tbody></table></div>` : '<div class="empty">수급 데이터 없음</div>'}</section>
      <section class="card"><h2>등락 종목 수</h2><dl class="kv"><dt>상승</dt><dd class="up">${fmt(br.up, 0)}</dd><dt>하락</dt><dd class="dn">${fmt(br.down, 0)}</dd><dt>보합</dt><dd>${fmt(br.flat, 0)}</dd></dl><p class="note">강세·약세 종목 필터: ${esc(mv.filter || '')}</p></section>
    </div>
    <div class="grid g2">${t(mv.up, '상승률 상위')}${t(mv.down, '하락률 상위')}</div>
    ${t(mv.amount, '거래대금 상위')}`;
  };

  views.flow = async () => {
    const m = await data('market');
    const list = m?.intraday || [];
    return `<div class="page-head"><h1>장중 흐름 (5분봉)</h1><span class="stamp">갱신 ${esc(m?.updated || '—')}</span></div>
    <div class="grid g2">${list.length ? list.map(it => `<section class="card flow"><h2>${esc(it.name)} ${it.verdict ? `<span class="verdict ${it.verdict.includes('후약') || it.verdict.includes('약세') ? 'dn' : 'up'}">· ${esc(it.verdict)}</span>` : ''}</h2>${flowChart(it)}${it.error ? '' : `<dl class="kv" style="margin-top:8px"><dt>시가·고가·저가·종가</dt><dd>${fmt(it.open)} · ${fmt(it.high)} · ${fmt(it.low)} · ${fmt(it.close)}</dd><dt>종가 위치</dt><dd>하루 범위의 ${it.pos ?? '—'}% 지점</dd><dt>기준일</dt><dd>${esc(it.date)}</dd></dl>`}</section>`).join('') : '<div class="empty">첫 자동 갱신 후 표시됩니다</div>'}</div>
    <p class="note">판정: 시가→장 중간 구간과 장 중간→종가 구간의 방향으로 나눕니다(전강후약 = 앞 상승·뒤 하락). 종가 위치 0%는 최저가 마감, 100%는 최고가 마감.</p>`;
  };

  views.global = async () => {
    const m = await data('market');
    if (!m) return '<div class="empty">시세 데이터가 아직 없습니다</div>';
    return `<div class="page-head"><h1>미국·글로벌</h1><span class="stamp">갱신 ${esc(m.updated || '—')} · ${esc(m.source || '')}</span></div>
    <div class="grid g4">${(m.us || []).slice(0, 4).map(q => tile(q)).join('')}</div>
    <div class="grid g2" style="margin-top:14px">
      <section class="card"><h2>미국 지수·변동성</h2>${quoteTable(m.us)}</section>
      <section class="card"><h2>금리·환율·원자재</h2>${quoteTable(m.macro)}</section>
      <section class="card"><h2>아시아·유럽 지수</h2>${quoteTable(m.global)}</section>
      <section class="card"><h2>미국 주요 종목</h2>${quoteTable(m.us_stocks)}</section>
    </div>`;
  };

  views.memo = async () => {
    const d = await data('memo');
    const items = d?.items || [];
    return `<div class="page-head"><h1>메모</h1></div>${items.length ? items.map(i => `<section class="card"><p class="eyebrow">${esc(i.date)}</p><h2>${esc(i.title)}</h2><p style="white-space:pre-line;margin:0">${esc(i.body)}</p>${(i.tags || []).length ? `<div class="chips">${i.tags.map(t => `<span class="chip">${esc(t)}</span>`).join('')}</div>` : ''}</section>`).join('') : '<div class="empty">data/memo.json 에 메모를 추가하면 여기 표시됩니다</div>'}`;
  };

  views.study = async () => window.StudyView ? window.StudyView() : '<div class="empty">공부 자료를 불러오지 못했습니다</div>';

  function sessionTab(group, def) {
    try { return sessionStorage.getItem('tab:' + group) || def; } catch (e) { return def; }
  }

  async function render() {
    const name = (location.hash || '#home').slice(1).split(/[?&]/)[0] || 'home';
    const view = views[name] ? name : 'home';
    document.querySelectorAll('nav.menu a').forEach(a => { if (a.getAttribute('href') === '#' + view) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    app.innerHTML = await views[view]();
    if (view === 'study' && window.StudyBind) window.StudyBind(app);
  }

  app.addEventListener('click', e => {
    const b = e.target.closest('button[data-tab]');
    if (!b) return;
    const [g, k] = b.dataset.tab.split(':');
    try { sessionStorage.setItem('tab:' + g, k); } catch (err) { }
    render();
  });
  window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
  render();
})();
