"""
영어 학습용 쉐도잉 & 퀴즈 플랫폼
Streamlit + Firebase를 활용한 인터랙티브 영어 학습 도구
"""

import streamlit as st
import random
import string
from datetime import datetime
from io import BytesIO
import json


# ==========================================================================
# GLOBAL STYLES
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
        /* 헤더 중앙 정렬 */
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
        /* 로그인 탭 컨테이너 카드화 */
        div[data-testid="stTabs"] > div:first-child {
            background: rgba(255,255,255,0.94);
            padding: 18px;
            border-radius: 18px;
            box-shadow: 0 20px 60px rgba(15,23,42,0.12);
            border: 1px solid #e2e8f0;
        }
        /* 입력 및 버튼 공통 */
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
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# 0. YBM 교과서 데이터
# ============================================================================

# YBM 교과서 단원별 지문 데이터 (난이도별)
YBM_TEXTBOOK = {
    "Unit 1": {
        "title": "Unit 1 - Greeting",
        "Beginner": "Hello! My name is John. I am from New York. Nice to meet you. How are you today? I am fine, thank you. What is your name? Where are you from?",
        "Intermediate": "Good morning, everyone! My name is John Smith and I come from New York City. I'm delighted to make your acquaintance. How are you doing today? I'm doing quite well, thank you for asking. What might your name be? And which country do you hail from?",
        "Advanced": "Allow me to introduce myself - I am John Smith, a native of New York City with a background in international business. I am absolutely delighted to make your acquaintance today. I trust you are doing exceptionally well? I am doing remarkably well, thank you sincerely for your inquiry. Might I have the pleasure of knowing your name? And perhaps, from which country do you originate?"
    },
    "Unit 2": {
        "title": "Unit 2 - Family",
        "Beginner": "I have a family. I have a mother and a father. I have one brother and one sister. My mother is a teacher. My father is a doctor. We live together in a big house. We are happy.",
        "Intermediate": "I come from a close-knit family. My family consists of my mother, who is a dedicated teacher, and my father, who works as a doctor. Additionally, I have one brother and one sister. We all live together in a spacious house in the suburbs. Our family shares many wonderful moments together.",
        "Advanced": "I originate from a closely knit family unit comprising my mother, an accomplished educator, and my father, who practices medicine as a physician. I have one brother and one sister with whom I share familial bonds. Our household is situated in a spacious residence in the suburban area. We maintain harmonious relationships and frequently engage in meaningful family interactions."
    },
    "Unit 3": {
        "title": "Unit 3 - Food",
        "Beginner": "I like to eat many kinds of food. I like rice and bread. I like chicken and fish. I like vegetables and fruit. I eat breakfast, lunch, and dinner. I drink milk and water. What do you like to eat?",
        "Intermediate": "I have a diverse palate and enjoy consuming a wide variety of foods. I particularly enjoy rice and bread as staple foods. I also like chicken and fish as protein sources. Additionally, I appreciate vegetables and fruits for their nutritional value. I have three meals daily - breakfast, lunch, and dinner. I also consume milk and water regularly.",
        "Advanced": "I possess an eclectic taste in cuisine and appreciate the consumption of an extensive array of comestibles. I have a particular predilection for rice and bread as foundational carbohydrates. I also exhibit a preference for poultry and fish as protein sources. Furthermore, I appreciate the nutritional and gustatory benefits of vegetables and fruits. I maintain a structured eating schedule with breakfast, lunch, and dinner. Additionally, I consume dairy products and water for hydration."
    },
    "Unit 4": {
        "title": "Unit 4 - School",
        "Beginner": "I go to school every day. I study English, math, and science. My teachers are kind and helpful. I have many friends at school. We play together at lunch time. School is fun and interesting.",
        "Intermediate": "I attend school on a daily basis. Throughout my academic day, I study several subjects including English, mathematics, and science. My teachers are exceptionally kind and always willing to provide assistance. I have made numerous friends at school with whom I interact regularly. During lunch breaks, we enjoy playing games and socializing together. Overall, school provides me with an engaging and intellectually stimulating environment.",
        "Advanced": "I maintain regular attendance at an educational institution where I engage in the study of multiple disciplines including English language arts, mathematics, and natural sciences. My pedagogical instructors demonstrate remarkable kindness and demonstrate unwavering commitment to educational assistance. I have cultivated substantive friendships with numerous peers within the academic setting. During designated lunch periods, we engage in recreational activities and social interactions. The educational experience proves to be both intellectually engaging and profoundly enriching."
    },
    "Unit 5": {
        "title": "Unit 5 - Sports",
        "Beginner": "I like sports very much. I play soccer with my friends. I also like basketball and tennis. I exercise three times a week. Exercise is good for my health. I run in the park every morning.",
        "Intermediate": "I have a strong passion for sports and athletic activities. I regularly play soccer with my friends on weekends. I also enjoy basketball and tennis as recreational pursuits. I maintain a consistent exercise routine three times per week. Physical activity is beneficial for my overall health and wellness. I go for runs in the park every morning as part of my fitness regimen.",
        "Advanced": "I maintain an ardent enthusiasm for sports and athletic endeavors. I engage in soccer matches with my companions on a regular basis during weekends. I also cultivate an appreciation for basketball and tennis as avocational pursuits. I adhere to a disciplined exercise schedule, maintaining physical activity thrice weekly. Regular physical exertion provides substantial benefits to my comprehensive health and physiological well-being. I undertake morning constitutional runs through the municipal park as an integral component of my fitness program."
    },
    "Unit 6": {
        "title": "Unit 6 - Hobbies",
        "Beginner": "My hobby is reading books. I like to read stories about animals. I read every day before bed. Reading is fun and relaxing. I also like drawing pictures. I draw my favorite animals in my notebook.",
        "Intermediate": "My primary hobby is reading literature, particularly novels about adventure and exploration. I dedicate considerable time to reading every evening before retiring. Reading provides me with both entertainment and relaxation. I also enjoy painting and sketching, which allows me to express my creativity. I maintain a collection of my artwork that I am quite proud of.",
        "Advanced": "My principal avocation encompasses the perusal of contemporary literature, with particular emphasis on novels exploring philosophical themes and cultural narratives. I engage in this intellectual pursuit quotidian, deriving substantial gratification from the literary experience. Additionally, I cultivate an appreciation for visual arts, including watercolor painting and pencil sketching. These artistic endeavors facilitate profound self-expression and cognitive development."
    },
    "Unit 7": {
        "title": "Unit 7 - Travel",
        "Beginner": "I love to travel. I like visiting new places. Last summer, I went to Tokyo. It was very beautiful. I visited temples and parks. I ate delicious food. I want to travel again next year.",
        "Intermediate": "I have a genuine passion for traveling and exploring diverse destinations. Last summer, I had the opportunity to visit Tokyo, which proved to be an absolutely captivating experience. I explored historical temples, visited serene gardens, and sampled authentic Japanese cuisine. The cultural richness of the experience has motivated my desire to undertake further travels in the coming years.",
        "Advanced": "I maintain an ardent enthusiasm for international travel and cultural exploration. During my preceding summer excursion to Tokyo, I engaged in comprehensive exploration of historical temples, meticulously maintained gardens, and gastronomic establishments featuring traditional Japanese cuisine. The profound cultural immersion facilitated extensive personal enrichment and intellectual stimulation, thereby invigorating my determination to pursue subsequent international expeditions."
    },
    "Unit 8": {
        "title": "Unit 8 - Career",
        "Beginner": "When I grow up, I want to be a doctor. Doctors help people. They work in hospitals. They study hard in school. I like science class. I want to help sick people and make them healthy.",
        "Intermediate": "My aspiration is to pursue a career in medicine upon completing my education. Medical professionals play a vital role in society by providing healthcare services and improving patient outcomes. The field requires rigorous academic preparation and specialized training. I am particularly interested in pediatric medicine, as it allows me to work directly with children and their families.",
        "Advanced": "My professional aspirations center upon the pursuit of a career in medical science, specifically within the field of pediatric oncology. This specialization would facilitate my contribution to advancing therapeutic interventions for critically ill pediatric patients. The discipline necessitates extensive academic preparation, including undergraduate studies, medical school, residency training, and specialized fellowship programs. I am committed to acquiring the requisite expertise to address complex healthcare challenges in this specialized domain."
    }
}

