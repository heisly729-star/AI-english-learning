"""
ReadFit - 영어 학습 플랫폼
Streamlit + Firebase + OpenAI를 활용한 인터랙티브 영어 학습 도구
"""

import streamlit as st
import random
import string
from datetime import datetime
from openai import OpenAI

# ==========================================================================
# GLOBAL STYLES (기존 유지)
# ==========================================================================

def apply_global_styles():
    """앱 전체에 공통 스타일을 적용합니다."""
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at 10% 20%, #e0f2fe 0%, #f8fafc 30%, #f3e8ff 65%, #fdf2f8 100%);
        }
        div.block-container { padding-top: 2rem; }
        .login-hero { text-align: center; margin-bottom: 0.25rem; }
        .login-hero h1 { margin: 0; font-size: 32px; color: #0f172a; font-weight: 800; }
        .login-sub { text-align: center; color: #475569; font-weight: 700; font-size: 18px; margin-bottom: 1.5rem; }
        .card {
            background: rgba(255,255,255,0.92);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 18px 48px rgba(15,23,42,0.12);
            border: 1px solid #e2e8f0;
        }
        .card + .card { margin-top: 16px; }
        .section-title { margin: 0 0 8px 0; font-weight: 800; color: #0f172a; }
        .muted { color: #64748b; font-size: 13px; }
        div[data-testid="stTabs"] > div:first-child {
            background: rgba(255,255,255,0.94);
            padding: 18px;
            border-radius: 18px;
            box-shadow: 0 20px 60px rgba(15,23,42,0.12);
            border: 1px solid #e2e8f0;
        }
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stSelectbox > div > div > select,
        .stFileUploader > div {
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            box-shadow: inset 0 1px 2px rgba(15,23,42,0.05);
        }
        button[kind="secondary"], button[kind="primary"] {
            border-radius: 12px !important;
            font-weight: 700;
        }
        .mission-card {
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 24px;
            border: 2px solid #e2e8f0;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .mission-card:hover {
            border-color: #667eea;
            box-shadow: 0 12px 24px rgba(102, 126, 234, 0.15);
        }
        .mission-badge {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            margin-top: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# FIREBASE INITIALIZATION (기존 유지)
# ============================================================================

@st.cache_resource
def init_firebase():
    """Firebase를 초기화합니다 (캐시됨)"""
    try:
        from firebase_config import initialize_firebase, get_firestore_client, get_storage_bucket
        initialize_firebase()
        return get_firestore_client, get_storage_bucket
    except Exception as e:
        st.error(f"Firebase 초기화 실패: {e}")
        st.stop()

try:
    get_firestore_client, get_storage_bucket = init_firebase()
except Exception:
    pass


# ============================================================================
# AUTHENTICATION (기존 유지)
# ============================================================================

def authenticate_teacher(email, password):
    """Firebase Authentication으로 교사 인증"""
    try:
        import requests
        from firebase_config import get_web_api_key
        
        api_key = get_web_api_key()
        if not api_key:
            return {"success": False, "error": "Firebase API Key를 찾을 수 없습니다."}
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(url, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            return {"success": True, "user_email": data.get("email", email), "user_id": data.get("localId")}
        else:
            error_message = data.get("error", {}).get("message", "로그인 실패")
            error_map = {
                "INVALID_EMAIL": "유효하지 않은 이메일 주소입니다.",
                "INVALID_PASSWORD": "비밀번호가 틀렸습니다.",
                "USER_DISABLED": "비활성화된 사용자입니다.",
                "USER_NOT_FOUND": "등록되지 않은 이메일입니다."
            }
            return {"success": False, "error": error_map.get(error_message, error_message)}
    except Exception as e:
        return {"success": False, "error": f"인증 오류: {str(e)}"}


# ============================================================================
# OPENAI IMAGE GENERATION (새로 추가)
# ============================================================================

def generate_image_with_dalle(word):
    """DALL-E 3를 사용하여 단어의 이미지 생성"""
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Cute cartoon illustration of {word}, simple style, colorful, no text, kid-friendly",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        st.warning(f"이미지 생성 실패: {e}")
        # Fallback 이미지
        return f"https://source.unsplash.com/featured/1024x1024/?{word}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_access_code():
    """6자리 랜덤 숫자 코드 생성"""
    return "".join(random.choices(string.digits, k=6))


def check_access_code_exists(code):
    """Firestore에서 해당 접속 코드가 존재하는지 확인"""
    try:
        db = get_firestore_client()
        doc = db.collection("readfit_assignments").document(code).get()
        return doc.exists, doc.to_dict() if doc.exists else None
    except Exception:
        return False, None


def save_assignment_to_firebase(access_code, unit, difficulty, quiz_data, text):
    """과제를 Firestore에 저장"""
    try:
        db = get_firestore_client()
        assignment = {
            "access_code": access_code,
            "unit": unit,
            "difficulty": difficulty,
            "text": text,
            "quiz": quiz_data,
            "created_at": datetime.now(),
            "status": "active"
        }
        db.collection("readfit_assignments").document(access_code).set(assignment)
        return True
    except Exception as e:
        st.error(f"과제 저장 오류: {e}")
        return False


def logout():
    """로그아웃 처리"""
    st.session_state.clear()
    st.rerun()


# ============================================================================
# YBM 교과서 데이터 (기존 유지)
# ============================================================================

YBM_TEXTBOOK = {
    "Unit 1": {
        "title": "Unit 1 - My Lifelogging",
        "Beginner": "Hi! I am Harin. I like to run. I run in the park every day. The air is fresh and nice. I use a running app on my phone. It shows my speed and time. It also counts my steps. The app helps me a lot. Running makes me happy and healthy. Hello! My name is Mike. I love fashion and clothes. I take photos of my outfits every day. Then I post the pictures on social media. Many people follow me. They like my fashion posts. They write nice things about my clothes. I feel happy when they comment. This is my fashion diary. Hi! I am Elena. I really love donuts. They are so delicious. I go to donut shops on weekends. I use a map app to find good shops. I mark my favorite shops on the map. Then I go there again with my friends. We eat donuts together. Donuts make me very happy. They are my favorite snack. All three of us record our daily activities. We use apps and social media. This is called lifelogging. We share our hobbies with others. It is fun to keep records of what we do. Lifelogging helps us remember good times. We can look back and smile at our memories.",
        "Intermediate": "Hi, everyone! I'm Harin. I am an active person. I exercise a lot. I love running. I often run in the park, and I enjoy the fresh air there. I use a running app. It records my speed, time, and steps. It is very helpful. The app shows me how much I improve each day. I can see my progress over time. Sometimes I share my running records with my friends. They encourage me to keep going. Running is not just exercise for me. It is a way to clear my mind and feel energized. Hello! My name is Mike. I'm very interested in fashion. I take pictures of my clothes. Then, I post them on social media. These pictures are my fashion diary. I have many followers. They love my posts. They leave nice comments, too. Fashion is my passion and my way of expressing myself. Every morning, I choose my outfit carefully. I think about colors, styles, and trends. Taking photos helps me remember what I wore and how I felt that day. My followers give me ideas and feedback. We inspire each other with different fashion styles. My name is Elena. I'm into donuts these days. I visit donut shops in my free time. I mark good shops on my map app. Then, I visit them again with my friends. Donuts are not just a snack for me. They are my happiness! Each donut shop has unique flavors and recipes. I love trying new types of donuts. My map app helps me discover hidden gem shops in the city. When I find a great donut, I feel excited to share it with friends. We talk about the taste, texture, and toppings. These small moments bring us joy.",
        "Advanced": "Greetings, everyone! I am Harin, and I consider myself a highly active individual with a strong commitment to physical fitness."
    },
    "Unit 2": {"title": "Unit 2 - Fun School Events Around the World", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 3": {"title": "Unit 3 - Food and Nutrition", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 4": {"title": "Unit 4 - My Family Tradition", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 5": {"title": "Unit 5 - Sports and Physical Activity", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 6": {"title": "Unit 6 - Hobbies and Leisure Activities", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 7": {"title": "Unit 7 - Travel and Exploring the World", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."},
    "Unit 8": {"title": "Unit 8 - Career and Professional Life", "Beginner": "Sample text...", "Intermediate": "Sample text...", "Advanced": "Sample text..."}
}


# ============================================================================
# QUIZ GENERATION
# ============================================================================

def generate_quiz_questions(unit):
    """해당 Unit의 간단한 퀴즈 문제 생성"""
    quiz_templates = {
        "Unit 1": [
            {"question": "What is Harin's hobby?", "options": ["Running", "Swimming", "Dancing"], "answer": 0},
            {"question": "What does Mike do on social media?", "options": ["Posts food pictures", "Posts outfit pictures", "Posts travel photos"], "answer": 1},
            {"question": "What does Elena love?", "options": ["Cooking", "Donuts", "Shopping"], "answer": 1}
        ],
        "Unit 2": [
            {"question": "Where is Cross Country Race Day held?", "options": ["Philippines", "New Zealand", "USA"], "answer": 1},
            {"question": "How many languages are there in the Philippines?", "options": ["50", "100", "150"], "answer": 1},
            {"question": "What musical instrument does the student play?", "options": ["Guitar", "Piano", "Violin"], "answer": 2}
        ],
        "Unit 3": [
            {"question": "What is important for our health?", "options": ["Candy", "Food", "Soda"], "answer": 1},
            {"question": "How much water should we drink daily?", "options": ["4 glasses", "8 glasses", "12 glasses"], "answer": 1},
            {"question": "What makes our bones strong?", "options": ["Sugar", "Calcium", "Salt"], "answer": 1}
        ],
        "Unit 4": [
            {"question": "What is Yubin's father's origin?", "options": ["Korea", "India", "Japan"], "answer": 1},
            {"question": "When do they visit the baseball park?", "options": ["Winter", "Spring", "Summer"], "answer": 1},
            {"question": "What game do they play after dinner?", "options": ["Chess", "Pachisi", "Go"], "answer": 1}
        ]
    }
    return quiz_templates.get(unit, quiz_templates["Unit 1"])


# ============================================================================
# TEACHER DASHBOARD
# ============================================================================

def show_teacher_dashboard():
    """교사 대시보드"""
    st.header("👨‍🏫 교사 대시보드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 새 과제 생성")
        
        unit = st.selectbox("Unit 선택", ["Unit 1", "Unit 2", "Unit 3", "Unit 4"])
        difficulty = st.radio("난이도 선택", ["상", "중", "하"])
        
        if st.button("🚀 과제 생성 및 배포", use_container_width=True):
            # 접속 코드 생성
            access_code = generate_access_code()
            
            # 퀴즈 데이터 생성
            quiz_data = generate_quiz_questions(unit)
            
            # 텍스트 가져오기
            difficulty_map = {"상": "Advanced", "중": "Intermediate", "하": "Beginner"}
            text = YBM_TEXTBOOK.get(unit, {}).get(difficulty_map[difficulty], "Sample text")
            
            # Firestore에 저장
            if save_assignment_to_firebase(access_code, unit, difficulty, quiz_data, text):
                st.success(f"✅ 과제가 생성되었습니다!")
                st.info(f"**학생 접속 코드: {access_code}**")
            else:
                st.error("과제 생성 실패")
    
    with col2:
        st.subheader("📊 배포된 과제")
        st.write("*배포된 과제 목록은 여기에 표시됩니다.*")


# ============================================================================
# STUDENT WORKSPACE - 4 STEP FLOW
# ============================================================================

def show_step1_quiz(assignment):
    """Step 1: 퀴즈 풀기"""
    st.header("Step 1️⃣ 퀴즈 풀기")
    
    st.subheader("📖 지문")
    st.text_area("지문 내용", value=assignment["text"], height=150, disabled=True)
    
    st.divider()
    st.subheader("❓ 문제")
    
    quiz_data = assignment["quiz"]
    answers = []
    
    for idx, q in enumerate(quiz_data):
        st.write(f"**{idx + 1}. {q['question']}**")
        answer = st.radio("정답을 선택하세요", q["options"], key=f"quiz_{idx}")
        answers.append(q["options"].index(answer))
    
    if st.button("✅ 정답 제출", use_container_width=True):
        score = sum(1 for i, q in enumerate(quiz_data) if answers[i] == q["answer"]) / len(quiz_data) * 100
        st.session_state.quiz_score = int(score)
        st.session_state.step = 2
        st.rerun()


def show_step2_mission_selection(quiz_score):
    """Step 2: 미션 선택"""
    st.header("Step 2️⃣ 미션 선택")
    
    # 점수 표시
    st.info(f"🎯 당신의 퀴즈 점수: **{quiz_score}점**")
    
    missions = [
        {
            "id": "image_detective",
            "title": "🎨 이미지 탐정",
            "difficulty": "하",
            "description": "그림을 보고 단어를 맞춰보세요!",
            "emoji": "🎨"
        },
        {
            "id": "mystery_20_questions",
            "title": "🕵️ 미스터리 스무고개",
            "difficulty": "중",
            "description": "AI의 힌트를 듣고 단어를 추리하세요!",
            "emoji": "🕵️"
        },
        {
            "id": "writer",
            "title": "✍️ 베스트셀러 작가",
            "difficulty": "상",
            "description": "뒷이야기를 상상해서 써보세요!",
            "emoji": "✍️"
        }
    ]
    
    # 난이도 추천 로직
    if quiz_score >= 80:
        recommended = 2  # 작가
    elif quiz_score >= 60:
        recommended = 1  # 스무고개
    else:
        recommended = 0  # 이미지 탐정
    
    cols = st.columns(3)
    
    for idx, mission in enumerate(missions):
        with cols[idx]:
            st.markdown(f"""
            <div class="mission-card">
                <div style="font-size: 40px; margin-bottom: 10px;">{mission['emoji']}</div>
                <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">{mission['title']}</div>
                <div style="color: #666; font-size: 14px; margin-bottom: 10px;">{mission['description']}</div>
                <div style="color: #999; font-size: 12px;">난이도: {mission['difficulty']}</div>
            """, unsafe_allow_html=True)
            
            if idx == recommended:
                st.markdown('<div class="mission-badge">👍 AI 추천</div>', unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("이 미션 선택하기", key=f"mission_{idx}", use_container_width=True):
                st.session_state.selected_mission = mission["id"]
                st.session_state.mission_title = mission["title"]
                st.session_state.step = 3
                st.rerun()


def show_step3_image_detective(assignment):
    """Step 3: 이미지 탐정 활동"""
    st.header("Step 3️⃣ 활동 수행")
    st.subheader("🎨 이미지 탐정")
    st.write("**AI가 그린 그림을 보고 단어를 맞춰보세요!**")
    
    # 세션 초기화
    if "detective_word" not in st.session_state:
        st.session_state.detective_word = None
        st.session_state.detective_image = None
        st.session_state.detective_options = []
    
    # 단어 및 이미지 생성
    if st.session_state.detective_word is None:
        # 지문에서 간단한 영어 단어 추출
        sample_words = ["astronaut", "dog", "cat", "tree", "house", "car", "sun", "moon", "flower", "bird", "book", "apple", "hat", "shoes", "bicycle"]
        selected_word = random.choice(sample_words)
        st.session_state.detective_word = selected_word
        
        # 보기 생성
        wrong_words = [w for w in sample_words if w != selected_word]
        random.shuffle(wrong_words)
        options = [selected_word] + wrong_words[:3]
        random.shuffle(options)
        st.session_state.detective_options = options
        
        # DALL-E 이미지 생성
        with st.spinner("🤖 AI가 그림을 그리고 있어요..."):
            image_url = generate_image_with_dalle(selected_word)
            st.session_state.detective_image = image_url
    
    # 이미지 표시
    if st.session_state.detective_image:
        st.image(st.session_state.detective_image, caption="이 그림이 무엇일까요?", use_container_width=True)
    
    st.write("**아래 버튼 중 정답을 선택하세요:**")
    
    # 4개 선택지 버튼
    cols = st.columns(4)
    for idx, option in enumerate(st.session_state.detective_options):
        with cols[idx]:
            if st.button(f"**{option}**", key=f"detect_{idx}", use_container_width=True):
                if option == st.session_state.detective_word:
                    st.session_state.activity_score = 100
                    st.success("🎉 정답입니다!")
                else:
                    st.session_state.activity_score = 30
                    st.error(f"❌ 틀렸습니다. 정답은 '{st.session_state.detective_word}'입니다.")
                
                # 초기화 및 다음 단계
                st.session_state.detective_word = None
                st.session_state.detective_image = None
                st.session_state.detective_options = []
                st.session_state.step = 4
                st.rerun()


def show_step3_mystery_questions():
    """Step 3: 미스터리 스무고개"""
    st.header("Step 3️⃣ 활동 수행")
    st.subheader("🕵️ 미스터리 스무고개")
    st.write("**AI의 힌트를 듣고 단어를 추리하세요!**")
    
    with st.expander("💬 AI 힌트 보기"):
        st.write("• 이것은 동물입니다.")
        st.write("• 이것은 4개의 다리가 있습니다.")
        st.write("• 이것은 개입니다.")
    
    answer = st.text_input("정답을 입력하세요:", key="mystery_answer")
    
    if st.button("✅ 정답 제출", use_container_width=True):
        if answer.lower() == "dog":
            st.session_state.activity_score = 90
            st.success("🎉 정답입니다!")
        else:
            st.session_state.activity_score = 40
            st.error("❌ 틀렸습니다. 정답은 'dog'입니다.")
        
        st.session_state.step = 4
        st.rerun()


def show_step3_story_writer():
    """Step 3: 베스트셀러 작가"""
    st.header("Step 3️⃣ 활동 수행")
    st.subheader("✍️ 베스트셀러 작가")
    st.write("**뒷이야기를 상상해서 써보세요!**")
    st.caption("(200자 이상 작성 권장)")
    
    story = st.text_area("이야기 작성", height=200, placeholder="뒷이야기를 입력하세요...", key="writer_story")
    
    if st.button("✅ 작품 제출", use_container_width=True):
        if len(story.strip()) > 0:
            st.session_state.activity_score = 85
            st.success("🎉 작품이 제출되었습니다!")
            st.session_state.step = 4
            st.rerun()
        else:
            st.error("최소 1자 이상 작성해주세요.")


def show_step4_report(quiz_score, activity_score, mission_title):
    """Step 4: 최종 리포트"""
    st.header("Step 4️⃣ 최종 리포트")
    
    total_score = int(quiz_score * 0.4 + activity_score * 0.6)
    
    # 점수 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 퀴즈 점수", f"{quiz_score}점")
    with col2:
        st.metric("🎯 활동 점수", f"{activity_score}점")
    with col3:
        st.metric("⭐ 최종 점수", f"{total_score}점")
    
    st.divider()
    
    # 칭호 생성
    titles = {
        100: "🏆 완벽한 마스터",
        90: "🥇 매의 눈을 가진 탐정",
        80: "🥈 뛰어난 학습자",
        70: "🥉 열심히 하는 학생",
        60: "📚 성장하는 독서왕",
        0: "🌟 재도전 중인 별"
    }
    
    title = next((v for k, v in sorted(titles.items(), reverse=True) if total_score >= k), "🌟 재도전 중인 별")
    
    st.markdown(f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 16px; color: white; margin: 20px 0;">
        <div style="font-size: 60px; margin-bottom: 10px;">🎉</div>
        <div style="font-size: 28px; font-weight: bold; margin-bottom: 10px;">학습 완료!</div>
        <div style="font-size: 20px; margin-bottom: 10px;">오늘의 칭호</div>
        <div style="font-size: 24px; font-weight: bold;">{title}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # AI 피드백
    st.subheader("📊 오늘의 학습 요약")
    feedback = f"""
    아주 잘했어요! 당신은 '{mission_title}' 미션을 완료했습니다. 
    
    총 점수 {total_score}점을 획득했습니다. 계속 열심히 공부하면 더 좋은 결과를 얻을 수 있을 거예요!
    
    - 퀴즈 점수: {quiz_score}점
    - 활동 점수: {activity_score}점
    """
    st.info(feedback)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 메인으로 돌아가기", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    with col2:
        if st.button("🔄 다시 풀기", use_container_width=True):
            st.session_state.step = 1
            st.rerun()


# ============================================================================
# STUDENT WORKSPACE
# ============================================================================

def show_student_workspace(assignment):
    """학생 워크스페이스 - 4 Step Flow"""
    apply_global_styles()
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="font-size: 24px; font-weight: bold;">📚 ReadFit</div>
        <div style="color: #666; font-size: 14px;">Unit: {assignment['unit']} | 난이도: {assignment['difficulty']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "quiz_score" not in st.session_state:
        st.session_state.quiz_score = 0
    if "activity_score" not in st.session_state:
        st.session_state.activity_score = 0
    
    # Step 진행 표시
    st.progress(st.session_state.step / 4, f"Step {st.session_state.step}/4")
    
    if st.session_state.step == 1:
        show_step1_quiz(assignment)
    elif st.session_state.step == 2:
        show_step2_mission_selection(st.session_state.quiz_score)
    elif st.session_state.step == 3:
        if st.session_state.selected_mission == "image_detective":
            show_step3_image_detective(assignment)
        elif st.session_state.selected_mission == "mystery_20_questions":
            show_step3_mystery_questions()
        elif st.session_state.selected_mission == "writer":
            show_step3_story_writer()
    elif st.session_state.step == 4:
        show_step4_report(st.session_state.quiz_score, st.session_state.activity_score, st.session_state.mission_title)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """메인 앱"""
    apply_global_styles()
    
    # 초기 세션 상태
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    
    # 로그인 전
    if st.session_state.user_role is None:
        st.markdown("<div class='login-hero'><h1>📚 ReadFit</h1></div>", unsafe_allow_html=True)
        st.markdown("<div class='login-sub'>영어 학습 플랫폼 - 퀴즈 & 미션으로 영어 실력 UP!</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
        
        with col2:
            tab1, tab2 = st.tabs(["👨‍🏫 교사 로그인", "👨‍🎓 학생 입장"])
            
            # 교사 로그인
            with tab1:
                st.markdown("<div class='section-title'>교사 계정으로 로그인</div>", unsafe_allow_html=True)
                
                teacher_email = st.text_input("📧 이메일", placeholder="teacher@example.com")
                teacher_password = st.text_input("🔑 비밀번호", type="password")
                
                if st.button("로그인", use_container_width=True, key="teacher_login"):
                    if teacher_email and teacher_password:
                        result = authenticate_teacher(teacher_email, teacher_password)
                        if result["success"]:
                            st.session_state.user_role = "teacher"
                            st.session_state.user_email = result["user_email"]
                            st.rerun()
                        else:
                            st.error(result["error"])
                    else:
                        st.error("이메일과 비밀번호를 입력하세요.")
            
            # 학생 입장
            with tab2:
                st.markdown("<div class='section-title'>학생 접속</div>", unsafe_allow_html=True)
                
                access_code = st.text_input("🔐 접속 코드 입력", placeholder="6자리 숫자")
                
                if st.button("입장하기", use_container_width=True, key="student_login"):
                    if access_code:
                        exists, assignment = check_access_code_exists(access_code)
                        if exists:
                            st.session_state.user_role = "student"
                            st.session_state.access_code = access_code
                            st.session_state.assignment = assignment
                            st.rerun()
                        else:
                            st.error("❌ 유효하지 않은 접속 코드입니다.")
                    else:
                        st.error("접속 코드를 입력하세요.")
    
    # 로그인 후
    else:
        if st.session_state.user_role == "teacher":
            col1, col2 = st.columns([10, 1])
            with col2:
                if st.button("🚪", help="로그아웃"):
                    logout()
            
            show_teacher_dashboard()
        
        elif st.session_state.user_role == "student":
            col1, col2 = st.columns([10, 1])
            with col2:
                if st.button("🚪", help="종료"):
                    logout()
            
            show_student_workspace(st.session_state.assignment)


if __name__ == "__main__":
    main()
