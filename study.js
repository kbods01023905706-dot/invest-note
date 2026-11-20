/* 재무제표 공부 — 점검 순서, 용어, 퀴즈, 계산기 */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const STEPS = [
    { t: '1. 사기 전에 위험부터 거른다', d: [
      '감사의견: "적정"이 아니면(한정·부적정·의견거절) 검토 대상에서 제외합니다.',
      '이익의 질: 영업이익은 흑자인데 영업활동현금흐름이 몇 해째 마이너스라면 이익이 현금으로 들어오지 않는 구조입니다.',
      '빚 감당력: 이자보상배율(영업이익 ÷ 이자비용)이 1배를 밑돌면 번 돈으로 이자도 못 내는 상태입니다.',
      '운전자본: 매출채권·재고자산이 매출보다 훨씬 빠르게 늘면 밀어내기·회수 지연을 의심합니다.',
      '희석: 전환사채(CB)·신주인수권부사채(BW)·유상증자가 반복되면 주주가치가 계속 나뉩니다. 이 사이트의 실적 리포트는 최근 1년 건수를 자동으로 셉니다.'] },
    { t: '2. 테마는 숫자로 확인한다', d: [
      '사업보고서 "II. 사업의 내용"에서 해당 사업의 매출 비중, 주요 고객, 수주잔고를 찾습니다.',
      '뉴스에 나온 신사업이 매출의 한 자릿수 초반이라면 실적보다 기대가 주가를 움직이는 단계로 봅니다.'] },
    { t: '3. 업종에 맞는 잣대로 가격을 본다', d: [
      'PBR = ROE × PER. ROE가 높을수록 높은 PBR이 정당화됩니다.',
      '은행·보험: ROE 대비 PBR. 경기민감(철강·화학·해운): 이익 대신 PBR 밴드. 성장주: PER을 이익 성장률로 나눈 PEG. 수주산업(조선·건설·방산): 수주잔고와 마진.'] },
    { t: '4. 성장이 꺾이는 신호를 본다', d: [
      '매출총이익률이 2~3개 분기 연속 하락',
      '재고자산회전일수가 늘어남(팔리는 속도보다 쌓이는 속도가 빠름)',
      '증권사 이익 추정치(컨센서스 EPS)가 연이어 하향',
      '설비투자(CAPEX)가 감가상각비를 크게 웃도는 상태가 이어지는데 매출이 따라오지 않음'] },
    { t: '5. 실적 발표 날 세 줄로 정리한다', d: [
      '컨센서스 대비: 매출·영업이익이 예상보다 높았나 낮았나',
      '일회성 제외: 자산 매각이익, 충당금 환입 같은 일회성 항목을 빼도 좋은가',
      '현금 동행: 영업활동현금흐름이 이익과 같은 방향으로 움직였나'] }
  ];

  const CF = [
    ['+', '−', '−', '본업으로 번 돈으로 투자하고 빚을 갚거나 배당하는 성숙 기업'],
    ['+', '−', '+', '본업 흑자에 외부 자금까지 끌어 투자를 늘리는 성장 기업'],
    ['−', '−', '+', '본업 적자를 외부 자금으로 메우며 투자하는 초기·바이오 기업 — 남은 현금으로 버틸 기간 확인'],
    ['−', '+', '+', '본업 적자를 자산 매각과 차입으로 메우는 상태 — 가장 경계']
  ];

  const TERMS = [
    ['매출액', '손익', '제품·서비스를 팔아 들어온 총액. 모든 이익의 출발점'],
    ['매출총이익', '손익', '매출액 − 매출원가. 제품 자체의 마진'],
    ['영업이익', '손익', '매출총이익 − 판매비와관리비. 본업에서 번 이익'],
    ['당기순이익', '손익', '영업이익에 금융손익·기타손익·법인세를 반영한 최종 이익'],
    ['EBITDA', '손익', '영업이익 + 감가상각비. 설비가 큰 회사의 현금 창출력 비교에 사용'],
    ['영업이익률', '비율', '영업이익 ÷ 매출액. 업종 평균과 함께 봐야 의미가 있음'],
    ['ROE', '비율', '순이익 ÷ 자기자본. 주주 돈으로 얼마나 버는지'],
    ['ROA', '비율', '순이익 ÷ 총자산. 빚까지 포함한 전체 자산의 효율'],
    ['PER', '가치', '주가 ÷ 주당순이익(EPS). 이익 대비 몇 배에 거래되는지'],
    ['PBR', '가치', '주가 ÷ 주당순자산(BPS). 장부가치 대비 몇 배인지'],
    ['PEG', '가치', 'PER ÷ 이익 성장률(%). 1 근처면 성장 대비 적정으로 보는 관행'],
    ['EV/EBITDA', '가치', '기업가치(시총+순차입금) ÷ EBITDA. 부채 구조가 다른 회사 비교에 유리'],
    ['EPS', '가치', '순이익 ÷ 발행주식수. 1주가 번 이익'],
    ['BPS', '가치', '자기자본 ÷ 발행주식수. 1주에 해당하는 순자산'],
    ['배당성향', '가치', '배당총액 ÷ 순이익. 번 돈 중 주주에게 돌려준 비율'],
    ['부채비율', '안정성', '부채 ÷ 자기자본. 업종마다 정상 범위가 다름(금융업 제외)'],
    ['유동비율', '안정성', '유동자산 ÷ 유동부채. 1년 안의 지급 능력'],
    ['이자보상배율', '안정성', '영업이익 ÷ 이자비용. 1배 미만이면 이자도 못 버는 상태'],
    ['순차입금', '안정성', '차입금 − 현금성자산. 마이너스면 순현금 회사'],
    ['영업활동현금흐름', '현금', '본업에서 실제로 들어온 현금. 이익의 질을 가늠'],
    ['투자활동현금흐름', '현금', '설비·지분 투자로 나간(또는 매각으로 들어온) 현금'],
    ['재무활동현금흐름', '현금', '차입·증자로 들어오거나 상환·배당으로 나간 현금'],
    ['잉여현금흐름(FCF)', '현금', '영업현금흐름 − 설비투자. 자유롭게 쓸 수 있는 현금'],
    ['CAPEX', '현금', '설비투자. 감가상각비보다 크면 확장 국면'],
    ['감가상각비', '현금', '설비 비용을 내용연수에 나눠 반영한 것. 현금 지출은 없음'],
    ['매출채권', '운전자본', '팔았지만 아직 받지 못한 돈'],
    ['재고자산', '운전자본', '아직 팔리지 않은 제품·원재료'],
    ['재고자산회전일수', '운전자본', '재고가 팔리기까지 걸리는 평균 일수. 늘어나면 경계'],
    ['계약자산', '운전자본', '수주산업에서 진행률로 인식했지만 청구하지 않은 금액'],
    ['연결재무제표', '공시', '지배회사와 종속회사를 하나로 합친 재무제표. 기본 분석 대상'],
    ['별도재무제표', '공시', '모회사 단독 재무제표. 배당 재원 판단에 사용'],
    ['잠정실적', '공시', '확정 전 회사가 먼저 알리는 실적. 정기보고서와 다를 수 있음'],
    ['분기보고서', '공시', '분기 종료 후 45일 안에 내는 정기보고서(4분기는 사업보고서 90일)'],
    ['감사의견', '공시', '외부감사인의 의견. 적정·한정·부적정·의견거절'],
    ['전환사채(CB)', '자금조달', '주식으로 바꿀 수 있는 채권. 전환 시 지분 희석'],
    ['신주인수권부사채(BW)', '자금조달', '신주를 살 권리가 붙은 채권'],
    ['리픽싱', '자금조달', '주가 하락 시 전환가액을 낮추는 조항. 희석이 커질 수 있음'],
    ['컨센서스', '실적', '증권사 추정치 평균. 실적 서프라이즈의 기준'],
    ['어닝 서프라이즈', '실적', '발표 실적이 컨센서스를 크게 웃도는 경우(통상 10% 이상)'],
    ['흑자전환', '실적', '직전 비교 기간 적자에서 이번에 흑자로 돌아선 것']
  ];

  const QUIZ = [
    ['PBR을 ROE와 PER로 나타내면?', ['ROE ÷ PER', 'ROE × PER', 'PER ÷ ROE', 'ROE + PER'], 1],
    ['영업이익은 흑자인데 영업현금흐름이 계속 마이너스다. 먼저 의심할 것은?', ['배당 확대', '이익의 질(매출채권·재고 증가)', '자사주 매입', '주가 과열'], 1],
    ['이자보상배율 0.7배의 의미는?', ['이자의 7배를 번다', '번 돈으로 이자도 다 못 낸다', '부채가 없다', '배당이 많다'], 1],
    ['현금흐름 부호(영업·투자·재무)가 (+, −, −)인 회사는?', ['성숙 우량 기업', '본업 적자 기업', '구조조정 기업', '신생 바이오'], 0],
    ['가장 경계해야 할 현금흐름 부호 조합은?', ['+, −, −', '+, −, +', '−, −, +', '−, +, +'], 3],
    ['경기민감 업종(철강·해운)의 가격 판단에 더 많이 쓰는 지표는?', ['PEG', 'PBR 밴드', '배당성향', '유동비율'], 1],
    ['감사의견 중 "적정"이 아닌 것은?', ['한정', '부적정', '의견거절', '셋 모두'], 3],
    ['분기보고서 제출 기한은 분기 종료 후 며칠 이내?', ['30일', '45일', '60일', '90일'], 1],
    ['EV/EBITDA의 EV에 포함되는 것은?', ['시가총액만', '시가총액 + 순차입금', '자기자본', '매출액'], 1],
    ['전환사채 발행이 잦을 때 주주에게 생기는 문제는?', ['배당 증가', '지분 희석', '부채비율 0', '감사의견 개선'], 1],
    ['재고자산회전일수가 늘어난다는 것은?', ['재고가 더 빨리 팔린다', '재고가 팔리는 데 더 오래 걸린다', '매출이 늘었다', '현금이 늘었다'], 1],
    ['PER 15배, 이익 성장률 30%인 회사의 PEG는?', ['0.5', '2', '15', '45'], 0],
    ['잉여현금흐름(FCF)의 계산은?', ['순이익 − 배당', '영업현금흐름 − 설비투자', '매출 − 원가', '자산 − 부채'], 1],
    ['연결재무제표가 보여주는 것은?', ['모회사 단독', '지배·종속회사를 합친 전체', '해외법인만', '감사인 의견'], 1],
    ['이 사이트가 "실적 급증"으로 표시하는 기준이 아닌 것은?', ['영업이익 전분기 대비 +50% 이상', '흑자전환', '영업이익 전년 동기 대비 +50% 이상', '주가 상한가'], 3]
  ];

  window.StudyView = function () {
    const cats = [...new Set(TERMS.map(t => t[1]))];
    return `<div class="page-head"><h1>재무제표 공부</h1><span class="stamp">점검 순서 5단계 · 용어 ${TERMS.length}개 · 퀴즈 ${QUIZ.length}문제 · 계산기</span></div>
    <div class="grid g2">
      <section class="card"><h2>재무제표, 이렇게 쓴다</h2>
        ${STEPS.map((s, i) => `<details ${i === 0 ? 'open' : ''}><summary>${esc(s.t)}</summary><ul>${s.d.map(x => `<li>${esc(x)}</li>`).join('')}</ul></details>`).join('')}
      </section>
      <section class="card"><h2>현금흐름 부호로 회사 읽기</h2>
        <div class="scroll"><table class="tbl"><thead><tr><th class="n">영업</th><th class="n">투자</th><th class="n">재무</th><th>해석</th></tr></thead><tbody>
        ${CF.map(r => `<tr>${r.slice(0, 3).map(v => `<td class="n ${v === '+' ? 'up' : 'dn'}">${v}</td>`).join('')}<td>${esc(r[3])}</td></tr>`).join('')}</tbody></table></div>
        <h2 style="margin-top:16px">DART 사업보고서 읽는 순서</h2>
        <ol><li>감사보고서의 감사의견</li><li>II. 사업의 내용 — 매출 구성·수주잔고</li><li>III. 재무에 관한 사항 — 요약재무, 손익·현금흐름</li><li>주석 — 매출채권·재고·충당금 변동</li><li>VII. 주주 — 최대주주·특수관계인 변동</li><li>주요사항보고서 — CB·유상증자 이력</li></ol>
      </section>
    </div>
    <section class="card"><h2>계산기</h2>
      <div class="calc">
        <label>현재 주가(원)<input type="number" id="c-price" value="50000"></label>
        <label>EPS(원)<input type="number" id="c-eps" value="4000"></label>
        <label>BPS(원)<input type="number" id="c-bps" value="40000"></label>
        <label>이익 성장률(%)<input type="number" id="c-g" value="15"></label>
        <label>목표 PER(배)<input type="number" id="c-tper" value="14"></label>
      </div>
      <div class="result" id="c-out"></div>
      <p class="note">예시 숫자가 들어 있습니다. 값을 바꾸면 바로 다시 계산합니다. 목표 주가는 EPS × 목표 PER로 단순 계산한 참고값입니다.</p>
    </section>
    <section class="card"><h2>용어 사전</h2>
      <div class="calc" style="margin-bottom:10px"><label>검색<input type="search" id="t-q" placeholder="예: PER, 현금흐름"></label>
      <label>분류<select id="t-cat"><option value="">전체</option>${cats.map(c => `<option>${esc(c)}</option>`).join('')}</select></label></div>
      <div class="scroll"><table class="tbl"><thead><tr><th>용어</th><th>분류</th><th>뜻</th></tr></thead><tbody id="t-body"></tbody></table></div>
    </section>
    <section class="card"><h2>오늘의 퀴즈</h2><div id="q-box"></div></section>`;
  };

  window.StudyBind = function (root) {
    const $ = id => root.querySelector('#' + id);
    const calc = () => {
      const p = +$('c-price').value, eps = +$('c-eps').value, bps = +$('c-bps').value, g = +$('c-g').value, tp = +$('c-tper').value;
      const per = eps ? p / eps : NaN, pbr = bps ? p / bps : NaN, roe = bps ? eps / bps * 100 : NaN, peg = g ? per / g : NaN, target = eps * tp, up = p ? (target / p - 1) * 100 : NaN;
      const f = (v, d = 2) => isFinite(v) ? v.toLocaleString('ko-KR', { maximumFractionDigits: d }) : '—';
      $('c-out').innerHTML = `PER ${f(per)}배 · PBR ${f(pbr)}배 · ROE ${f(roe, 1)}% · PEG ${f(peg)}<br>목표 PER 적용 주가 ${f(target, 0)}원 (현재가 대비 <span class="${up >= 0 ? 'up' : 'dn'}">${up >= 0 ? '+' : ''}${f(up, 1)}%</span>)`;
    };
    root.querySelectorAll('.calc input[type=number]').forEach(i => i.addEventListener('input', calc));
    calc();

    const terms = () => {
      const q = $('t-q').value.trim().toLowerCase(), c = $('t-cat').value;
      const rows = TERMS.filter(t => (!c || t[1] === c) && (!q || (t[0] + t[2]).toLowerCase().includes(q)));
      $('t-body').innerHTML = rows.map(t => `<tr><td><b>${esc(t[0])}</b></td><td><span class="chip">${esc(t[1])}</span></td><td>${esc(t[2])}</td></tr>`).join('') || '<tr><td colspan="3">검색 결과가 없습니다</td></tr>';
    };
    $('t-q').addEventListener('input', terms); $('t-cat').addEventListener('change', terms); terms();

    let qi = (new Date().getDate()) % QUIZ.length, score = 0, seen = 0;
    const showQ = () => {
      const [q, opts, ans] = QUIZ[qi];
      $('q-box').innerHTML = `<p><b>Q.</b> ${esc(q)}</p>${opts.map((o, i) => `<button type="button" class="btn quiz-opt" data-i="${i}">${i + 1}. ${esc(o)}</button>`).join('')}<p class="note" id="q-msg">맞힌 문제 ${score} / ${seen}</p>`;
      $('q-box').querySelectorAll('.quiz-opt').forEach(b => b.addEventListener('click', () => {
        if ($('q-box').dataset.done) return;
        $('q-box').dataset.done = '1'; seen++;
        const i = +b.dataset.i;
        if (i === ans) { score++; b.classList.add('ok'); } else { b.classList.add('no'); $('q-box').querySelectorAll('.quiz-opt')[ans].classList.add('ok'); }
        $('q-msg').innerHTML = `${i === ans ? '정답입니다.' : '오답입니다.'} 맞힌 문제 ${score} / ${seen} <button type="button" class="btn" id="q-next">다음 문제</button>`;
        $('q-next').addEventListener('click', () => { qi = (qi + 1) % QUIZ.length; delete $('q-box').dataset.done; showQ(); });
      }));
    };
    showQ();
  };
})();