# AI 자동 퀴즈 생성 함수
def generate_ai_quiz(text_content, unit_title, difficulty):
    """
    지문을 기반으로 AI가 자동으로 3가지 유형의 퀴즈를 생성합니다.
    1. 요약 문제 (Summary)
    2. 주제 추론 (Theme Inference)
    3. 제목 추론 (Title Inference)
    """
    
    # 난이도별 질문 수준 조정
    difficulty_level = "초급" if "Beginner" in difficulty else "중급" if "Intermediate" in difficulty else "고급"
    
    # 단원별 기본 정보 추출
    unit_num = unit_title.split()[0]  # "Unit 1" 같은 형식에서 "Unit"
    topic = unit_title.split("-")[1].strip() if "-" in unit_title else "Topic"
    
    # 1. 요약 문제 (Summary)
    summary_questions = {
        "Unit 1 - Greeting": {
            "Beginner": "이 지문의 주요 내용은 무엇입니까?",
            "Intermediate": "지문에서 설명하는 인사의 중요성을 요약하시오.",
            "Advanced": "지문의 핵심 메시지를 한 문장으로 요약하고, 그 의미를 설명하시오."
        },
        "Unit 2 - Family": {
            "Beginner": "가족 구성원들이 어떤 일을 하는지 설명하세요.",
            "Intermediate": "지문에서 가족 관계가 어떻게 묘사되는지 요약하세요.",
            "Advanced": "가족의 역할과 관계의 중요성을 지문을 바탕으로 분석하세요."
        },
        "Unit 3 - Food": {
            "Beginner": "어떤 음식들이 언급되었나요?",
            "Intermediate": "지문에서 식습관에 대해 설명하는 내용을 요약하시오.",
            "Advanced": "음식과 건강의 관계를 지문의 내용으로 설명하시오."
        },
        "Unit 4 - School": {
            "Beginner": "학교에서 하는 활동들을 설명하세요.",
            "Intermediate": "학교 환경이 어떻게 묘사되는지 요약하세요.",
            "Advanced": "교육 경험의 가치를 지문을 바탕으로 분석하세요."
        },
        "Unit 5 - Sports": {
            "Beginner": "어떤 스포츠들이 언급되었나요?",
            "Intermediate": "운동이 건강에 미치는 영향에 대해 설명하세요.",
            "Advanced": "신체활동의 다양한 이점을 지문의 내용으로 분석하세요."
        },
        "Unit 6 - Hobbies": {
            "Beginner": "어떤 취미활동들이 소개되었나요?",
            "Intermediate": "취미활동이 개인에게 어떤 의미를 갖는지 설명하세요.",
            "Advanced": "취미가 자아 발견과 창의성에 미치는 영향을 분석하세요."
        },
        "Unit 7 - Travel": {
            "Beginner": "어디로 여행을 갔습니까?",
            "Intermediate": "여행의 의미와 영향에 대해 설명하세요.",
            "Advanced": "문화 교류와 개인 성장의 관점에서 여행의 가치를 분석하세요."
        },
        "Unit 8 - Career": {
            "Beginner": "어떤 직업을 소개하고 있나요?",
            "Intermediate": "선택된 직업의 특징과 필요성에 대해 설명하세요.",
            "Advanced": "전문 직업 선택의 동기와 사회적 책임을 분석하세요."
        }
    }
    
    # 2. 주제 추론 문제 (Theme Inference)
    theme_questions = {
        "Unit 1 - Greeting": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "지문이 전달하려는 사회적 메시지는 무엇입니까?",
            "Advanced": "인간관계 형성의 기초가 되는 커뮤니케이션의 중요성을 파악하시오."
        },
        "Unit 2 - Family": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "가족의 역할과 중요성에 대한 저자의 관점을 파악하세요.",
            "Advanced": "가족 관계에서 도출할 수 있는 사회적, 심리적 의미를 추론하세요."
        },
        "Unit 3 - Food": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "음식과 건강의 관계에 대한 관점을 추론하세요.",
            "Advanced": "음식 문화와 라이프스타일의 상관관계를 분석하세요."
        },
        "Unit 4 - School": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "학교가 학생 개인에게 갖는 의미를 추론하세요.",
            "Advanced": "교육 기관이 사회에서 수행하는 역할을 비판적으로 분석하세요."
        },
        "Unit 5 - Sports": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "운동이 개인의 삶에서 갖는 중요성을 추론하세요.",
            "Advanced": "신체활동과 정신 건강의 상호 관계를 분석하세요."
        },
        "Unit 6 - Hobbies": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "취미 활동이 삶의 질에 미치는 영향을 추론하세요.",
            "Advanced": "개인의 예술 활동이 자아 정체성 형성에 미치는 역할을 분석하세요."
        },
        "Unit 7 - Travel": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "여행이 개인에게 갖는 의미를 추론하세요.",
            "Advanced": "국제 여행 경험이 세계관 형성에 미치는 영향을 분석하세요."
        },
        "Unit 8 - Career": {
            "Beginner": "이 지문의 주제는 무엇입니까?",
            "Intermediate": "직업 선택의 동기와 목표를 추론하세요.",
            "Advanced": "개인의 전문 활동과 사회 기여의 관계를 분석하세요."
        }
    }
    
    # 3. 제목 추론 문제 (Title Inference)
    title_questions = {
        "Unit 1 - Greeting": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "이 지문의 내용을 가장 잘 나타내는 제목을 작성하세요.",
            "Advanced": "지문의 함축적 의미를 반영한 창의적인 제목을 제시하고 그 이유를 설명하세요."
        },
        "Unit 2 - Family": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "가족의 구조와 역할을 반영하는 제목을 작성하세요.",
            "Advanced": "현대 가족의 특성을 포함한 깊이 있는 제목을 제시하고 근거를 제시하세요."
        },
        "Unit 3 - Food": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "음식 문화와 건강을 반영하는 제목을 작성하세요.",
            "Advanced": "음식과 생활 방식의 관계를 나타내는 의미 깊은 제목을 제시하세요."
        },
        "Unit 4 - School": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "학교의 역할과 의미를 반영하는 제목을 작성하세요.",
            "Advanced": "교육의 사회적 가치를 드러내는 철학적 제목을 제시하세요."
        },
        "Unit 5 - Sports": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "운동의 신체적, 정신적 이점을 반영하는 제목을 작성하세요.",
            "Advanced": "스포츠의 사회적, 문화적 의미를 포함한 제목을 제시하세요."
        },
        "Unit 6 - Hobbies": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "취미 활동의 의미와 가치를 반영하는 제목을 작성하세요.",
            "Advanced": "예술과 자아 발견의 관계를 나타내는 창의적인 제목을 제시하세요."
        },
        "Unit 7 - Travel": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "여행 경험과 개인 성장을 반영하는 제목을 작성하세요.",
            "Advanced": "문화 교류와 세계 시민 의식을 나타내는 제목을 제시하세요."
        },
        "Unit 8 - Career": {
            "Beginner": "이 지문에 가장 적합한 제목은 무엇입니까?",
            "Intermediate": "직업 선택의 동기와 목표를 반영하는 제목을 작성하세요.",
            "Advanced": "전문직과 사회 봉사의 관계를 나타내는 제목을 제시하세요."
        }
    }
    
    # 난이도별 문제 선택
    difficulty_label = "Beginner" if "Beginner" in difficulty else "Intermediate" if "Intermediate" in difficulty else "Advanced"
    
    summary_q = summary_questions.get(unit_title, {}).get(difficulty_label, "이 지문의 주요 내용을 요약하세요.")
    theme_q = theme_questions.get(unit_title, {}).get(difficulty_label, "이 지문의 주제는 무엇입니까?")
    title_q = title_questions.get(unit_title, {}).get(difficulty_label, "이 지문에 가장 적합한 제목은 무엇입니까?")
    
    return {
        "summary": {
            "type": "📝 요약 문제 (Summary)",
            "question": summary_q
        },
        "theme": {
            "type": "🎯 주제 추론 (Theme Inference)",
            "question": theme_q
        },
        "title": {
            "type": "📋 제목 추론 (Title Inference)",
            "question": title_q
        }
    }


