"""
ReadFit - 영어 학습 플랫폼
Streamlit + Firebase + OpenAI를 활용한 인터랙티브 영어 학습 도구
"""

import streamlit as st
import random
import string
import os
from datetime import datetime
# Note: OpenAI client import removed. The app does not currently
# use OpenAI APIs, and importing the client caused a runtime error
# if the package is not installed. Re-add only if needed.

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


# =========================================================================
# IMAGE GENERATION (OpenAI 사용 + 안전한 폴백)
# ============================================================================

def generate_image_with_dalle(word):
    """OpenAI로 먼저 생성, 실패 시 단계적 폴백."""
    import base64

    # 미니멀 폴백(1x1 PNG) - PIL도 없을 때 대비
    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMBgQdX8FAAAAAASUVORK5CYII="
    )

    # 1) OpenAI 시도 (항상 실행, 키는 secrets에서 가져옴)
    api_key = None
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception as e:
        st.error(f"OPENAI_API_KEY가 설정되지 않았습니다: {e}")

    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = f"A colorful, kid-friendly illustration of '{word}', simple background"
            result = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                response_format="b64_json"
            )
            b64_data = result.data[0].b64_json
            if b64_data:
                return base64.b64decode(b64_data)
            else:
                st.error("OpenAI에서 이미지 데이터가 없습니다")
        except Exception as e:
            st.error(f"OpenAI 이미지 생성 실패: {e}")

    # 2) 외부 무료 이미지 서비스(picsum) 사용 시도
    try:
        from urllib.parse import quote
        seed = quote(word)
        return f"https://picsum.photos/seed/{seed}/640/360"
    except Exception as e:
        st.error(f"Picsum 로드 실패: {e}")

    # 3) 폴백: 로컬 플레이스홀더 PNG 생성 (Pillow 필요)
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        img = Image.new("RGB", (640, 360), color=(240, 243, 255))
        draw = ImageDraw.Draw(img)
        title = "Image Detective"
        label = f"Guess: {word}"

        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
            font_body = ImageFont.truetype("DejaVuSans.ttf", 24)
        except Exception:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

        draw.text((40, 100), title, fill=(60, 60, 90), font=font_title)
        draw.text((40, 180), label, fill=(80, 90, 120), font=font_body)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        st.error(f"로컬 이미지 생성 실패: {e}")
        return tiny_png


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
        "Advanced": "Greetings, everyone! I am Harin, and I consider myself a highly active individual with a strong commitment to physical fitness. Running constitutes a significant aspect of my lifestyle. I frequently engage in running sessions at the local park, where I appreciate the invigorating fresh air and natural surroundings. To optimize my training regimen, I utilize a sophisticated running application that meticulously tracks various metrics including velocity, duration, and step count. This technology-driven approach provides valuable data that enables me to monitor my performance improvements over extended periods. The quantified self-movement, exemplified by such tracking methods, facilitates goal-setting and motivational reinforcement. Beyond the physiological benefits, running serves as a meditative practice that enhances my mental clarity and overall well-being. Greetings! My name is Mike, and I possess a profound interest in contemporary fashion and personal styling. I systematically document my daily attire through photography, subsequently sharing these images on various social media platforms. This curated collection functions as a comprehensive fashion diary that chronicles my evolving aesthetic sensibilities. I have cultivated a substantial following of individuals who engage enthusiastically with my content through comments and interactions. Fashion, for me, transcends mere clothing selection; it represents a form of artistic self-expression and identity construction. Each morning's outfit selection involves deliberate consideration of color theory, stylistic coherence, and current fashion trends. The digital documentation process allows for retrospective analysis of my fashion journey while simultaneously contributing to broader online fashion discourse. The reciprocal nature of social media engagement fosters a community of fashion enthusiasts who mutually inspire and influence one another. My name is Elena, and I have recently developed an intense fascination with artisanal donuts. I dedicate considerable leisure time to exploring various donut establishments throughout the metropolitan area. Employing a mapping application, I catalog noteworthy shops, creating a personalized gastronomic guide that facilitates future visits with companions. For me, donuts represent more than simple confectionery; they embody sources of genuine happiness and sensory pleasure. Each establishment offers distinctive flavor profiles and preparation techniques that reflect unique culinary philosophies. My systematic approach to discovering and documenting these experiences exemplifies the contemporary phenomenon of food-focused lifelogging. The integration of mobile technology with culinary exploration enhances social connectivity, as sharing these discoveries with friends creates memorable collective experiences centered around appreciation of quality craftsmanship in food preparation."
    },
    "Unit 2": {
        "title": "Unit 2 - Fun School Events Around the World",
        "Beginner": "Today is a special day in New Zealand. It is Cross Country Race Day. All students run in the woods. We run four kilometers. The path has small hills and many trees. It is not easy, but we can do it. Everyone is at the starting line now. We are ready to run. Let's go! In the Philippines, August is special. It is National Language Month. We have many languages in our country. There are over 100 languages! At school, we have fun events. We have speech contests. We read poems. We act in plays. Everything is in our own languages. I am very proud of my language. It is important to keep our languages alive. In the USA, all students learn music at my school. Some students join the orchestra. Some students join the chorus. Others join the music band. Soon we will have a big concert. I will play the violin in the orchestra. My friend Tom will sing in the chorus. Annie will play the guitar in the band. Our parents will come to watch us. I am nervous but very excited. In Korea, we have a digital writing contest today. We use our smartphones to take pictures. We also write stories about our school. Then we post everything on the school website. Today's topic is our school in spring. I will write about the school garden. I will take pictures of beautiful flowers. This contest is really fun. These are special school events from different countries. Each country has unique traditions. School events help us learn and have fun together.",
        "Intermediate": "Today is Cross Country Race Day in New Zealand. It's a big sport event at our school. We run 4 kilometers in the woods. The course has small hills and lots of trees. It is a hard race, but we can finish it. Now, we're waiting at the starting line! Everyone is excited and ready. Cross country running teaches us perseverance and teamwork. Even though we run individually, we cheer for our classmates. The fresh air and natural scenery make the challenge enjoyable. How many languages do you have in your country? We have over 100 languages in the Philippines. August is National Language Month. There are many events at schools. We have speech contests. We read poems and act in our languages. I'm proud of our languages! Language is an important part of our culture and identity. These events help us appreciate linguistic diversity. Students perform traditional songs and stories in various regional languages. At my school in the USA, every student joins the orchestra, the chorus, or the music band. Soon, we will have a concert in the music hall. I will play the violin in the orchestra. Tom will sing in the chorus, and Annie will play the guitar in the band. My parents are waiting for the concert. I'm nervous but excited! Music education is valued at our school. Regular performances help students develop confidence and artistic skills. We have a digital writing contest today in Korea. We write stories and take pictures with our smartphones. Then, we post our work on the school's online board. The topic is our school campus in the spring. I will write about the school garden and post pictures of the beautiful flowers. It will be fun! Digital literacy is an important skill in modern education. This contest combines creativity with technology.",
        "Advanced": "Today marks Cross Country Race Day in New Zealand, a significant athletic event at our institution. Participants undertake a challenging four-kilometer course through wooded terrain characterized by undulating hills and dense vegetation. This endurance event, while physically demanding, represents an achievable goal for all students who have trained adequately. At present, competitors are assembled at the starting line, demonstrating a mixture of anticipation and determination. Cross country running cultivates not merely physical stamina but also mental resilience and strategic pacing abilities. The communal aspect of cheering for classmates fosters school spirit and collective achievement despite the individual nature of the competition. The Philippines boasts remarkable linguistic diversity, with over 100 distinct languages spoken throughout the archipelago. August is designated as National Language Month, during which educational institutions organize numerous celebratory events. These include oratorical competitions, poetic recitations, and theatrical performances conducted in various indigenous languages. Such initiatives serve to preserve and promote linguistic heritage in an era of increasing globalization. Students gain appreciation for the rich tapestry of Filipino linguistic and cultural traditions. These educational activities reinforce the importance of multilingualism as both a cultural asset and a cognitive advantage. At my American school, comprehensive music education constitutes a mandatory component of the curriculum. Every student participates in either the orchestra, choral ensemble, or instrumental band. An upcoming concert in the school's auditorium will showcase our collective musical development. I shall perform violin in the orchestra, while my peers Tom and Annie will contribute vocal and guitar performances respectively. Despite pre-performance anxiety, the experience of collaborative musical creation proves immensely rewarding. Music education has been demonstrated to enhance cognitive abilities, emotional intelligence, and collaborative skills. Today's digital writing contest in Korea exemplifies the integration of technology with creative expression in contemporary education. Students compose narratives and capture photographic imagery using smartphones, subsequently publishing their work on the school's digital platform. The designated theme focuses on the school campus during the spring season. I intend to document the botanical beauty of our school garden through both prose and photography. This innovative pedagogical approach develops digital literacy, creative writing skills, and visual composition abilities simultaneously, preparing students for the multimedia communication landscape of the 21st century."
    },
    "Unit 3": {
        "title": "Unit 3 - The Power of Small Acts",
        "Beginner": "Food is very important for our health. We need to eat different kinds of food every day. A balanced diet includes fruits, vegetables, grains, proteins, and dairy products. For breakfast, many people eat cereal, toast, or eggs. Some people drink orange juice or milk. Breakfast gives us energy to start the day. For lunch, students often eat sandwiches, salads, or rice with vegetables. It is important to eat vegetables because they have many vitamins. Carrots are good for our eyes. Spinach makes us strong. Tomatoes have vitamin C. For dinner, families usually eat together. They might have chicken, fish, or beef with rice or potatoes. Drinking water is very important. We should drink at least eight glasses of water every day. Water helps our body work well. Some foods are not healthy. Candy and soda have too much sugar. Chips have too much salt. We should not eat too much fast food like hamburgers and pizza. These foods can make us sick if we eat them every day. Fruits are nature's candy. Apples, bananas, oranges, and grapes are delicious and healthy. They give us natural sugar and energy. We should eat five servings of fruits and vegetables every day. Protein helps build strong muscles. We can get protein from meat, fish, eggs, beans, and nuts. Calcium makes our bones and teeth strong. Milk, cheese, and yogurt have calcium. Growing children need calcium every day. Eating healthy food helps us grow, learn, and play. When we eat good food, we feel happy and strong. We can think better in school and run faster in sports.",
        "Intermediate": "Understanding nutrition is essential for maintaining a healthy lifestyle. Nutritionists recommend following the food pyramid or the newer MyPlate guidelines, which emphasize balanced portions of different food groups. A well-rounded diet should consist of whole grains, lean proteins, fruits, vegetables, and low-fat dairy products. Whole grains like brown rice, whole wheat bread, and oatmeal provide fiber and sustained energy throughout the day. Unlike refined grains, they help regulate blood sugar levels and promote digestive health. Proteins are the building blocks of our bodies. They repair tissues and support muscle growth. Good protein sources include chicken, fish, eggs, legumes, tofu, and nuts. Fish, particularly salmon and tuna, contain omega-3 fatty acids that benefit heart and brain health. Fruits and vegetables are rich in vitamins, minerals, and antioxidants. These nutrients strengthen our immune system and protect against diseases. Colorful vegetables like broccoli, bell peppers, and sweet potatoes offer different nutritional benefits. Nutritionists suggest eating a rainbow of colors to ensure varied nutrient intake. Calcium and vitamin D work together to build strong bones. Dairy products, fortified plant-based milk, and leafy greens provide calcium. Sunlight helps our bodies produce vitamin D. However, modern eating habits often include too much processed food, which contains excessive sodium, sugar, and unhealthy fats. These ingredients contribute to obesity, diabetes, and heart disease. Reading nutrition labels helps us make informed choices about what we consume. Portion control is equally important. Even healthy foods can lead to weight gain if consumed in large quantities. Staying hydrated by drinking water instead of sugary beverages supports overall health and helps maintain proper body functions.",
        "Advanced": "Nutritional science has evolved significantly over the past decades, revealing the complex relationship between diet and overall health. Contemporary research emphasizes not merely the quantity of food consumed but the quality and nutritional density of dietary choices. The concept of functional foods—items that provide health benefits beyond basic nutrition—has gained prominence in nutritional discourse. These include foods rich in probiotics, antioxidants, and phytonutrients that may help prevent chronic diseases. The Mediterranean diet, extensively studied for its health benefits, exemplifies a balanced approach to nutrition. It prioritizes olive oil, fish, whole grains, legumes, and abundant fresh produce while limiting red meat and processed foods. Research indicates this dietary pattern reduces cardiovascular disease risk and promotes longevity. Macronutrient balance—the ratio of carbohydrates, proteins, and fats—remains a subject of ongoing scientific investigation. While traditional guidelines recommended low-fat diets, current evidence suggests that healthy fats from sources like avocados, nuts, and fatty fish play crucial roles in hormone production, nutrient absorption, and cellular function. The glycemic index and glycemic load concepts help individuals understand how different carbohydrates affect blood sugar levels. Complex carbohydrates with low glycemic indices provide sustained energy and better metabolic outcomes compared to simple sugars. Emerging research on the gut microbiome has revolutionized our understanding of nutrition's impact on health. The trillions of bacteria in our digestive system influence not only digestion but also immune function, mental health, and disease susceptibility. Fermented foods and dietary fiber support beneficial gut bacteria. However, nutritional requirements vary based on age, gender, activity level, and individual health conditions. Personalized nutrition, guided by genetic factors and biomarkers, represents the future of dietary recommendations, moving beyond one-size-fits-all guidelines."
    },
    "Unit 4": {
        "title": "Unit 4 - My Family Tradition",
        "Beginner": "My name is Yubin. My father is from India. My mother is from Korea. They both work with computers. We are a family of three. We have two special family traditions. Every spring, we go to the baseball park. It is the first day of the baseball season. We wear our team's uniform. We cheer loudly for our team. We take pictures at the park gates. I was four years old when we went there for the first time. Now I am older, but we still go every year. It is very exciting! My father's birthday is in the fall. We do special things on his birthday. In the evening, we cook Indian chicken curry together. It is my father's favorite food. We use special curry powder from my grandmother in India. It tastes like real Indian food. We all love eating curry together. It is warm and delicious. After dinner, we play a board game called pachisi. It is a traditional game from India. My father played this game when he was a child. Last year, I lost the game. So I had to wash the dishes. This year, I want to win! I will try my best. Family traditions are very important. They create happy memories. I love our family traditions. I want to keep them for a long time. When I grow up and have my own family, I will teach these traditions to my children. Traditions connect us to our family history and culture.",
        "Intermediate": "My name is Yubin. My father and mother are computer engineers. My mother fell in love with him when she worked in India. Yes, my father is Indian. We're a family of three. We have two family traditions. Every spring, we visit the city's baseball park on the KBO's opening day. It's an exciting day. We wear our team's uniform and cheer for them loudly. We like to take pictures at the gates. When we visited the park for the first time, I was four years old. This tradition has continued for many years now. The excitement of opening day never gets old. Watching baseball together brings our family closer. We share the joy of victories and the disappointment of defeats. My father's birthday is in the fall. We do special things on his birthday. In the evening, we cook Indian chicken curry together. It's his favorite dish. We get special curry powder from my grandmother in India. It has the real taste of India. We all love a warm and tasty bowl of curry. Cooking together is a bonding experience. We talk, laugh, and share stories while preparing the meal. After dinner, we play pachisi. It's a traditional board game in India. My father played it when he was young. Last year, I lost the game and did the dishes. I really want to win this year! The game teaches us about strategy and patience. It also connects us to my father's childhood memories in India. Family traditions create wonderful memories. I love my family traditions and hope to keep them for a long time. These rituals give us a sense of identity and belonging. They remind us of our multicultural heritage and the love that binds us together.",
        "Advanced": "My name is Yubin. Both my parents are computer engineers who met professionally. My mother developed romantic feelings for my father during her employment tenure in India. Indeed, my father is of Indian descent, making our household a cross-cultural family unit of three members. We maintain two distinctive family traditions that reflect our bicultural heritage. Annually during spring, we attend the city's baseball stadium on the Korean Baseball Organization's opening day. This occasion represents a significant family ritual. We don matching team uniforms and enthusiastically support our chosen team with vocal encouragement. We habitually capture photographic memories at the stadium entrance gates. I was merely four years of age during our inaugural visit, and this tradition has persisted consistently ever since. The ceremonial aspect of opening day attendance transcends mere sports spectatorship; it represents a familial bonding experience and a celebration of Korean cultural participation. My father's birthday occurs during the autumn season. We observe specific commemorative practices on this occasion. During the evening hours, we collaboratively prepare Indian chicken curry, his preferred culinary dish. We utilize specialized curry powder procured from my paternal grandmother in India, ensuring authentic flavor profiles characteristic of genuine Indian cuisine. The communal preparation and consumption of this meal constitutes both a gastronomic experience and a cultural ritual connecting us to my father's heritage. Following the meal, we engage in pachisi, a traditional Indian board game with historical significance. My father participated in this game during his childhood in India. During last year's competition, my defeat resulted in dish-washing responsibilities. This year, I am determined to achieve victory through improved strategic gameplay. The game serves multiple functions: entertainment, strategic thinking development, and cultural transmission. Family traditions function as crucial mechanisms for creating enduring memories and establishing familial identity. I deeply value our family traditions and aspire to perpetuate them indefinitely. These practices represent more than mere routines; they embody our multicultural identity, preserve intergenerational connections, and reinforce the affective bonds that constitute our family unit. Such traditions provide continuity, meaning, and a sense of belonging in an increasingly globalized world."
    },
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
            {"question": "What is Harin's main hobby?", "options": ["Swimming", "Running", "Dancing"], "answer": 1},
            {"question": "What does Mike share on social media?", "options": ["Food pictures", "Fashion outfit pictures", "Travel photos"], "answer": 1},
            {"question": "What does Elena love to visit?", "options": ["Restaurants", "Donut shops", "Bookstores"], "answer": 1}
        ],
        "Unit 2": [
            {"question": "Which country celebrates Cross Country Race Day?", "options": ["USA", "New Zealand", "Philippines"], "answer": 1},
            {"question": "How many languages are spoken in the Philippines?", "options": ["Over 50", "Over 100", "Over 150"], "answer": 1},
            {"question": "What instrument does the narrator play?", "options": ["Piano", "Guitar", "Violin"], "answer": 2}
        ],
        "Unit 3": [
            {"question": "What is essential for a healthy lifestyle?", "options": ["Sweets", "Balanced nutrition", "Fast food"], "answer": 1},
            {"question": "How many glasses of water should we drink daily?", "options": ["4 glasses", "8 glasses", "12 glasses"], "answer": 1},
            {"question": "Which nutrient is important for strong bones?", "options": ["Iron", "Calcium", "Sodium"], "answer": 1}
        ],
        "Unit 4": [
            {"question": "Where is Yubin's father originally from?", "options": ["Korea", "India", "USA"], "answer": 1},
            {"question": "When do they visit the baseball park?", "options": ["Fall", "Spring", "Summer"], "answer": 1},
            {"question": "What traditional game do they play?", "options": ["Chess", "Pachisi", "Go"], "answer": 1}
        ]
    }
    return quiz_templates.get(unit, quiz_templates["Unit 1"])


