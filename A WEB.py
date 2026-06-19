import streamlit as st
from groq import Groq
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
import streamlit.components.v1 as components
import json
import io
import random
import base64

# ── API ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="🦉 링고", layout="centered", initial_sidebar_state="collapsed")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.main .block-container { padding:0.5rem 0.8rem 4rem !important; max-width:520px !important; }
[data-testid="stHorizontalBlock"] { gap:0.25rem !important; }
[data-testid="stPills"] { display:flex; flex-wrap:wrap; gap:6px !important; margin:6px 0; }
[data-testid="stPills"] button {
    border:3px solid #6366f1 !important;
    border-radius:10px !important;
    font-weight:700 !important;
    font-size:0.95rem !important;
    padding:6px 14px !important;
    min-height:0 !important;
    background:white !important;
    color:#4338ca !important;
}
[data-testid="stPills"] button:hover { background:#ede9fe !important; }
.stButton>button { width:100% !important; min-height:50px !important; font-size:1rem !important;
  border-radius:14px !important; font-weight:700 !important; margin:3px 0 !important; }
.stRadio label { font-size:0.82rem !important; padding:7px 10px !important;
  border:2px solid #e5e7eb; border-radius:12px; display:block; background:white; margin:3px 0; cursor:pointer; line-height:1.3 !important; }
audio { width:100% !important; border-radius:10px; margin:6px 0; }
.stTextInput input { font-size:1.1rem !important; padding:12px !important; border-radius:12px !important; }
h1 { font-size:1.5rem !important; text-align:center; }
h2,h3 { font-size:1.1rem !important; }
#MainMenu,footer,header { visibility:hidden; }
[data-testid="stSidebarNav"] { display:none; }
.score-bar { display:flex; justify-content:space-around; background:#f8fafc;
  border-radius:16px; padding:10px 8px; margin:6px 0 12px; border:2px solid #e2e8f0;
  font-size:1rem; font-weight:700; }
.q-card { background:linear-gradient(135deg,#6366f1,#8b5cf6); border-radius:18px;
  padding:24px 18px; text-align:center; margin:8px 0; color:white;
  font-size:1.3rem; font-weight:700; box-shadow:0 4px 14px rgba(99,102,241,.3); }
.correct-box { background:#dcfce7; border:2px solid #22c55e; border-radius:14px;
  padding:14px; text-align:center; font-size:1.1rem; font-weight:700; color:#166534; margin:8px 0; }
.wrong-box { background:#fee2e2; border:2px solid #ef4444; border-radius:14px;
  padding:14px; text-align:center; font-size:1.1rem; font-weight:700; color:#991b1b; margin:8px 0; }
.match-done { background:#dcfce7 !important; border:2px solid #22c55e !important;
  border-radius:12px; padding:12px; margin:4px 0; text-align:center;
  font-weight:700; color:#166534; font-size:0.95rem; }
.story-box { background:#f8fafc; border-left:4px solid #6366f1; border-radius:12px;
  padding:16px; margin:10px 0; font-size:1rem; line-height:1.8; color:#1f2937; }
.prog { background:#e5e7eb; border-radius:99px; height:10px; margin:6px 0 12px; overflow:hidden; }
.prog-fill { background:#22c55e; height:100%; border-radius:99px; transition:width .4s; }
.built-area { min-height:54px; background:#f0fdf4; border:2px solid #22c55e;
  border-radius:14px; padding:10px 12px; margin:8px 0; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.tile { display:inline-block; background:white; border:2px solid #6366f1;
  border-radius:10px; padding:7px 13px; font-size:0.95rem; font-weight:600; color:#4338ca; }
</style>""", unsafe_allow_html=True)

# ── 세션 초기화 ───────────────────────────────────────────────────────────────
def _init():
    defs = {
        "score":0, "lives":5, "streak":0, "total_ok":0, "total":0,
        "mode":"home", "cat":"일상 회화",
        # 듣기
        "ls_data":None, "ls_ans":False, "ls_res":"", "ls_audio_b64":None, "ls_history":[],
        # 짝 맞추기
        "mt_data":None, "mt_matched":None, "mt_sk":None, "mt_se":None,
        "mt_ko":None, "mt_eo":None, "mt_wrong":False, "mt_done":False,
        # 스피킹
        "sp_data":None, "sp_result":None, "sp_history":[],
        # 문장 만들기
        "wo_data":None, "wo_built":None, "wo_avail":None, "wo_ans":False, "wo_res":"", "wo_history":[],
        # 스토리
        "st_data":None, "st_qi":0, "st_ans":False, "st_fb":"",
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

# ── 공통 함수 ─────────────────────────────────────────────────────────────────
def tts(text):
    try:
        t = gTTS(text=text, lang="en", tld="com")
        fp = io.BytesIO(); t.write_to_fp(fp); fp.seek(0)
        return fp
    except Exception:
        return None

def ai(prompt, json_mode=False):
    kw = dict(model=MODEL, messages=[{"role":"user","content":prompt}], temperature=0.7)
    if json_mode:
        kw["response_format"] = {"type":"json_object"}
    return client.chat.completions.create(**kw).choices[0].message.content

def score_bar():
    h = "❤️"*st.session_state.lives + "🖤"*(5-st.session_state.lives)
    st.markdown(f'<div class="score-bar"><span>{h}</span><span>🔥 {st.session_state.streak}연속</span><span>⭐ {st.session_state.score}XP</span></div>', unsafe_allow_html=True)

def add_correct(xp=10):
    st.session_state.score += xp
    st.session_state.streak += 1
    st.session_state.total_ok += 1
    st.session_state.total += 1

def add_wrong():
    st.session_state.lives = max(0, st.session_state.lives-1)
    st.session_state.streak = 0
    st.session_state.total += 1

def game_over():
    if st.session_state.lives <= 0:
        acc = int(st.session_state.total_ok/st.session_state.total*100) if st.session_state.total else 0
        st.error("😭 하트를 모두 잃었어요!")
        st.markdown(f"""<div style='text-align:center;padding:20px;background:#f8fafc;border-radius:16px;'>
            <div style='font-size:3rem;'>🏆</div>
            <div style='font-size:1.5rem;font-weight:700;'>최종 점수: {st.session_state.score} XP</div>
            <div style='color:#6b7280;'>정확도: {acc}%</div></div>""", unsafe_allow_html=True)
        if st.button("🔄 다시 시작", type="primary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        return True
    return False

def nav(clear_fn=None):
    c1, c2 = st.columns([1,2])
    with c1:
        if st.button("← 홈"):
            if clear_fn: clear_fn()
            st.session_state.mode = "home"
            st.rerun()
    return c2

def show_vocab(vocab_list):
    if not vocab_list:
        return
    st.markdown("**📖 단어 & 숙어 설명**")
    items_html = ""
    for i, v in enumerate(vocab_list):
        word = v.get("word", "")
        meaning = v.get("meaning", "")
        example = v.get("example", "")
        b64 = ""
        if word:
            fp = tts(word)
            if fp:
                fp.seek(0)
                b64 = base64.b64encode(fp.read()).decode()
        sep = '<hr style="border:none;border-top:1px solid #e5e7eb;margin:6px 0;">' if i > 0 else ""
        if b64:
            btn = f'<button onclick="new Audio(\'data:audio/mp3;base64,{b64}\').play()" style="background:#ede9fe;border:2px solid #6366f1;border-radius:8px;padding:4px 10px;font-size:0.92rem;font-weight:700;color:#4338ca;cursor:pointer;margin-right:6px;">🔊 {word}</button>'
        else:
            btn = f'<strong style="color:#4338ca;">🔹 {word}</strong>'
        ex_html = f'<div style="color:#6b7280;font-size:0.82rem;margin-top:3px;padding-left:2px;">예) {example}</div>' if example else ""
        items_html += f'{sep}<div style="margin:4px 0;">{btn}<span style="color:#374151;font-size:0.88rem;vertical-align:middle;"> — {meaning}</span>{ex_html}</div>'
    height = len(vocab_list) * 68 + 16
    components.html(f"""<!DOCTYPE html><html><body style="margin:0;padding:6px 2px;background:transparent;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">{items_html}</body></html>""", height=height, scrolling=False)

def prog_bar(n, total):
    pct = int(n/total*100) if total else 0
    st.markdown(f'<div class="prog"><div class="prog-fill" style="width:{pct}%;"></div></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# 홈
# ════════════════════════════════════════════════════════════════════════════════
def show_home():
    st.markdown("# 🦉 링고")
    st.markdown("<p style='text-align:center;color:#6b7280;margin-top:-10px;'>AI 영어 학습</p>", unsafe_allow_html=True)
    score_bar()

    cats = ["일상 회화","비즈니스 영어","여행 영어","해외 쇼핑","감정 표현","뉴스/시사"]
    st.session_state.cat = st.selectbox("카테고리", cats, index=cats.index(st.session_state.cat), label_visibility="collapsed")

    st.markdown("**학습 모드를 선택하세요**")
    modes = [
        ("🎧","듣기 퀴즈","listening","영어 듣고 문장 고르기"),
        ("🔗","단어 짝 맞추기","matching","한↔영 단어 연결하기"),
        ("🎤","스피킹","speaking","영어로 말하기"),
        ("🧩","문장 만들기","wordorder","단어 클릭해 순서 맞추기"),
        ("📖","영어 스토리","story","스토리 읽고 문제 풀기"),
    ]
    for i in range(0, len(modes), 2):
        c1, c2 = st.columns(2)
        for col, j in [(c1,i),(c2,i+1)]:
            if j < len(modes):
                em, lb, key, desc = modes[j]
                with col:
                    if st.button(f"{em} {lb}"):
                        st.session_state.mode = key
                        st.rerun()
                    st.markdown(f'<div style="text-align:center;color:#9ca3af;font-size:0.78rem;margin:-4px 0 6px;">{desc}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# 1. 듣기 퀴즈
# ════════════════════════════════════════════════════════════════════════════════
def show_listening():
    st.markdown("# 🎧 듣기 퀴즈")
    score_bar()
    if game_over(): return

    def clear():
        st.session_state.ls_data = None
        st.session_state.ls_ans = False
        st.session_state.ls_res = ""
        st.session_state.ls_audio_b64 = None
    c2 = nav(clear)
    with c2:
        if st.button("새 문제 🔄"): clear(); st.rerun()

    if not st.session_state.ls_data:
        with st.spinner("문제 만드는 중..."):
            situations = ["식당 주문", "길 묻기", "쇼핑 계산", "전화 통화", "의사 진료", "호텔 체크인",
                          "친구와 약속", "직장 회의", "날씨 대화", "취미 이야기", "감정 표현", "사과/감사",
                          "면접", "대중교통", "카페 주문", "병원 예약", "집 구하기", "은행 업무"]
            situation = random.choice(situations)
            used = ", ".join([f'"{s}"' for s in st.session_state.ls_history[-8:]]) if st.session_state.ls_history else "없음"
            p = f"""
Make a listening quiz about '{situation}' in category '{st.session_state.cat}'.
IMPORTANT: Do NOT repeat these already-used sentences: [{used}]

Requirements:
- Use intermediate~advanced level sentence (NOT basic greetings like Hello/Thank you)
- Keep sentences SHORT: 6-9 words maximum so they fit on one line on mobile
- Include at least ONE advanced vocabulary word or idiom (e.g. procrastinate, come across, be on the fence, meticulous, pull through)
- 1 correct English sentence + 3 distractors that sound similar but differ in meaning

LANGUAGE RULE: korean / tip / vocab meaning fields MUST be written in Korean (한국어) ONLY.
NEVER use Russian, Vietnamese, Chinese, Japanese, or any other language. Korean characters only for those fields.

Respond ONLY raw JSON:
{{
  "correct": "The sentence (must include at least one advanced word)",
  "options": ["correct sentence","wrong 1","wrong 2","wrong 3"],
  "korean": "정답 한국어 뜻 (한국어만)",
  "tip": "이 표현 팁 (한국어만)",
  "vocab": [
    {{"word": "advanced word from sentence", "meaning": "한국어 뜻만", "example": "example sentence"}},
    {{"word": "another key word or idiom", "meaning": "한국어 뜻만", "example": "example sentence"}}
  ]
}}
Shuffle the options array randomly.
"""
            try:
                d = json.loads(ai(p, json_mode=True))
                random.shuffle(d["options"])
                st.session_state.ls_history.append(d.get("correct",""))
                st.session_state.ls_data = d
                st.session_state.ls_ans = False
                st.session_state.ls_res = ""
            except Exception as e:
                st.error(f"오류: {e}"); return

    data = st.session_state.ls_data
    st.markdown('<div style="text-align:center;color:#6b7280;font-size:0.9rem;margin-bottom:6px;">🔊 영어 문장을 듣고, 들린 문장을 고르세요! (3번 반복 재생)</div>', unsafe_allow_html=True)

    # 오디오 bytes를 세션에 캐시 (매번 TTS 재생성 방지)
    if not st.session_state.get("ls_audio_b64"):
        fp = tts(data["correct"])
        if fp:
            fp.seek(0)
            st.session_state.ls_audio_b64 = base64.b64encode(fp.read()).decode()

    b64 = st.session_state.get("ls_audio_b64", "")
    if b64:
        answered = st.session_state.ls_ans
        # 정답 확인 전: 자동재생 + 3번 반복
        # 정답 확인 후: 자동재생 없이 버튼만
        autoplay_js = "" if answered else "a.onended=function(){if(++c<3)setTimeout(function(){a.play()},700)};"
        autoplay_attr = "" if answered else "autoplay"
        components.html(f"""<!DOCTYPE html>
<html><body style="margin:0;padding:4px 0;background:transparent;">
<audio id="a" {autoplay_attr}><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>
<button onclick="document.getElementById('a').play()"
  style="width:100%;padding:11px;border-radius:12px;border:2px solid #6366f1;
  background:white;color:#6366f1;font-size:1rem;font-weight:700;cursor:pointer;">
  🔁 다시 듣기
</button>
<script>var c=0,a=document.getElementById('a');{autoplay_js}</script>
</body></html>""", height=55, scrolling=False)

    choice = st.radio("들은 문장은?", data["options"], key="ls_radio")

    if not st.session_state.ls_ans:
        if st.button("✔️ 정답 확인", type="primary"):
            if choice == data["correct"]:
                add_correct(10); st.session_state.ls_res = "correct"
            else:
                add_wrong(); st.session_state.ls_res = f"wrong|{data['correct']}"
            st.session_state.ls_ans = True; st.rerun()

    if st.session_state.ls_ans:
        r = st.session_state.ls_res
        if r == "correct":
            st.markdown('<div class="correct-box">🎯 정답! +10 XP</div>', unsafe_allow_html=True)
        else:
            ans = r.split("|",1)[1] if "|" in r else ""
            st.markdown(f'<div class="wrong-box">❌ 틀렸어요.<br><small>정답: {ans}</small></div>', unsafe_allow_html=True)

        st.markdown(f"""<div style='background:#f0f9ff;border-radius:14px;padding:14px;margin:8px 0;'>
            <div style='font-size:0.8rem;color:#6b7280;margin-bottom:4px;'>🇰🇷 한국어 뜻</div>
            <div style='font-size:1rem;font-weight:700;color:#0c4a6e;'>{data['korean']}</div>
            <div style='font-size:0.9rem;color:#374151;margin-top:6px;'>💡 {data.get('tip','')}</div>
        </div>""", unsafe_allow_html=True)

        show_vocab(data.get("vocab", []))

        if st.button("다음 문제 →", type="primary"):
            clear(); st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# 2. 단어 짝 맞추기
# ════════════════════════════════════════════════════════════════════════════════
def _mt_clear():
    st.session_state.mt_data = None
    st.session_state.mt_matched = []
    st.session_state.mt_sk = None; st.session_state.mt_se = None
    st.session_state.mt_ko = None; st.session_state.mt_eo = None
    st.session_state.mt_wrong = False; st.session_state.mt_done = False

def show_matching():
    st.markdown("# 🔗 단어 짝 맞추기")
    score_bar()
    if game_over(): return

    c2 = nav(_mt_clear)
    with c2:
        if st.button("새 단어 🔄"): _mt_clear(); st.rerun()

    if not st.session_state.mt_data:
        with st.spinner("단어 가져오는 중..."):
            p = f"""
Create 5 Korean-English expression pairs for '{st.session_state.cat}'.
Use natural, everyday Korean expressions matched with their natural English equivalents.
Intermediate~advanced level. Must be real, grammatically correct Korean that native speakers actually say.

Good examples:
- "마음이 복잡해" → "I have mixed feelings"
- "눈치가 없어" → "Can't read the room"
- "발이 넓다" → "Know a lot of people"

Respond ONLY raw JSON:
{{
  "pairs": [
    {{"korean":"자연스러운 한국어 표현","english":"Natural English equivalent"}}
  ]
}}
Exactly 5 pairs. Korean must be natural phrases that actually make sense.
"""
            try:
                d = json.loads(ai(p, json_mode=True))
                n = len(d["pairs"])
                ko = list(range(n)); random.shuffle(ko)
                eo = list(range(n)); random.shuffle(eo)
                st.session_state.mt_data = d
                st.session_state.mt_matched = []
                st.session_state.mt_sk = None; st.session_state.mt_se = None
                st.session_state.mt_ko = ko; st.session_state.mt_eo = eo
                st.session_state.mt_wrong = False; st.session_state.mt_done = False
            except Exception as e:
                st.error(f"오류: {e}"); return

    pairs = st.session_state.mt_data["pairs"]
    matched = st.session_state.mt_matched
    sk = st.session_state.mt_sk; se = st.session_state.mt_se

    if st.session_state.mt_wrong:
        st.markdown('<div class="wrong-box">❌ 틀렸어요! 다시 골라보세요.</div>', unsafe_allow_html=True)
        st.session_state.mt_wrong = False

    st.markdown(f'<div style="text-align:center;color:#6b7280;font-size:0.9rem;margin-bottom:6px;">한국어와 영어를 탭해서 짝 지어보세요! ({len(matched)}/{len(pairs)})</div>', unsafe_allow_html=True)
    prog_bar(len(matched), len(pairs))

    ck, ce = st.columns(2)

    with ck:
        st.markdown("🇰🇷 **한국어**")
        for i in st.session_state.mt_ko:
            if i in matched:
                st.markdown(f'<div class="match-done">✅ {pairs[i]["korean"]}</div>', unsafe_allow_html=True)
            else:
                sel = (sk == i)
                label = ("★ " if sel else "") + pairs[i]["korean"]
                if st.button(label, key=f"mk_{i}"):
                    st.session_state.mt_sk = i
                    cur_se = st.session_state.mt_se
                    if cur_se is not None:
                        if cur_se == i:
                            matched.append(i); st.session_state.mt_matched = matched
                            st.session_state.mt_sk = None; st.session_state.mt_se = None
                            st.session_state.score += 3; st.session_state.streak += 1
                            if len(matched) == len(pairs): st.session_state.mt_done = True
                        else:
                            add_wrong(); st.session_state.mt_wrong = True
                            st.session_state.mt_sk = None; st.session_state.mt_se = None
                    st.rerun()

    with ce:
        st.markdown("🇺🇸 **영어**")
        for i in st.session_state.mt_eo:
            if i in matched:
                st.markdown(f'<div class="match-done">✅ {pairs[i]["english"]}</div>', unsafe_allow_html=True)
            else:
                sel = (se == i)
                label = ("★ " if sel else "") + pairs[i]["english"]
                if st.button(label, key=f"me_{i}"):
                    st.session_state.mt_se = i
                    cur_sk = st.session_state.mt_sk
                    if cur_sk is not None:
                        if cur_sk == i:
                            matched.append(i); st.session_state.mt_matched = matched
                            st.session_state.mt_sk = None; st.session_state.mt_se = None
                            st.session_state.score += 3; st.session_state.streak += 1
                            if len(matched) == len(pairs): st.session_state.mt_done = True
                        else:
                            add_wrong(); st.session_state.mt_wrong = True
                            st.session_state.mt_sk = None; st.session_state.mt_se = None
                    st.rerun()

    if st.session_state.mt_done:
        st.markdown('<div class="correct-box">🎉 모두 맞췄어요! 완벽해요!</div>', unsafe_allow_html=True)
        if st.button("다음 세트 →", type="primary"):
            _mt_clear(); st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# 3. 스피킹
# ════════════════════════════════════════════════════════════════════════════════
def show_speaking():
    st.markdown("# 🎤 스피킹")
    score_bar()
    if game_over(): return

    def clear():
        st.session_state.sp_data = None
        st.session_state.sp_result = None
        # 히스토리는 유지 (중복 방지용)
    c2 = nav(clear)
    with c2:
        if st.button("새 문장 🔄"): clear(); st.rerun()

    if not st.session_state.sp_data:
        with st.spinner("문장 불러오는 중..."):
            history = st.session_state.sp_history
            used = ", ".join([f'"{s}"' for s in history[-10:]]) if history else "없음"
            p = f"""
Speaking practice for Korean learner of English. Category: '{st.session_state.cat}'.
IMPORTANT: Do NOT use any of these already-used sentences: [{used}]
Choose a completely DIFFERENT sentence with a DIFFERENT topic/situation each time.

Requirements:
- Include at least ONE advanced/uncommon English word or idiom per sentence
- Examples of good advanced words: eloquent, spontaneous, procrastinate, come to terms with, on the fence, pull off, bear in mind, shed light on
- NOT basic words like go/come/eat/drink

LANGUAGE RULE: korean / tip / vocab meaning fields MUST be written in Korean (한국어) ONLY.
NEVER use Russian, Vietnamese, Chinese, Japanese, or any other language. Korean characters only for those fields.

Respond ONLY raw JSON:
{{
  "sentence": "English sentence with at least one advanced word",
  "korean": "한국어 번역만",
  "tip": "발음 팁 (한국어만)",
  "difficulty": "Easy/Medium/Hard",
  "vocab": [
    {{"word": "advanced word from sentence", "meaning": "한국어 뜻만", "example": "another example sentence"}},
    {{"word": "another key expression", "meaning": "한국어 뜻만", "example": "another example sentence"}}
  ]
}}
"""
            try:
                d = json.loads(ai(p, json_mode=True))
                st.session_state.sp_data = d
                st.session_state.sp_history.append(d.get("sentence", ""))
            except Exception as e:
                st.error(f"오류: {e}"); return

    data = st.session_state.sp_data
    dc = {"Easy":"#22c55e","Medium":"#f59e0b","Hard":"#ef4444"}.get(data.get("difficulty",""),"#6366f1")
    st.markdown(f'<div style="text-align:center;margin:4px 0 8px;"><span style="background:{dc};color:white;padding:3px 12px;border-radius:99px;font-size:0.8rem;font-weight:700;">{data.get("difficulty","")}</span></div>', unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;color:#6b7280;font-size:0.9rem;">아래 영어 문장을 소리 내어 읽어보세요!</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="q-card">{data["sentence"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;color:#6b7280;margin:-2px 0 8px;">🇰🇷 {data["korean"]}</div>', unsafe_allow_html=True)
    st.info(f"💡 {data.get('tip','')}")

    fp = tts(data["sentence"])
    if fp:
        st.markdown("**원어민 발음 듣기**")
        st.audio(fp, format="audio/mp3")

    if not st.session_state.get("sp_result"):
        st.markdown("**🎙️ 따라 말하기**")
        audio = mic_recorder(start_prompt="녹음 시작", stop_prompt="🛑 완료", key="sp_mic")

        if audio and "bytes" in audio:
            with st.spinner("발음 분석 중..."):
                try:
                    af = io.BytesIO(audio["bytes"]); af.name = "audio.wav"
                    trans = client.audio.transcriptions.create(model="whisper-large-v3", file=af, response_format="text")
                    spoken = trans.strip()

                    if not spoken or spoken in [".", ",", ""]:
                        st.warning("녹음이 너무 짧아요. 다시 말해보세요!")
                    else:
                        ep = f"""
You are evaluating English pronunciation for a Korean learner.
Target sentence: "{data['sentence']}"
What the learner said: "{spoken}"

Respond ONLY with this exact JSON. The feedback field MUST be written in Korean only (한국어만 사용, 다른 언어 절대 금지):
{{"score": 82, "grade": "A", "feedback": "발음이 정확해요! 조금 더 자신감 있게 말해보세요."}}

- score: integer 0-100
- grade: S(95+) A(80+) B(65+) C(below 65)
- feedback: 한국어로만 1-2문장. NO Vietnamese, NO English, NO other language.
"""
                        r = json.loads(ai(ep, json_mode=True))
                        sc = r.get("score", 0)
                        gr = r.get("grade", "C")
                        fb = r.get("feedback", "")
                        if isinstance(fb, dict):
                            fb = fb.get("content", fb.get("detail", str(fb)))
                        if sc >= 80: add_correct(15)
                        elif sc >= 60: add_correct(8)
                        else: add_wrong()
                        st.session_state.sp_result = {"sc": sc, "gr": gr, "fb": fb, "spoken": spoken}
                        st.rerun()
                except Exception as e:
                    st.error(f"분석 오류: {e}")

    if st.session_state.get("sp_result"):
        res = st.session_state.sp_result
        sc, gr, fb = res["sc"], res["gr"], res["fb"]
        st.markdown(f"🗣️ **{res['spoken']}**")
        ge = {"S":"🌟","A":"🎉","B":"👍","C":"💪"}.get(gr,"💪")
        bc = "#22c55e" if sc>=80 else "#f59e0b" if sc>=60 else "#ef4444"
        st.markdown(f"""<div style='background:#f8fafc;border-radius:16px;padding:14px;text-align:center;margin:8px 0;'>
            <div style='font-size:1.8rem;'>{ge}</div>
            <div style='font-size:1.4rem;font-weight:800;color:{bc};'>{sc}점 · {gr}등급</div>
            <div style='background:#e5e7eb;border-radius:99px;height:10px;margin:8px 0;overflow:hidden;'>
              <div style='background:{bc};width:{sc}%;height:100%;border-radius:99px;'></div></div>
            <div style='color:#374151;'>{fb}</div>
        </div>""", unsafe_allow_html=True)

        show_vocab(data.get("vocab", []) if data else [])

        if st.button("다음 문장 →", type="primary"):
            clear(); st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# 4. 문장 만들기 (단어 순서)
# ════════════════════════════════════════════════════════════════════════════════
def _wo_clear():
    st.session_state.wo_data = None
    st.session_state.wo_built = []
    st.session_state.wo_avail = []
    st.session_state.wo_ans = False
    st.session_state.wo_res = ""

def show_wordorder():
    st.markdown("# 🧩 문장 만들기")
    score_bar()
    if game_over(): return

    c2 = nav(_wo_clear)
    with c2:
        if st.button("새 문장 🔄"): _wo_clear(); st.rerun()

    if not st.session_state.wo_data:
        with st.spinner("문제 만드는 중..."):
            history = st.session_state.wo_history
            used = ", ".join([f'"{s}"' for s in history[-8:]]) if history else "없음"
            p = f"""
Word ordering exercise for Korean English learner. Category: '{st.session_state.cat}'.
IMPORTANT: Do NOT repeat these already-used sentences: [{used}]

Requirements:
- Use 5-8 words
- Mix of easy/medium/hard: most sentences intermediate level, occasionally one harder word
- NOT kindergarten level (not just "I go to school") but also NOT overly academic
- Natural everyday English that a learner would actually use

LANGUAGE RULE: korean / vocab meaning fields MUST be written in Korean (한국어) ONLY.
NEVER use Russian, Vietnamese, Chinese, Japanese, or any other language. Korean characters only for those fields.

Respond ONLY raw JSON:
{{
  "korean": "한국어 문장만",
  "sentence": "The correct English sentence with at least one advanced word",
  "words": ["word1","word2","word3","word4","word5"],
  "vocab": [
    {{"word": "key word or expression from sentence", "meaning": "한국어 뜻만", "example": "example sentence"}},
    {{"word": "another useful word or phrase", "meaning": "한국어 뜻만", "example": "example sentence"}}
  ]
}}
words = sentence split by spaces exactly.
"""
            try:
                d = json.loads(ai(p, json_mode=True))
                words = d.get("words", d["sentence"].split())
                shuffled = [(i, w) for i, w in enumerate(words)]
                random.shuffle(shuffled)
                while [w for _,w in shuffled] == words and len(words) > 1:
                    random.shuffle(shuffled)
                st.session_state.wo_history.append(d.get("sentence", ""))
                st.session_state.wo_data = d
                st.session_state.wo_avail = shuffled
                st.session_state.wo_built = []
                st.session_state.wo_ans = False
                st.session_state.wo_res = ""
            except Exception as e:
                st.error(f"오류: {e}"); return

    data = st.session_state.wo_data
    avail = st.session_state.wo_avail
    built = st.session_state.wo_built

    st.markdown('<div style="text-align:center;color:#6b7280;font-size:0.9rem;">단어를 순서대로 클릭해서 문장을 완성하세요!</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="q-card">{data["korean"]}</div>', unsafe_allow_html=True)

    # 만들고 있는 문장
    st.markdown("**내가 만드는 문장:**")
    if built:
        tiles = " ".join([f'<span class="tile">{w}</span>' for _,w in built])
        st.markdown(f'<div class="built-area">{tiles}</div>', unsafe_allow_html=True)
        if not st.session_state.wo_ans:
            if st.button("← 마지막 단어 지우기"):
                last = built.pop()
                avail.append(last)
                st.session_state.wo_built = built
                st.session_state.wo_avail = avail
                st.rerun()
    else:
        st.markdown('<div class="built-area" style="justify-content:center;"><span style="color:#9ca3af;">여기에 단어가 쌓여요</span></div>', unsafe_allow_html=True)

    # 선택 가능한 단어들 - pills로 다닥다닥
    if not st.session_state.wo_ans and avail:
        st.markdown("**단어 선택:**")
        avail_words = [w for _, w in avail]
        sel = st.pills("", avail_words, key=f"wo_pills_{len(avail)}", label_visibility="collapsed")
        if sel is not None:
            for item in list(avail):
                if item[1] == sel:
                    built.append(item)
                    avail.remove(item)
                    break
            st.session_state.wo_built = built
            st.session_state.wo_avail = avail
            st.rerun()

    if not st.session_state.wo_ans and not avail and built:
        if st.button("✔️ 제출하기", type="primary"):
            user_s = " ".join([w for _,w in built]).strip().lower().rstrip(".,!?")
            corr_s = data["sentence"].strip().lower().rstrip(".,!?")
            if user_s == corr_s:
                add_correct(15); st.session_state.wo_res = "correct"
            else:
                add_wrong(); st.session_state.wo_res = f"wrong|{' '.join([w for _,w in built])}"
            st.session_state.wo_ans = True; st.rerun()

    if st.session_state.wo_ans:
        r = st.session_state.wo_res
        if r == "correct":
            st.markdown('<div class="correct-box">🎯 정답! +15 XP</div>', unsafe_allow_html=True)
        else:
            ua = r.split("|",1)[1] if "|" in r else ""
            st.markdown(f'<div class="wrong-box">❌ 틀렸어요.<br><small>내 답: {ua}</small></div>', unsafe_allow_html=True)
        st.markdown(f"""<div style='background:#f0fdf4;border-radius:14px;padding:14px;margin:8px 0;'>
            <div style='font-size:0.8rem;color:#6b7280;'>정답</div>
            <div style='font-size:1.1rem;font-weight:700;color:#166534;'>{data["sentence"]}</div>
        </div>""", unsafe_allow_html=True)

        show_vocab(data.get("vocab", []))

        if st.button("다음 문장 →", type="primary"):
            _wo_clear(); st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# 5. 영어 스토리
# ════════════════════════════════════════════════════════════════════════════════
def _st_clear():
    st.session_state.st_data = None
    st.session_state.st_qi = 0
    st.session_state.st_ans = False
    st.session_state.st_fb = ""

def show_story():
    st.markdown("# 📖 영어 스토리")
    score_bar()
    if game_over(): return

    c2 = nav(_st_clear)
    with c2:
        if st.button("새 스토리 🔄"): _st_clear(); st.rerun()

    if not st.session_state.st_data:
        with st.spinner("AI가 스토리를 쓰는 중..."):
            p = f"""
Write a short English story for Korean English learners + 3 comprehension questions.
Category: '{st.session_state.cat}'. Story: 4-5 sentences, simple and fun.
Respond ONLY raw JSON:
{{
  "title": "Story title",
  "story": "Full English story here.",
  "korean_summary": "스토리 한국어 요약 (2문장)",
  "questions": [
    {{
      "question": "English comprehension question?",
      "options": ["first real option text","second real option text","third real option text","fourth real option text"],
      "answer": "MUST be copied EXACTLY from one of the options above, word for word"
    }}
  ]
}}
CRITICAL: The "answer" field must be the EXACT same string as one of the four options. Never use "Answer A/B/C/D". Make exactly 3 questions.
"""
            try:
                st.session_state.st_data = json.loads(ai(p, json_mode=True))
                st.session_state.st_qi = 0
                st.session_state.st_ans = False
                st.session_state.st_fb = ""
            except Exception as e:
                st.error(f"오류: {e}"); return

    data = st.session_state.st_data
    questions = data.get("questions", [])
    qi = st.session_state.st_qi

    st.markdown(f"### 📚 {data.get('title','')}")
    st.markdown(f'<div class="story-box">{data.get("story","")}</div>', unsafe_allow_html=True)

    fp = tts(data.get("story",""))
    if fp: st.audio(fp, format="audio/mp3")

    with st.expander("🇰🇷 한국어 요약 보기"):
        st.write(data.get("korean_summary",""))

    st.markdown("---")

    if qi >= len(questions):
        st.markdown('<div class="correct-box">🎉 스토리 완료! 모든 문제를 풀었어요!</div>', unsafe_allow_html=True)
        if st.button("새 스토리 →", type="primary"):
            _st_clear(); st.rerun()
        return

    q = questions[qi]
    st.markdown(f'<div style="text-align:center;color:#6b7280;font-size:0.85rem;margin-bottom:4px;">문제 {qi+1} / {len(questions)}</div>', unsafe_allow_html=True)
    prog_bar(qi, len(questions))
    st.markdown(f'<div class="q-card">{q["question"]}</div>', unsafe_allow_html=True)

    choice = st.radio("정답을 고르세요", q["options"], key=f"st_radio_{qi}")

    if not st.session_state.st_ans:
        if st.button("✔️ 정답 확인", type="primary"):
            if choice == q["answer"]:
                add_correct(10); st.session_state.st_fb = "correct"
            else:
                add_wrong(); st.session_state.st_fb = f"wrong|{q['answer']}"
            st.session_state.st_ans = True; st.rerun()

    if st.session_state.st_ans:
        fb = st.session_state.st_fb
        if fb == "correct":
            st.markdown('<div class="correct-box">🎯 정답! +10 XP</div>', unsafe_allow_html=True)
        else:
            ans = fb.split("|",1)[1] if "|" in fb else ""
            st.markdown(f'<div class="wrong-box">❌ 틀렸어요. 정답: {ans}</div>', unsafe_allow_html=True)
        if st.button("다음 문제 →", type="primary"):
            st.session_state.st_qi += 1
            st.session_state.st_ans = False
            st.session_state.st_fb = ""
            st.rerun()

# ── 라우터 ────────────────────────────────────────────────────────────────────
{
    "home": show_home,
    "listening": show_listening,
    "matching": show_matching,
    "speaking": show_speaking,
    "wordorder": show_wordorder,
    "story": show_story,
}.get(st.session_state.mode, show_home)()