# ============================================================================
# 1. PAGE CONFIG & INITIALIZATION
# ============================================================================

st.set_page_config(
    page_title="AI English Learning Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State 초기화
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None  # "teacher" or "student"
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "current_access_code" not in st.session_state:
    st.session_state.current_access_code = None


# ============================================================================
# 2. FIREBASE INITIALIZATION (Lazy Loading)
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

# Firebase 초기화
try:
    get_firestore_client, get_storage_bucket = init_firebase()
except Exception:
    pass


# ============================================================================
# 3. UTILITY FUNCTIONS
# ============================================================================

def authenticate_teacher(email, password):
    """
    Firebase Authentication으로 교사 인증
    """
    try:
        import requests
        from firebase_config import get_web_api_key
        
        api_key = get_web_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "Firebase API Key를 찾을 수 없습니다."
            }
        
        # Firebase Authentication REST API 사용
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "success": True,
                "user_email": data.get("email", email),
                "user_id": data.get("localId")
            }
        else:
            error_message = data.get("error", {}).get("message", "로그인 실패")
            
            # Firebase 에러 메시지 매핑
            error_map = {
                "INVALID_EMAIL": "유효하지 않은 이메일 주소입니다.",
                "INVALID_PASSWORD": "비밀번호가 틀렸습니다.",
                "USER_DISABLED": "비활성화된 사용자입니다.",
                "USER_NOT_FOUND": "등록되지 않은 이메일입니다."
            }
            
            friendly_error = error_map.get(error_message, error_message)
            
            return {
                "success": False,
                "error": friendly_error
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"인증 오류: {str(e)}"
        }


