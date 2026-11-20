# 이중재의 투자노트

GitHub Pages로 운영하는 개인 투자노트입니다. GitHub Actions가 평일 하루 4번 자동으로 데이터를 모아 사이트를 갱신합니다.

| 메뉴 | 내용 | 데이터 |
|---|---|---|
| 홈 | 지수 요약, 장중 흐름 판정, 실적 급증 종목, 강세종목, 최신 브리핑 | 아래 전체 |
| 아침 브리핑 | `briefs/` 폴더의 PDF 목록 | 직접 업로드 |
| 실적발표 종목 | 분기·반기·사업보고서와 잠정실적 공시, 실적 급증 종목 자동 리포트 | OpenDART |
| 강세종목·수급 | 상승률·하락률·거래대금 상위, 투자자별 순매수, 등락 종목 수 | KRX (FinanceDataReader·pykrx) |
| 장중 흐름 | 코스피·코스닥·S&P 500·나스닥 5분봉, 전강후약/전약후강 판정 | Yahoo Finance |
| 미국·글로벌 | 미국 지수, 금리·환율·원자재, 아시아·유럽 지수, 미국 대형주 | Yahoo Finance |
| 재무제표 공부 | 점검 순서, 현금흐름 부호, 용어 사전, 퀴즈, PER·PBR 계산기 | 정적 콘텐츠 |
| 메모 | `data/memo.json` 내용 | 직접 작성 |

## 처음 설정 (한 번만, 약 10분)

1. **저장소 만들기** — GitHub에서 `New repository` → 이름 `invest-note` → **Public** → Create.
2. **파일 올리기** — 저장소 화면의 `uploading an existing file` (또는 `Add file → Upload files`)을 눌러, 압축을 푼 폴더 **안의 내용 전체**를 끌어다 놓고 `Commit changes`.
   - Mac Finder에서는 `.github` 폴더가 숨김이라 안 보일 수 있습니다. `Cmd + Shift + .` 로 숨김 파일을 표시한 뒤 함께 끌어다 놓으세요.
   - 업로드 뒤 저장소에 `.github/workflows/update.yml` 이 보이는지 확인하세요. 없으면 `Add file → Create new file` 에서 파일 이름에 `.github/workflows/update.yml` 을 입력하고 압축 파일 속 내용을 붙여 넣으면 됩니다.
3. **DART 키 등록** — `Settings → Secrets and variables → Actions → New repository secret`
   - Name: `DART_API_KEY` / Secret: OpenDART 인증키 40자리
4. **쓰기 권한 허용** — `Settings → Actions → General → Workflow permissions` 에서 **Read and write permissions** 선택 → Save.
5. **Pages 켜기** — `Settings → Pages → Build and deployment` 에서 Source `Deploy from a branch`, Branch `main` / `/ (root)` → Save.
6. **첫 실행** — `Actions` 탭 → `투자노트 자동 갱신` → `Run workflow`. 2~5분 뒤 아래 주소에서 확인합니다.
   - `https://<GitHub아이디>.github.io/invest-note/`

## 자동 갱신 시간 (한국시간, 평일)

- 08:20 미국 마감·아시아 개장 전 / 15:50 국내 장마감 / 18:00·20:30 실적 공시
- `briefs/` 에 PDF를 올리면 그때도 목록이 바로 갱신됩니다.
- 시간 변경은 `.github/workflows/update.yml` 의 `cron`(UTC 기준, 한국시간 −9시간)을 고치면 됩니다.

## 실적 급증 기준

영업이익(3개월) 10억 원 이상이면서 다음 중 하나:
- 전분기 대비 +50% 이상 (3분기·반기보고서)
- 전년 동기 대비 +50% 이상
- 흑자전환

해당 종목은 `reports/` 에 리포트 페이지가 자동으로 만들어집니다(손익 요약, QoQ·YoY, 최근 1년 CB·BW·EB·유상증자 결정 건수, DART 원문 링크). 기준은 `scripts/update_dart.py` 의 `MIN_OP`, `flags_for` 에서 바꿀 수 있습니다.

## 알아둘 점

- 시세는 무료 공개 데이터(Yahoo Finance·KRX)라 지연·누락이 있을 수 있습니다. 실패한 항목은 "수집 실패"로 표시되고 나머지는 계속 갱신됩니다.
- DART 무료 키는 하루 20,000회까지 호출할 수 있어 이 사이트 사용량으로 충분합니다.
- 공개 저장소이므로 인증키는 반드시 Secrets에만 넣고 파일에 쓰지 마세요.
- 본 사이트는 정보 제공 목적이며 매매 권유가 아닙니다.
