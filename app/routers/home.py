from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# 외부 CSS·JS·이미지·글꼴을 전혀 불러오지 않는 한 장짜리 페이지(그림은 아래 SVG를 직접 그린 것).
HOME_HTML = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Board API</title>
<style>
  :root {
    --bg: #f6f7fb; --card: #ffffff; --text: #1d2433; --muted: #5b667a; --line: #e3e7ef;
    --accent: #4f46e5; --accent-text: #ffffff; --ok: #0a8f5b; --bad: #c0392b; --bar: #d9deea; --bar2: #eceff6;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1420; --card: #171e2e; --text: #e8ecf5; --muted: #9aa6bd; --line: #2a3347;
      --accent: #818cf8; --accent-text: #0f1420; --ok: #34d399; --bad: #f87171; --bar: #36415a; --bar2: #263046;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text); line-height: 1.6; word-break: keep-all;
    font-family: system-ui, -apple-system, "Segoe UI", "Noto Sans KR", "Malgun Gothic", sans-serif;
  }
  main { max-width: 980px; margin: 0 auto; padding: 48px 20px 40px; }
  .hero { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 32px; align-items: center; }
  .eyebrow { margin: 0 0 8px; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); font-weight: 700; }
  h1 { margin: 0 0 12px; font-size: clamp(36px, 6vw, 56px); line-height: 1.1; }
  .lead { margin: 0 0 22px; color: var(--muted); font-size: 17px; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
  .btn {
    display: inline-block; padding: 10px 16px; border-radius: 10px; text-decoration: none; font-weight: 600;
    color: var(--text); background: var(--card); border: 1px solid var(--line);
  }
  .btn:hover { border-color: var(--accent); }
  .btn.primary { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
  .status { margin: 0; font-size: 14px; color: var(--muted); }
  .status::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--muted); margin-right: 8px; }
  .status.ok { color: var(--ok); } .status.ok::before { background: var(--ok); }
  .status.bad { color: var(--bad); } .status.bad::before { background: var(--bad); }
  .art { width: 100%; height: auto; }
  .art .card { fill: var(--card); stroke: var(--line); stroke-width: 2; }
  .art .line { stroke: var(--line); stroke-width: 2; }
  .art .bar { fill: var(--bar); } .art .bar2 { fill: var(--bar2); }
  .art .flow { stroke: var(--accent); stroke-width: 2; stroke-dasharray: 5 6; fill: none; }
  .art .badge { fill: var(--accent); } .art .badge-text { fill: var(--accent-text); font: 700 13px system-ui, sans-serif; }
  .art .db { fill: none; stroke: var(--accent); stroke-width: 3; }
  h2 { margin: 44px 0 14px; font-size: 20px; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .feature { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
  .feature b { display: block; margin-bottom: 2px; }
  .feature span { color: var(--muted); font-size: 14px; }
  ol { margin: 0; padding-left: 22px; color: var(--muted); }
  ol li { margin: 4px 0; } ol b, ol code { color: var(--text); }
  code { background: var(--bar2); padding: 1px 6px; border-radius: 6px; font-size: 90%; }
  footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
  @media (max-width: 760px) {
    .hero { grid-template-columns: 1fr; } .grid { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 480px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <p class="eyebrow">RESTful Backend · FastAPI</p>
      <h1>Board API</h1>
      <p class="lead">회원가입·로그인(JWT)과 게시글·댓글을 제공하는 게시판 백엔드입니다.
        작성자만 수정·삭제할 수 있도록 권한을 검증하고, 모든 오류를 하나의 형식으로 돌려줍니다.</p>
      <div class="actions">
        <a class="btn primary" href="/docs">API 문서 열기 (Swagger)</a>
        <a class="btn" href="/redoc">ReDoc</a>
        <a class="btn" href="/health">상태 확인</a>
      </div>
      <p class="status" id="status">서버 상태를 확인하는 중…</p>
    </div>
    <svg class="art" viewBox="0 0 440 330" role="img" aria-label="게시글 목록, JWT 자물쇠, 데이터베이스를 그린 그림">
      <rect class="card" x="8" y="8" width="296" height="236" rx="16"/>
      <circle cx="32" cy="32" r="6" fill="#ff6b6b"/><circle cx="52" cy="32" r="6" fill="#ffd166"/><circle cx="72" cy="32" r="6" fill="#06d6a0"/>
      <line class="line" x1="8" y1="52" x2="304" y2="52"/>
      <rect x="28" y="70" width="46" height="20" rx="10" fill="#4f46e5"/>
      <rect class="bar" x="86" y="75" width="150" height="10" rx="5"/><rect class="bar2" x="248" y="75" width="40" height="10" rx="5"/>
      <rect x="28" y="108" width="46" height="20" rx="10" fill="#0ea5e9"/>
      <rect class="bar" x="86" y="113" width="120" height="10" rx="5"/><rect class="bar2" x="248" y="113" width="40" height="10" rx="5"/>
      <rect x="28" y="146" width="46" height="20" rx="10" fill="#f59e0b"/>
      <rect class="bar" x="86" y="151" width="170" height="10" rx="5"/><rect class="bar2" x="268" y="151" width="20" height="10" rx="5"/>
      <rect class="bar2" x="60" y="186" width="200" height="8" rx="4"/>
      <rect class="bar2" x="60" y="206" width="150" height="8" rx="4"/>
      <path class="flow" d="M304 90 C 340 90, 340 90, 352 90"/>
      <path class="flow" d="M304 200 C 340 200, 330 245, 352 255"/>
      <circle class="badge" cx="392" cy="90" r="40"/>
      <rect x="378" y="86" width="28" height="22" rx="4" fill="#ffffff"/>
      <path d="M384 86 v-8 a8 8 0 0 1 16 0 v8" fill="none" stroke="#ffffff" stroke-width="4"/>
      <text class="badge-text" x="392" y="148" text-anchor="middle" style="fill: var(--muted)">JWT</text>
      <ellipse class="db" cx="392" cy="236" rx="34" ry="12"/>
      <path class="db" d="M358 236 v46 a34 12 0 0 0 68 0 v-46"/>
      <path class="db" d="M358 259 a34 12 0 0 0 68 0"/>
      <text class="badge-text" x="392" y="312" text-anchor="middle" style="fill: var(--muted)">PostgreSQL</text>
    </svg>
  </section>

  <h2>주요 기능</h2>
  <section class="grid">
    <div class="feature"><b>JWT 인증·인가</b><span>bcrypt 해싱, 30분 토큰, 작성자만 수정·삭제(403)</span></div>
    <div class="feature"><b>게시글 · 댓글</b><span>페이지네이션, 분류 거르기, 검색, 글 삭제 시 댓글 CASCADE</span></div>
    <div class="feature"><b>이미지 업로드</b><span>파일 내용으로 종류 검사, 5MB 제한, 무작위 파일명</span></div>
    <div class="feature"><b>통일된 오류 형식</b><span>code · message · details, 입력값은 되돌려 주지 않음</span></div>
    <div class="feature"><b>운영 기능</b><span>요청 번호 로깅, CORS, 조회 캐시, DB 확인 헬스체크</span></div>
    <div class="feature"><b>문서 · 테스트</b><span>OpenAPI(Swagger) 문서, pytest로 동작과 문서를 함께 검증</span></div>
  </section>

  <h2>Swagger에서 바로 시험해 보기</h2>
  <ol>
    <li><b>API 문서 열기</b>를 누르고 <code>POST /auth/signup</code>으로 가입합니다.</li>
    <li>오른쪽 위 <b>Authorize</b>에 이메일(<code>username</code> 칸)과 비밀번호를 입력합니다.</li>
    <li>자물쇠 표시가 있는 API(<code>POST /posts</code> 등)를 <b>Try it out</b>으로 실행합니다.</li>
  </ol>

  <footer>Board API · FastAPI · SQLAlchemy · PostgreSQL · AWS EC2</footer>
</main>
<script>
  (function () {
    var el = document.getElementById("status");
    function show(cls, text) { el.className = "status " + cls; el.textContent = text; }
    fetch("/health")
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (res.ok) { show("ok", "서버 정상 · DB 연결 정상"); }
        else { show("bad", "서버는 켜져 있지만 DB에 연결할 수 없습니다"); }
      })
      .catch(function () { show("bad", "서버 상태를 확인할 수 없습니다"); });
  })();
</script>
</body>
</html>
'''

router = APIRouter()


@router.get('/', response_class=HTMLResponse, include_in_schema=False)
async def home():
    '''대문 화면. 문서(/docs)로 안내하는 페이지라서 Swagger 문서 목록에는 넣지 않는다.'''
    return HTMLResponse(HOME_HTML)