def generate_access_code():
    """6자리 랜덤 숫자 코드 생성"""
    return "".join(random.choices(string.digits, k=6))


def check_access_code_exists(code):
    """Firestore에서 해당 접속 코드가 존재하는지 확인"""
    try:
        db = get_firestore_client()
        doc = db.collection("assignments").document(code).get()
        return doc.exists
    except Exception as e:
        st.error(f"데이터베이스 오류: {e}")
        return False


def get_assignment_data(code):
    """Firestore에서 과제 데이터 조회"""
    try:
        db = get_firestore_client()
        doc = db.collection("assignments").document(code).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        st.error(f"과제 데이터 조회 오류: {e}")
        return None


def save_assignment(code, data):
    """Firestore에 과제 저장"""
    try:
        db = get_firestore_client()
        data["created_at"] = datetime.now()
        db.collection("assignments").document(code).set(data)
        return True
    except Exception as e:
        st.error(f"과제 저장 오류: {e}")
        return False


def upload_audio_to_storage(audio_bytes, access_code, student_name):
    """Firebase Storage에 오디오 파일 업로드"""
    try:
        bucket = get_storage_bucket()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{student_name}_{timestamp}.wav"
        blob_path = f"student_audio/{access_code}/{filename}"
        
        blob = bucket.blob(blob_path)
        blob.upload_from_string(audio_bytes, content_type="audio/wav")
        
        # 다운로드 URL 생성
        url = blob.public_url
        return url, filename
    except Exception as e:
        st.error(f"오디오 업로드 오류: {e}")
        return None, None