# ============================================================================
# TEACHER DASHBOARD
# ============================================================================

def show_teacher_dashboard():
    """교사 대시보드"""
    st.header("👨‍🏫 교사 대시보드")

    tab1, tab2, tab3 = st.tabs(["📚 과제 배포", "📈 결과 대시보드", "🗂 제공 텍스트 보기"])

    # ------------------------------------------------------------
    # Tab 1: 과제 배포 (미리보기/편집 + 퀴즈 확인)
    # ------------------------------------------------------------
    with tab1:
        st.subheader("📚 새 과제 생성 및 미리보기")

        unit = st.selectbox("Unit 선택", ["Unit 1", "Unit 2", "Unit 3", "Unit 4"], key="publish_unit")
        difficulty = st.radio("난이도 선택", ["상", "중", "하"], horizontal=True, key="publish_difficulty")

        difficulty_map = {"상": "Advanced", "중": "Intermediate", "하": "Beginner"}
        text_key = difficulty_map[difficulty]
        base_text = YBM_TEXTBOOK.get(unit, {}).get(text_key, "Sample text")

        # 미리보기(편집 가능): 난이도/유닛에 따라 키를 달리하여 캐시 문제 방지
        edited_text = st.text_area(
            "지문 미리보기 (편집 가능)",
            value=base_text,
            height=220,
            key=f"preview_text_{unit}_{text_key}"
        )

        st.divider()
        st.subheader("❓ 자동 생성 퀴즈 미리보기")
        quiz_preview = generate_quiz_questions(unit)

        # MCQ 스타일로 보기 구성
        for idx, q in enumerate(quiz_preview):
            st.markdown(f"**{idx+1}. {q['question']}**")
            opts = q.get("options", [])
            correct_idx = q.get("answer", 0)
            for i, opt in enumerate(opts):
                marker = "①" if i == 0 else "②" if i == 1 else "③" if i == 2 else "④"
                label = f"{marker} {opt}"
                if i == correct_idx:
                    st.write(f"- {label} (정답)")
                else:
                    st.write(f"- {label}")
            st.write("—")

        # 디버그 정보
        with st.expander("🔍 디버그 정보"):
            st.write({
                "selected_unit": unit,
                "selected_difficulty": difficulty,
                "text_key": text_key,
                "available_keys": list(YBM_TEXTBOOK.get(unit, {}).keys()),
                "text_length": len(base_text),
                "text_preview": base_text[:120]
            })

        if st.button("🚀 과제 생성 및 배포", use_container_width=True, key="publish_create"):
            access_code = generate_access_code()
            quiz_data = quiz_preview
            text = edited_text or base_text

            if save_assignment_to_firebase(access_code, unit, difficulty, quiz_data, text):
                st.success("✅ 과제가 생성되었습니다!")
                st.info(f"**학생 접속 코드: {access_code}**")
            else:
                st.error("과제 생성 실패")

    # ------------------------------------------------------------
    # Tab 2: 결과 대시보드 (Firestore에서 과제 조회)
    # ------------------------------------------------------------
    with tab2:
        st.subheader("📈 결과 대시보드")
        st.caption("배포된 과제와 학생 결과를 확인하세요")

        # Firestore에서 과제 목록 가져오기 (가능한 경우)
        assignments = []
        try:
            from firebase_admin import firestore  # type: ignore
            db = firestore.client()  # 이미 초기화된 경우 정상 동작
            docs = db.collection("readfit_assignments").order_by("created_at", direction=firestore.Query.DESCENDING).limit(20).stream()
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                assignments.append(data)
        except Exception:
            st.warning("Firestore 조회가 비활성화되어 있습니다. 배포 후 확인하세요.")

        if assignments:
            for a in assignments:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**접속 코드:** {a.get('access_code', '-')}")
                        st.markdown(f"- Unit: {a.get('unit', '-')}")
                        st.markdown(f"- 난이도: {a.get('difficulty', '-')}")
                        st.markdown(f"- 생성 시각: {a.get('created_at', '-')}")
                    with col2:
                        st.markdown("**퀴즈 문항 수:** " + str(len(a.get('quiz', []))))
                        # 학생 결과가 저장되는 필드를 가정하여 표시 (없으면 생략)
                        results = a.get('results')
                        if results:
                            avg = int(sum(r.get('total_score', 0) for r in results) / max(len(results), 1))
                            st.markdown(f"**평균 점수:** {avg}")
                            st.markdown(f"**제출 수:** {len(results)}")
                        else:
                            st.markdown("제출된 결과 없음")
        else:
            st.info("아직 표시할 과제가 없습니다.")

    # ------------------------------------------------------------
    # Tab 3: 제공 텍스트 보기 (Intermediate - 제공본 확인)
    # ------------------------------------------------------------
    with tab3:
        st.subheader("🗂 제공된 Unit 텍스트 (중급)")
        st.caption("Units 1–4의 제공된 중급 텍스트를 확인하세요")

        for u in ["Unit 1", "Unit 2", "Unit 3", "Unit 4"]:
            text_mid = YBM_TEXTBOOK.get(u, {}).get("Intermediate")
            title = YBM_TEXTBOOK.get(u, {}).get("title", u)
            with st.expander(f"{title} — {u}"):
                if text_mid:
                    st.write(text_mid)
                else:
                    st.write("중급 텍스트가 없습니다.")


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
        
        # 이미지 생성 (안정적인 URL)
        with st.spinner("🤖 AI가 그림을 그리고 있어요..."):
            image_url = generate_image_with_dalle(selected_word)
            st.session_state.detective_image = image_url
    
    # 이미지 표시 (바이트 또는 URL 모두 지원)
    if st.session_state.detective_image:
        try:
            st.image(st.session_state.detective_image, caption="이 그림이 무엇일까요?", use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ 이미지를 로드할 수 없습니다. ({str(e)})")
            st.info(f"단어: {st.session_state.detective_word}")
    else:
        st.warning("⚠️ 이미지를 준비하지 못했습니다.")
    
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