def save_submission(access_code, student_name, audio_url, audio_filename, score=0):
    """Firestore submissions 컬렉션에 제출 데이터 저장"""
    try:
        db = get_firestore_client()
        submission_data = {
            "access_code": access_code,
            "student_name": student_name,
            "audio_url": audio_url,
            "audio_filename": audio_filename,
            "submitted_at": datetime.now(),
            "score": score
        }
        db.collection("submissions").add(submission_data)
        return True
    except Exception as e:
        st.error(f"제출 저장 오류: {e}")
        return False


def get_all_assignment_codes():
    """모든 과제 코드 조회"""
    try:
        db = get_firestore_client()
        docs = db.collection("assignments").stream()
        codes = [doc.id for doc in docs]
        return codes
    except Exception as e:
        st.error(f"과제 코드 조회 오류: {e}")
        return []


def get_submissions_for_code(code):
    """특정 코드의 모든 제출 데이터 조회"""
    try:
        db = get_firestore_client()
        submissions = []
        docs = db.collection("submissions").where(
            "access_code", "==", code
        ).stream()
        
        for doc in docs:
            submissions.append(doc.to_dict())
        
        return submissions
    except Exception as e:
        st.error(f"제출 데이터 조회 오류: {e}")
        return []


def logout():
    """로그아웃 처리"""
    st.session_state.clear()
    st.rerun()


# ============================================================================
# 3. LOGIN PAGE
# ============================================================================

def show_login_page():
    """로그인 페이지 표시"""
    apply_global_styles()
    
    st.markdown("<div class='login-hero'><h1>📚 AI English Learning Platform</h1></div>", unsafe_allow_html=True)
    st.markdown("<div class='login-sub'>AI 평가 지문 생성 & 퀴즈 마스터</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    
    with col2:
        tab1, tab2 = st.tabs(["🎓 교사 로그인", "👨‍🎓 학생 입장"])
        
        # ===== 교사 로그인 탭 =====
        with tab1:
            st.subheader("교사 로그인")
            teacher_email = st.text_input("이메일", key="teacher_email", placeholder="teacher@example.com")
            teacher_pw = st.text_input("비밀번호", type="password", key="teacher_pw")
            
            if st.button("로그인", key="teacher_login_btn", use_container_width=True):
                if not teacher_email.strip():
                    st.error("이메일을 입력해주세요.")
                elif not teacher_pw.strip():
                    st.error("비밀번호를 입력해주세요.")
                else:
                    try:
                        # Firebase Authentication으로 로그인
                        auth_result = authenticate_teacher(teacher_email, teacher_pw)
                        
                        if auth_result["success"]:
                            st.session_state.is_logged_in = True
                            st.session_state.user_role = "teacher"
                            st.session_state.user_name = auth_result["user_email"]
                            st.success("교사 로그인 성공!")
                            st.rerun()
                        else:
                            st.error(auth_result["error"])
                    except Exception as e:
                        st.error(f"로그인 오류: {str(e)}")
        
        # ===== 학생 입장 탭 =====
        with tab2:
            st.subheader("학생 입장")
            student_name = st.text_input("이름", key="student_name")
            access_code = st.text_input("학습 코드 (6자리 숫자)", key="access_code_input")
            
            if st.button("입장하기", key="student_login_btn", use_container_width=True):
                if not student_name.strip():
                    st.error("이름을 입력해주세요.")
                elif not access_code.strip():
                    st.error("학습 코드를 입력해주세요.")
                elif not access_code.isdigit() or len(access_code) != 6:
                    st.error("학습 코드는 6자리 숫자여야 합니다.")
                else:
                    # Firestore에서 코드 확인
                    if check_access_code_exists(access_code):
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "student"
                        st.session_state.user_name = student_name
                        st.session_state.current_access_code = access_code
                        st.success(f"{student_name}님 입장을 환영합니다!")
                        st.rerun()
                    else:
                        st.error("유효하지 않은 학습 코드입니다. 코드를 다시 확인해주세요.")


# ============================================================================
# 4. TEACHER DASHBOARD
# ============================================================================

def show_teacher_dashboard():
    """교사 대시보드"""
    st.title("🎓 교사 대시보드")
    
    # 사이드바 메뉴
    with st.sidebar:
        st.write(f"### 👤 {st.session_state.user_name}")
        st.write(f"**역할**: 교사")
        st.divider()
        
        menu = st.radio(
            "메뉴 선택",
            ["과제 만들기", "학습 결과 확인"],
            key="teacher_menu"
        )
        
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()
    
    # ===== 과제 만들기 =====
    if menu == "과제 만들기":
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        show_create_assignment()
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== 학습 결과 확인 =====
    elif menu == "학습 결과 확인":
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        show_check_results()
        st.markdown("</div>", unsafe_allow_html=True)


def show_create_assignment():
    """과제 만들기 페이지 - YBM 교과서 단원 선택 및 AI 자동 퀴즈 생성"""
    st.subheader("📝 과제 만들기")
    
    st.info("💡 YBM 교과서 단원을 선택하고 난이도를 설정하면 자동으로 지문과 퀴즈가 로드됩니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 단원 선택
        selected_unit = st.selectbox(
            "📖 단원 선택",
            list(YBM_TEXTBOOK.keys()),
            key="unit_select"
        )
    
    with col2:
        # 난이도 선택
        difficulty = st.selectbox(
            "📊 난이도 선택",
            ["Beginner (초급)", "Intermediate (중급)", "Advanced (고급)"],
            key="assignment_difficulty_select"
        )
    
    st.divider()
    
    # 난이도에 따른 지문 자동 로드
    unit_data = YBM_TEXTBOOK[selected_unit]
    unit_title = unit_data["title"]
    
    # 난이도별 지문 선택
    difficulty_key = difficulty.split()[0]  # "Beginner", "Intermediate", "Advanced" 추출
    text_content = unit_data[difficulty_key]
    
    # 선택된 지문 표시
    st.subheader(f"🎯 {unit_title} ({difficulty})")
    st.text_area(
        "📄 지문 내용 (자동 로드됨)",
        value=text_content,
        height=200,
        disabled=True,
        key="display_text"
    )
    
    st.divider()
    
    # AI 자동 퀴즈 생성
    st.subheader("🤖 AI 자동 생성 퀴즈")
    st.info("아래 3가지 유형의 퀴즈가 자동으로 생성되었습니다.")
    
    # AI 퀴즈 생성
    ai_quiz = generate_ai_quiz(text_content, unit_title, difficulty)
    
    # 퀴즈 표시 (3가지 유형)
    quiz_col1, quiz_col2, quiz_col3 = st.columns(3)
    
    with quiz_col1:
        st.markdown(f"### {ai_quiz['summary']['type']}")
        st.write(ai_quiz['summary']['question'])
    
    with quiz_col2:
        st.markdown(f"### {ai_quiz['theme']['type']}")
        st.write(ai_quiz['theme']['question'])
    
    with quiz_col3:
        st.markdown(f"### {ai_quiz['title']['type']}")
        st.write(ai_quiz['title']['question'])
    
    st.divider()
    
    # 추가 퀴즈 작성 (선택사항)
    st.subheader("✏️ 추가 문제 작성 (선택사항)")
    st.caption("위의 AI 생성 퀴즈 외에 추가 문제를 작성하고 싶으신 경우 아래에 입력하세요.")
    
    with st.form("create_assignment_form"):
        additional_quiz = st.text_area(
            "추가 문제",
            height=100,
            key="assignment_quiz",
            placeholder="추가로 작성할 문제가 있으면 입력하세요... (선택사항)"
        )
        
        submitted = st.form_submit_button("✅ 과제 생성 및 배포", use_container_width=True)
        
        if submitted:
            # 6자리 코드 생성
            access_code = generate_access_code()
            
            # AI 퀴즈와 추가 퀴즈 병합
            full_quiz = f"""
【AI 자동 생성 퀴즈】

1️⃣ {ai_quiz['summary']['type']}
{ai_quiz['summary']['question']}

2️⃣ {ai_quiz['theme']['type']}
{ai_quiz['theme']['question']}

3️⃣ {ai_quiz['title']['type']}
{ai_quiz['title']['question']}
"""
            
            if additional_quiz.strip():
                full_quiz += f"\n【추가 문제】\n{additional_quiz}"
            
            # Firestore에 저장
            assignment_data = {
                "title": unit_title,
                "text_content": text_content,
                "difficulty": difficulty,
                "quiz": full_quiz,
                "teacher_name": st.session_state.user_name,
                "unit": selected_unit
            }
            
            if save_assignment(access_code, assignment_data):
                st.success(
                    f"✅ 과제가 생성되었습니다!\n\n"
                    f"**학생들에게 이 코드를 알려주세요: `{access_code}`**\n\n"
                    f"📚 단원: {unit_title}\n"
                    f"📊 난이도: {difficulty}\n"
                    f"❓ 문제: AI 자동 생성 (3가지) + 추가 문제" + ("" if not additional_quiz.strip() else " (수동 작성)")
                )
                st.balloons()
            else:
                st.error("과제 저장에 실패했습니다. 다시 시도해주세요.")


def show_check_results():
    """학습 결과 확인 페이지"""
    st.subheader("📊 학습 결과 확인")
    
    # 생성된 과제 코드 조회
    assignment_codes = get_all_assignment_codes()
    
    if not assignment_codes:
        st.info("생성된 과제가 없습니다.")
        return
    
    selected_code = st.selectbox(
        "과제 코드 선택",
        assignment_codes,
        key="result_code_select"
    )
    
    if selected_code:
        # 과제 정보 표시
        assignment = get_assignment_data(selected_code)
        if assignment:
            st.write(f"**단원명**: {assignment.get('title', 'N/A')}")
            st.write(f"**난이도**: {assignment.get('difficulty', 'N/A')}")
            st.divider()
        
        # 제출 데이터 조회
        submissions = get_submissions_for_code(selected_code)
        
        if not submissions:
            st.info("제출된 학습이 아직 없습니다.")
        else:
            st.write(f"**제출 현황**: {len(submissions)}명")
            
            # 테이블 형식으로 표시
            submission_data = []
            for sub in submissions:
                submission_data.append({
                    "학생 이름": sub.get("student_name", "N/A"),
                    "제출 시간": sub.get("submitted_at").strftime("%Y-%m-%d %H:%M:%S") 
                                  if sub.get("submitted_at") else "N/A",
                    "점수": sub.get("score", 0),
                    "오디오 URL": sub.get("audio_url", "N/A")
                })
            
            # 테이블 표시
            st.dataframe(submission_data, use_container_width=True)
            
            st.divider()
            st.subheader("오디오 재생")
            
            # 각 제출에 대한 오디오 플레이어
            for idx, sub in enumerate(submissions):
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write(f"**{sub.get('student_name', 'Unknown')}**")
                with col2:
                    if sub.get("audio_url"):
                        try:
                            st.audio(sub.get("audio_url"), format="audio/wav")
                        except Exception as e:
                            st.warning(f"오디오 로드 실패: {e}")
                    else:
                        st.write("오디오 없음")


# ============================================================================
# 5. STUDENT WORKSPACE
# ============================================================================

def show_student_workspace():
    """학생 워크스페이스"""
    st.title("👨‍🎓 학생 학습 공간")
    
    # 사이드바
    with st.sidebar:
        st.write(f"### 👤 {st.session_state.user_name}")
        st.write(f"**역할**: 학생")
        st.write(f"**학습 코드**: {st.session_state.current_access_code}")
        st.divider()
        
        if st.button("로그아웃", use_container_width=True):
            logout()
    
    # 과제 데이터 로드
    assignment = get_assignment_data(st.session_state.current_access_code)
    
    if not assignment:
        st.error("과제 정보를 불러올 수 없습니다.")
        return
    
    # ===== 과제 정보 표시 =====
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(assignment.get("title", "제목 없음"))
    with col2:
        st.metric("난이도", assignment.get("difficulty", "N/A"))
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📖 영어 지문")
    st.text_area(
        "지문 내용",
        value=assignment.get("text_content", ""),
        height=200,
        disabled=True,
        key="text_display"
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🎙️ 쉐도잉 녹음")
    st.info(
        "💡 **지문을 큰 소리로 읽고 녹음하세요.**\n\n"
        "자연스러운 발음과 억양으로 읽으시면 더 좋은 평가를 받을 수 있습니다."
    )
    
    st.subheader("🎵 오디오 파일 업로드")
    audio_file = st.file_uploader(
        "녹음된 오디오 파일을 업로드하세요 (MP3, WAV, M4A 형식)",
        type=["mp3", "wav", "m4a", "ogg"],
        key="audio_upload"
    )
    
    if audio_file is not None:
        st.success("✅ 파일이 선택되었습니다!")
        st.audio(audio_file)
        
        if st.button("📤 제출하기", use_container_width=True, key="submit_audio"):
            with st.spinner("업로드 중..."):
                try:
                    audio_bytes = audio_file.read()
                    audio_url, filename = upload_audio_to_storage(
                        audio_bytes,
                        st.session_state.current_access_code,
                        st.session_state.user_name
                    )
                    if audio_url:
                        if save_submission(
                            st.session_state.current_access_code,
                            st.session_state.user_name,
                            audio_url,
                            filename
                        ):
                            st.success("✅ 제출이 완료되었습니다!")
                            st.balloons()
                            st.session_state.submitted = True
                        else:
                            st.error("제출 저장에 실패했습니다.")
                    else:
                        st.error("오디오 업로드에 실패했습니다.")
                except Exception as e:
                    st.error(f"❌ 오류가 발생했습니다: {str(e)}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("❓ 학습 문제")
    st.text_area(
        "문제",
        value=assignment.get("quiz", ""),
        height=150,
        disabled=True,
        key="quiz_display"
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================================
# 6. MAIN APP LOGIC
# ============================================================================

def main():
    """메인 애플리케이션"""
    apply_global_styles()
    if not st.session_state.is_logged_in:
        show_login_page()
    elif st.session_state.user_role == "teacher":
        show_teacher_dashboard()
    elif st.session_state.user_role == "student":
        show_student_workspace()


if __name__ == "__main__":
    main()
