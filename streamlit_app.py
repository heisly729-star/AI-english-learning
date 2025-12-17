"""
ReadFit - 영어 학습 플랫폼
Streamlit + Firebase를 활용한 인터랙티브 영어 학습 도구
"""

import streamlit as st
import random
import string
import base64
import os
from datetime import datetime
from openai import OpenAI


# ==========================================================================
# UTILITY FUNCTIONS
# ==========================================================================

@st.cache_resource(show_spinner=False)
def get_openai_client():
    """Create a cached OpenAI client using secrets or env."""
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key) if api_key else None


def generate_report_insights_with_openai(submission_data, mission_details):
    """Generate coaching-style Korean report insights as JSON via OpenAI Responses API."""
    client = get_openai_client()
    if not client:
        return None

    json_schema = {
        "name": "report_insights",
        "schema": {
            "type": "object",
            "properties": {
                "one_line_feedback": {"type": "string"}
            },
            "required": ["one_line_feedback"],
            "additionalProperties": False
        },
        "strict": True
    }

    mission_id = submission_data.get("mission_id", "")
    is_correct = submission_data.get("activity_score", 0) >= 80
    
    # 2~3문장 피드백 프롬프트 (칭찬 + 꿀팁)
    prompt = f"""너는 초등학생을 따뜻하게 격려하는 선생님이야.
아이가 {mission_id} 활동을 했고, {'정답' if is_correct else '오답'}을 골랐어.

피드백 규칙 (총 2~3문장):
1. [구체적인 칭찬] - 그림의 어떤 요소(주어/동사/사물 등)를 잘 찾았는지 콕 집어서 칭찬
   예: "그림 속 주인공의 행동(run)을 아주 정확하게 캐치했네요!"
   
2. [앞으로의 공부 꿀팁] - 이번 활동과 관련된 구체적인 학습 행동 추천
   예: "앞으로도 지문을 읽을 때 머릿속으로 상황을 그림처럼 상상해보는 연습을 해보세요!"
   예: "다음에는 주인공의 행동을 나타내는 동사(Verb)에 동그라미를 치며 읽어볼까요?"

톤앤매너:
- 선생님이 옆에서 어깨를 토닥이며 격려해주는 따뜻한 말투
- "공부 열심히 해" 같은 뻔한 말 금지
- 쉽고 친근하게, 군더더기 설명 없이

좋은 예시 (전체):
"문장 속 장소(school)를 정확하게 찾아냈어요! 다음에는 주어가 누구인지도 함께 생각하며 읽어보면 더 잘 이해될 거예요."

제출 데이터: {submission_data}
미션 상세: {mission_details}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": str({"submission": submission_data, "mission_details": mission_details})}
            ],
            response_format={"type": "json_schema", "json_schema": json_schema}
        )

        content = resp.choices[0].message.content
        if not content:
            st.error("❌ OpenAI 응답에 content가 없습니다.")
            return None
        import json
        return json.loads(content)
    except Exception as e:
        st.error(f"❌ OpenAI 리포트 생성 실패: {type(e).__name__}: {str(e)}")
        return None

def generate_image_with_dalle(word, context_sentence=""):
    """OpenAI DALL-E 3를 사용하여 지문 맥락 기반 장면 이미지 생성
    
    Args:
        word (str): 정답 단어
        context_sentence (str): 지문 속 맥락 문장
        
    Returns:
        bytes or str: 이미지 바이트 데이터 또는 URL
    """
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            
            # 1단계: context_sentence를 시각화 가능한 장면 설명으로 변환
            if context_sentence:
                chat_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": f"""Convert this sentence into a visual scene description for an illustration.

Original sentence: "{context_sentence}"
Target word: "{word}"

Rules:
- Only describe what can be SEEN: characters, location, action, visible objects
- Do NOT add information not in the original sentence
- Keep it simple and clear (one sentence)
- Focus on the key word: {word}

Return ONLY the scene description, nothing else."""
                    }],
                    temperature=0.5
                )
                scene_description = chat_response.choices[0].message.content.strip()
            else:
                scene_description = f"A simple scene showing '{word}' in a typical context."
            
            # 2단계: 이미지 프롬프트를 지문 충실 템플릿으로 구성
            image_prompt = f"""
Create a simple educational illustration that is strictly grounded in the sentence below.
Use ONLY what the sentence states. Do NOT add any new characters, cultures, religions, clothing styles, symbols, or events not mentioned.
If details are not specified, use neutral generic characters.
Keep it literal and simple. No text.

Sentence:
{context_sentence}

Key word (use only if naturally visible in the sentence):
{word}
"""
            
            result = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                response_format="b64_json"
            )
            b64_data = result.data[0].b64_json
            if b64_data:
                return base64.b64decode(b64_data)
        except Exception as e:
            st.warning(f"OpenAI 이미지 생성 실패, 기본 이미지로 대체합니다: {e}")
    
    # 폴백: Picsum 랜덤 이미지 (단어 시드)
    try:
        return f"https://picsum.photos/seed/{word}/512/512"
    except Exception:
        # 최종 폴백: Unsplash 기본
        return f"https://source.unsplash.com/512x512/?{word},{random.randint(1,100)}"


def get_educational_distractors(word):
    """OpenAI GPT를 사용하여 교육적 오답 생성
    
    Args:
        word (str): 정답 단어
        
    Returns:
        dict: {"semantic": str, "spelling": str, "random": str}
    """
    api_key = st.secrets.get("OPENAI_API_KEY")
    
    if not api_key:
        return {"semantic": "dog", "spelling": "log", "random": "desk"}
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": f"""For the English word '{word}', generate 3 wrong answer options for a children's quiz:
1. Semantic distractor: A word with similar meaning or same category
2. Spelling distractor: A word that looks/sounds similar
3. Random distractor: A completely unrelated simple word

Return ONLY a JSON object like: {{"semantic": "word1", "spelling": "word2", "random": "word3"}}"""
            }],
            temperature=0.7
        )
        
        import json
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty content from OpenAI for distractors")
        result = json.loads(content)
        return result
    except Exception as e:
        st.warning(f"오답 생성 실패: {e}")
        return {"semantic": "dog", "spelling": "log", "random": "desk"}


def get_sentence_distractors(correct_sentence, context_text):
    """OpenAI GPT를 사용하여 문장 기반 교육적 오답 생성
    
    Args:
        correct_sentence (str): 정답 문장 (S+V+O 형태)
        context_text (str): 지문 내용
        
    Returns:
        dict: {"subject_wrong": str, "verb_wrong": str, "object_wrong": str}
    """
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    
    if not api_key:
        return {
            "subject_wrong": "The girl is running to school.",
            "verb_wrong": "The boy is walking to school.",
            "object_wrong": "The boy is running to the park."
        }
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": f"""Given the correct sentence: "{correct_sentence}"
Context from passage: "{context_text}"

Generate 3 wrong answer sentences for a children's quiz. Each wrong sentence should be based on the correct sentence but with ONLY ONE WORD changed:

1. subject_wrong: Change ONLY the subject (who/what does the action)
2. verb_wrong: Change ONLY the verb/action
3. object_wrong: Change ONLY the object/destination/place

Keep sentences simple (S+V+O structure). Use words that could plausibly fit but are incorrect based on the context.

Return ONLY a JSON object like: {{"subject_wrong": "sentence1", "verb_wrong": "sentence2", "object_wrong": "sentence3"}}"""
            }],
            temperature=0.7
        )
        
        import json
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty content from OpenAI for sentence distractors")
        result = json.loads(content)
        return result
    except Exception as e:
        st.warning(f"오답 생성 실패: {e}")
        return {
            "subject_wrong": "The girl is running to school.",
            "verb_wrong": "The boy is walking to school.",
            "object_wrong": "The boy is running to the park."
        }


def get_writing_feedback(text, keywords):
    """OpenAI GPT를 사용하여 학생 작문 피드백 생성
    
    Args:
        text (str): 학생이 작성한 텍스트
        keywords (list): 포함되어야 할 키워드 리스트
        
    Returns:
        str: 한국어 피드백 메시지
    """
    api_key = st.secrets.get("OPENAI_API_KEY")
    
    if not api_key:
        return "피드백 생성 중 오류가 발생했습니다."
    
    try:
        client = OpenAI(api_key=api_key)
        keywords_str = ", ".join(keywords)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""학생이 영어 작문을 했습니다. 다음을 확인해주세요:

작문 내용:
{text}

필수 키워드: {keywords_str}

다음을 포함한 한국어 피드백을 작성해주세요:
1. 전체적인 평가 (1-2줄)
2. 필수 키워드 사용 여부 체크
3. 문법/철자 오류가 있다면 간단히 수정 제안
4. 격려의 말

피드백은 초등학생이 이해하기 쉽게 친근하게 작성해주세요."""
            }],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"피드백 생성 중 오류: {e}"


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
        "title": "Unit 3 - Food and Nutrition",
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
    "Unit 5": {
        "title": "Unit 5 - Sports and Physical Activity",
        "Beginner": "Sports are fun and good for our health. Many people around the world love sports. Soccer is the most popular sport globally. Players kick a ball and try to score goals. Basketball is another popular sport. Players bounce a ball and throw it through a hoop. Swimming is great exercise. It makes our arms, legs, and heart strong. Tennis is a sport played with rackets. Two or four players hit a ball over a net. Running is simple but very healthy. Many people jog in parks every morning. Playing sports has many benefits. Exercise makes our bodies strong and healthy. It helps our hearts work better and gives us more energy. Sports also make us happy. When we play sports, our brain releases chemicals that make us feel good. Team sports like soccer and basketball teach us important lessons. We learn to work together and help our teammates. We learn to follow rules and be fair. We also learn that practice makes us better. Even when we lose, we can learn and improve. Some people prefer individual sports like swimming or running. These sports help us set personal goals and challenge ourselves. Many schools have physical education classes. Students play different sports and learn about fitness. Some students join school sports teams. They practice after school and compete with other schools. Playing sports keeps kids active and healthy. It's also a great way to make friends. Everyone can enjoy sports, whether playing for fun or competing seriously. The important thing is to be active, try your best, and have fun while staying healthy.",
        "Intermediate": "Physical activity and sports participation contribute significantly to overall health and personal development. Engaging in regular exercise strengthens cardiovascular systems, builds muscle tone, and enhances flexibility. Medical professionals recommend at least 150 minutes of moderate physical activity weekly for adults, while children should aim for 60 minutes daily. Athletic activities encompass diverse categories. Team sports like soccer, basketball, and volleyball foster collaboration and communication skills. Players must coordinate strategies, support teammates, and work toward common objectives. These experiences translate into valuable life skills applicable in academic and professional contexts. Individual sports such as swimming, running, and tennis cultivate self-discipline and personal responsibility. Athletes set individual goals, monitor progress, and develop mental resilience through training. Competitive swimming, for instance, requires consistent practice and technique refinement. Marathon runners demonstrate extraordinary endurance and dedication. Participation in sports also promotes psychological well-being. Physical activity reduces stress and anxiety while improving mood and self-esteem. The endorphins released during exercise create positive feelings and can alleviate symptoms of depression. Athletic involvement provides social connections and community belonging, particularly important for young people navigating social development. Moreover, sports teach essential values including perseverance, sportsmanship, and respect for opponents. Athletes learn to accept both victory and defeat gracefully, understanding that improvement comes through persistent effort. These character-building experiences shape individuals' approaches to challenges throughout life. From youth leagues to professional competitions, sports unite communities and transcend cultural boundaries, demonstrating universal values of excellence and fair play.",
        "Advanced": "The multifaceted benefits of sports and physical activity extend far beyond mere physiological improvements, encompassing psychological, social, and cultural dimensions. Contemporary sports science examines the intricate relationship between physical activity and holistic human development. Physiologically, regular exercise induces numerous adaptations including enhanced cardiovascular efficiency, improved metabolic function, increased bone density, and optimized neuromuscular coordination. Research demonstrates that consistent physical activity significantly reduces risk factors for chronic diseases such as diabetes, hypertension, and certain cancers. The psychological dimensions of sports participation merit serious consideration. Athletic engagement facilitates development of mental toughness, emotional regulation, and cognitive flexibility. Sports psychology research reveals that athletes often demonstrate superior executive function, including enhanced attention control and decision-making capabilities developed through competitive experiences. Furthermore, athletic participation provides opportunities for experiencing flow states—optimal psychological experiences characterized by complete absorption in challenging activities. The social capital generated through sports participation proves invaluable. Team sports cultivate leadership abilities, conflict resolution skills, and cultural competence through interaction with diverse teammates. These interpersonal competencies transfer readily to professional environments, explaining why many organizations actively recruit former athletes. Sports also function as vehicles for social mobility and community integration, particularly for marginalized populations. From a sociocultural perspective, sports reflect and shape broader societal values. Competitive athletics demonstrate meritocratic principles while simultaneously revealing persistent inequities in access and opportunity. Contemporary discourse addresses issues of gender equality, racial justice, and economic accessibility within sports institutions. Professional athletics generates substantial economic activity while raising questions about commercialization and ethical considerations in sports management. Understanding sports requires recognizing these complex, interconnected dimensions that influence individual development and collective social dynamics."
    },
    "Unit 6": {
        "title": "Unit 6 - Hobbies and Leisure Activities",
        "Beginner": "Hobbies are activities we do for fun in our free time. Everyone should have hobbies because they make us happy and relaxed. Reading books is a popular hobby. When we read, we learn new things and visit different worlds through stories. Many people like reading adventure stories, mystery books, or books about animals. Drawing and painting are creative hobbies. With just paper and colored pencils, we can create beautiful pictures. Some people draw landscapes, others draw people or animals. Art helps us express our feelings and ideas. Playing musical instruments is another wonderful hobby. The piano, guitar, and violin are common instruments. Learning music takes time and practice, but it is very rewarding. Music makes our brains work better and helps us concentrate. Collecting things is fun too. Some people collect stamps from different countries. Others collect coins, rocks, or trading cards. Collections teach us about history and different cultures. Gardening is a peaceful hobby. We can grow flowers, vegetables, or herbs in a garden or even in small pots on a balcony. Taking care of plants teaches us patience and responsibility. Watching plants grow is very satisfying. Sports and outdoor activities are active hobbies. Hiking, cycling, and swimming keep us healthy and strong. Photography is becoming very popular. With cameras or smartphones, we can capture special moments and beautiful scenes. Cooking is both useful and enjoyable. Trying new recipes and making delicious food for family and friends is rewarding. Hobbies give us something to look forward to after school or work. They help us develop new skills and meet people with similar interests.",
        "Intermediate": "Leisure activities play a crucial role in maintaining work-life balance and personal well-being. Pursuing hobbies provides opportunities for self-expression, skill development, and stress relief. The benefits extend beyond simple entertainment, contributing to mental health and overall life satisfaction. Reading represents one of the most enriching leisure pursuits. Literature expands vocabulary, enhances critical thinking, and develops empathy by exposing readers to diverse perspectives and experiences. Whether fiction or non-fiction, reading stimulates imagination and provides intellectual engagement. Many people join book clubs to share insights and discuss themes with fellow enthusiasts. Artistic endeavors such as painting, drawing, or sculpting offer therapeutic benefits. The creative process facilitates emotional expression and mindfulness. Art therapy research demonstrates that creative activities reduce anxiety and promote psychological healing. Digital art has expanded possibilities, allowing artists to experiment with various media and techniques. Musical engagement, whether playing instruments or singing, activates multiple brain regions simultaneously. Neuroscience research indicates that musical training enhances memory, coordination, and cognitive flexibility. Many communities offer amateur orchestras or choirs where individuals can participate collectively. Physical hobbies including hiking, cycling, and rock climbing combine exercise with nature appreciation. These activities reduce stress while improving cardiovascular health. Outdoor recreation fosters environmental awareness and appreciation for natural beauty. Collecting reflects human fascination with categorization and completion. Whether stamps, coins, or vintage items, collections require research, organization, and knowledge acquisition. Serious collectors develop expertise in their specialized areas, sometimes contributing to academic understanding. The digital age has introduced new hobby categories. Gaming, coding, and content creation attract millions of enthusiasts worldwide. These pursuits develop technological literacy and creative problem-solving abilities. Ultimately, hobbies enrich life by providing purpose, challenge, and joy beyond professional obligations.",
        "Advanced": "The psychology of leisure and recreational pursuits reveals profound insights into human motivation, identity formation, and well-being. Leisure activities serve functions beyond mere diversion, contributing significantly to self-actualization and life satisfaction. Contemporary research in positive psychology emphasizes the importance of engaging in personally meaningful activities that facilitate flow experiences, which are states of complete absorption where individuals lose self-consciousness and time awareness. Literary engagement exemplifies cognitively demanding leisure that yields substantial developmental benefits. Reading complex narratives enhances theory of mind, the capacity to understand others mental states, and cultivates empathetic understanding across cultural and temporal boundaries. Literary analysis develops critical thinking and interpretive skills transferable to numerous domains. Furthermore, bibliotherapy employs literature therapeutically to address psychological challenges and facilitate personal growth. Artistic creation engages neural networks associated with planning, motor control, and emotional processing. Neuroscientific investigations using functional magnetic resonance imaging reveal that artistic activities activate the default mode network, facilitating introspection and self-referential thought. Art-making serves as a form of non-verbal communication, particularly valuable for individuals who struggle with linguistic expression of complex emotions. Musical training produces remarkable neuroplastic changes, including increased gray matter volume in regions associated with motor control, auditory processing, and executive function. Longitudinal studies demonstrate that musical education enhances linguistic abilities, mathematical reasoning, and spatial-temporal skills. The social dimensions of ensemble performance foster collaborative abilities and collective emotional expression. Outdoor recreation reflects biophilia, humans innate connection to nature. Environmental psychology research demonstrates that natural environments reduce cognitive fatigue, lower cortisol levels, and enhance mood. The concept of wilderness therapy employs outdoor experiences to facilitate psychological healing and personal transformation. Collecting behaviors manifest deep-seated cognitive predispositions toward categorization and pattern recognition. Collections provide tangible manifestations of personal identity and intellectual interests. Museum-quality private collections occasionally contribute to scholarly research and cultural preservation. The digital revolution has democratized creative production, enabling unprecedented participation in media creation, knowledge sharing, and global communities of practice. These contemporary leisure forms challenge traditional distinctions between consumption and production, fostering participatory culture."
    },
    "Unit 7": {
        "title": "Unit 7 - Travel and Exploring the World",
        "Beginner": "Traveling is exciting and educational. When we visit new places, we see different things and learn about other cultures. Many families take vacations during summer. Some people go to the beach. They swim in the ocean, build sandcastles, and collect shells. The beach is relaxing and fun. Other families visit mountains. They go hiking on trails, breathe fresh air, and enjoy beautiful views. Mountain air is clean and healthy. Cities are interesting places to visit too. Big cities have tall buildings, museums, and famous landmarks. In London, people can see Big Ben and Buckingham Palace. In Paris, the Eiffel Tower is very famous. New York has the Statue of Liberty. Before traveling, people need to prepare. They pack clothes, toothbrushes, and other necessary items in suitcases. They check the weather to know what clothes to bring. Some people make lists so they don't forget anything important. There are many ways to travel. Airplanes are fast and can go to far places quickly. Trains are comfortable for traveling between cities. Buses are cheaper than planes and trains. Cars give families freedom to stop wherever they want. When traveling to other countries, people often learn new words in different languages. Saying hello, thank you, and goodbye in the local language is polite and helpful. Local people appreciate when visitors try to speak their language. Trying new foods is an exciting part of traveling. Each country has special dishes. Italian pizza and pasta are delicious. Chinese dumplings are tasty. Mexican tacos are spicy and flavorful. Traveling helps us understand that people everywhere have different customs but share similar feelings and dreams. It makes the world feel smaller and friendlier.",
        "Intermediate": "Travel broadens perspectives and enriches understanding of global diversity. Exploring different regions exposes individuals to varied cultural practices, historical contexts, and natural environments. Tourism represents a significant economic sector while facilitating cross-cultural exchange and international understanding. Destination selection depends on personal interests and objectives. Historical tourism focuses on visiting sites of cultural and historical significance. Ancient ruins like Machu Picchu in Peru or the Colosseum in Rome connect visitors with past civilizations. Museums and heritage sites preserve cultural artifacts and narratives. Ecotourism emphasizes environmental conservation and sustainable practices. Travelers visit natural reserves, observe wildlife in habitats, and support conservation efforts. Destinations like the Galapagos Islands or African safaris offer remarkable biodiversity experiences while promoting ecological awareness. Adventure tourism attracts individuals seeking physical challenges and novel experiences. Activities include mountain climbing, scuba diving, and trekking through remote regions. These experiences test personal limits and create lasting memories. Effective travel planning enhances trip quality. Researching destinations, understanding local customs, and learning basic phrases in local languages demonstrate respect and facilitate positive interactions. Budget management ensures financial sustainability throughout trips. Cultural sensitivity remains crucial when traveling. Different societies maintain distinct social norms, religious practices, and communication styles. Observing and respecting these differences prevents misunderstandings and fosters mutual appreciation. Photography etiquette, dress codes, and behavioral expectations vary significantly across cultures. Transportation options influence travel experiences. Air travel enables rapid long-distance movement but contributes to carbon emissions. Train travel offers scenic routes and reduced environmental impact. Overland travel by bus or car provides flexibility and opportunities for spontaneous exploration. Accommodation choices range from budget hostels to luxury resorts, each offering distinct experiences and price points. Travel ultimately transforms individuals by challenging assumptions, expanding worldviews, and creating connections across geographical and cultural boundaries.",
        "Advanced": "The anthropology of travel reveals complex motivations underlying human mobility and the profound impacts of tourism on both travelers and host communities. Contemporary travel encompasses diverse paradigms from mass tourism to transformative journeys focused on personal growth and cultural immersion. The tourism industry constitutes a significant component of global economic activity, generating employment and revenue while simultaneously raising concerns about sustainability, cultural commodification, and environmental degradation. The concept of sustainable tourism addresses the ecological footprint of travel. Climate change implications of aviation, overtourism's impact on fragile ecosystems, and resource consumption in tourist destinations necessitate thoughtful approaches. Responsible travelers minimize environmental impact through conscious transportation choices, supporting eco-certified accommodations, and respecting natural habitats. Community-based tourism initiatives empower local populations and distribute economic benefits more equitably. Cultural tourism presents both opportunities and challenges. While facilitating intercultural understanding and preserving heritage sites through economic incentives, tourism can also lead to cultural commodification where authentic practices become performative displays for commercial purposes. The tension between preservation and commercialization remains an ongoing concern in cultural heritage management. Travel writing and documentation shape collective understanding of places and peoples. Historical travel narratives often reflected colonial perspectives and orientalist frameworks that exoticized and misrepresented non-Western cultures. Contemporary travel discourse increasingly emphasizes respectful representation, avoiding stereotypes, and acknowledging power dynamics inherent in tourist-host relationships. Globalization has transformed travel accessibility and patterns. Budget airlines democratized international travel, while digital technologies facilitate planning, navigation, and documentation. However, this accessibility concentrates tourist flows toward popular destinations, exacerbating overtourism challenges in places like Venice, Barcelona, and certain Southeast Asian islands. The psychology of travel examines how journeys influence identity formation and perspective transformation. Immersive travel experiences can catalyze personal development by challenging preconceptions, fostering adaptability, and cultivating cultural intelligence. Extended travel or living abroad demonstrably enhances cognitive flexibility and creative thinking. Understanding travel requires recognizing it as a complex phenomenon shaped by economic forces, cultural exchanges, environmental considerations, and individual psychological processes, with implications extending far beyond simple leisure activity."
    },
    "Unit 8": {
        "title": "Unit 8 - Career and Professional Life",
        "Beginner": "Choosing a career is an important decision. A career is the work we do for many years. There are many different types of jobs. Doctors and nurses work in hospitals and help sick people get better. They study medicine for many years. Teachers work in schools. They help students learn reading, writing, math, and many other subjects. Teachers need to be patient and kind. Engineers design and build things like bridges, buildings, and machines. They use math and science in their work. Police officers and firefighters keep people safe. They are brave and help during emergencies. Artists and musicians create beautiful paintings, sculptures, or music. They need creativity and practice. Chefs work in restaurants and cook delicious meals. They need to know about different foods and recipes. Farmers grow food like vegetables, fruits, and grains. They work hard outdoors and take care of plants and animals. Office workers help companies run smoothly. They use computers and phones for their jobs. Some people work in stores and help customers find what they need. Others deliver mail or packages to homes and businesses. To prepare for a career, students need to work hard in school. Reading, writing, and math are important for almost every job. Some careers need special training or college education. People can also learn skills through practice and experience. It is good to think about what you enjoy doing. If you like helping people, you might become a doctor or teacher. If you enjoy building things, engineering might be good. If you love animals, you could be a veterinarian. Everyone has different talents and interests. Finding the right career makes work enjoyable and meaningful.",
        "Intermediate": "Career development constitutes a crucial aspect of adult life, influencing financial stability, personal identity, and life satisfaction. The contemporary job market requires strategic planning, continuous skill development, and adaptability to changing economic conditions. Educational preparation varies significantly across professions. Traditional careers in medicine, law, and engineering require extensive formal education including undergraduate degrees, graduate programs, and professional certifications. Medical professionals complete four years of medical school followed by residency training lasting three to seven years depending on specialization. Legal careers require law school and passing bar examinations. The technology sector has transformed career landscapes dramatically. Software development, data science, and cybersecurity represent rapidly growing fields with substantial demand. These careers often prioritize demonstrable skills and portfolio work over traditional credentials, though computer science degrees remain valuable. Entrepreneurship appeals to individuals seeking autonomy and creative control. Starting businesses requires business acumen, risk tolerance, and persistent effort. While potentially rewarding, entrepreneurship involves financial uncertainty and demanding workloads. Successful entrepreneurs identify market needs, develop innovative solutions, and build effective teams. Professional development involves continuous learning throughout careers. Technological advancement, industry evolution, and changing best practices necessitate ongoing skill acquisition. Professional conferences, workshops, online courses, and industry certifications help workers remain competitive and advance in their fields. Work-life balance has gained prominence in career discussions. Traditional career trajectories emphasizing constant availability and prioritizing work over personal life increasingly face criticism. Many professionals now seek positions offering flexible schedules, remote work options, and respect for personal time. Networking significantly influences career advancement. Professional relationships facilitate knowledge exchange, collaboration opportunities, and job leads. Industry associations, alumni networks, and professional social media platforms enable connection with colleagues and mentors. Career transitions have become increasingly common. Individuals change careers multiple times throughout working lives, pursuing new interests, responding to market changes, or seeking better compensation. Transferable skills facilitate these transitions, allowing professionals to apply competencies across different contexts.",
        "Advanced": "The sociology of work and career trajectories reveals how professional life intersects with broader economic structures, social identities, and individual agency. Contemporary career dynamics reflect tensions between traditional employment models and emerging work arrangements, shaped by technological disruption, globalization, and evolving organizational structures. The decline of lifelong employment with single organizations has fundamentally altered career paradigms. Rather than linear progression within hierarchical organizations, contemporary careers often follow non-linear paths involving lateral moves, industry transitions, and portfolio careers combining multiple income streams. This shift places greater responsibility on individuals for career management while reducing job security and institutional support. Credentialism—the increasing emphasis on educational credentials for employment—has intensified across sectors. Educational attainment correlates strongly with lifetime earnings and career opportunities. However, this trend raises concerns about accessibility and equity, as advanced degrees require substantial financial investment and time commitments that disproportionately burden certain populations. The gig economy represents a significant structural shift in employment relationships. Platform-based work offers flexibility and autonomy but often lacks benefits, job security, and labor protections associated with traditional employment. Debates continue regarding worker classification, rights, and the future of work in platform capitalism. Artificial intelligence and automation pose both opportunities and challenges for career planning. While technological advancement creates new roles requiring sophisticated skills, it simultaneously threatens to automate routine cognitive and manual tasks. Career resilience requires adaptability, continuous learning, and cultivation of distinctly human capabilities including creativity, emotional intelligence, and complex problem-solving. Professional identity formation involves integrating work roles into broader self-concepts. Careers provide not merely income but meaning, social status, and self-actualization opportunities. The psychological contract between employers and employees—mutual expectations regarding obligations and contributions—profoundly affects job satisfaction and organizational commitment. Gender, race, and socioeconomic background significantly influence career trajectories through mechanisms including discrimination, differential access to networks and mentorship, and systemic barriers. Addressing workplace equity requires institutional reforms, inclusive policies, and critical examination of organizational cultures and hiring practices. Understanding careers requires recognizing them as complex phenomena shaped by individual agency, structural constraints, technological forces, and cultural values, with profound implications for personal well-being and social organization."
    }
}


# ============================================================================
# 1. FIREBASE INITIALIZATION (Lazy Loading) - 기존 유지
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
# 2. UTILITY FUNCTIONS
# ============================================================================

def authenticate_teacher(email, password):
    """
    Firebase Authentication으로 교사 인증 (기존 함수 유지)
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
        doc = db.collection("readfit_assignments").document(code).get()
        return doc.exists
    except Exception as e:
        st.error(f"데이터베이스 오류: {e}")
        return False


def logout():
    """로그아웃 처리"""
    st.session_state.clear()
    st.rerun()


# ============================================================================
# 3. QUIZ & MISSION FUNCTIONS
# ============================================================================

def generate_simple_quiz(text_content, unit_title, difficulty):
    """
    지문을 기반으로 3가지 객관식 퀴즈 문제를 생성합니다.
    (ReadFit용 간단한 퀴즈)
    """
    difficulty_label = "Beginner" if "Beginner" in difficulty else "Intermediate" if "Intermediate" in difficulty else "Advanced"
    
    quiz_questions = {
        "Unit 1 - My Lifelogging": {
            "Beginner": [
                {
                    "question": "What does Harin like to do?",
                    "options": ["She likes to run", "She likes to swim", "She likes to dance"],
                    "answer": 0
                },
                {
                    "question": "What does Mike post on social media?",
                    "options": ["Food pictures", "Pictures of his clothes", "Travel photos"],
                    "answer": 1
                },
                {
                    "question": "What is Elena's favorite snack?",
                    "options": ["Cookies", "Donuts", "Ice cream"],
                    "answer": 1
                }
            ],
            "Intermediate": [
                {
                    "question": "What information does Harin's running app record?",
                    "options": ["Only distance", "Speed, time, and steps", "Only calories"],
                    "answer": 1
                },
                {
                    "question": "How does Mike describe his fashion photos?",
                    "options": ["His fashion diary", "His hobby collection", "His art project"],
                    "answer": 0
                },
                {
                    "question": "What app does Elena use to find donut shops?",
                    "options": ["A social media app", "A map app", "A food review app"],
                    "answer": 1
                }
            ],
            "Advanced": [
                {
                    "question": "What does Harin's tracking method exemplify?",
                    "options": ["Traditional fitness training", "The quantified self-movement", "Competitive sports preparation"],
                    "answer": 1
                },
                {
                    "question": "What does Mike's fashion documentation represent?",
                    "options": ["Simple photography practice", "Artistic self-expression and identity construction", "Professional fashion design"],
                    "answer": 1
                },
                {
                    "question": "What contemporary phenomenon does Elena's activity exemplify?",
                    "options": ["Traditional restaurant dining", "Food-focused lifelogging", "Professional food criticism"],
                    "answer": 1
                }
            ]
        },
        "Unit 2 - Fun School Events Around the World": {
            "Beginner": [
                {
                    "question": "How far do students run on Cross Country Race Day in New Zealand?",
                    "options": ["2 kilometers", "4 kilometers", "6 kilometers"],
                    "answer": 1
                },
                {
                    "question": "When is National Language Month in the Philippines?",
                    "options": ["July", "August", "September"],
                    "answer": 1
                },
                {
                    "question": "What instrument will the student play in the USA concert?",
                    "options": ["Piano", "Violin", "Guitar"],
                    "answer": 1
                }
            ],
            "Intermediate": [
                {
                    "question": "What does the cross country course in New Zealand have?",
                    "options": ["Flat roads only", "Small hills and lots of trees", "Swimming sections"],
                    "answer": 1
                },
                {
                    "question": "How many languages are spoken in the Philippines?",
                    "options": ["Over 50", "Over 100", "Over 200"],
                    "answer": 1
                },
                {
                    "question": "What is the topic of Korea's digital writing contest?",
                    "options": ["Summer vacation", "School campus in spring", "Family traditions"],
                    "answer": 1
                }
            ],
            "Advanced": [
                {
                    "question": "What does cross country running cultivate besides physical stamina?",
                    "options": ["Only speed improvement", "Mental resilience and strategic pacing abilities", "Dancing skills"],
                    "answer": 1
                },
                {
                    "question": "What do the Filipino language events serve to do?",
                    "options": ["Replace English education", "Preserve and promote linguistic heritage", "Teach foreign languages"],
                    "answer": 1
                },
                {
                    "question": "What skills does Korea's digital writing contest develop?",
                    "options": ["Only writing skills", "Digital literacy, creative writing, and visual composition", "Only photography skills"],
                    "answer": 1
                }
            ]
        },
        "Unit 3 - The Power of Small Acts": {
            "Beginner": [
                {
                    "question": "Where did Jimin and Sora go?",
                    "options": ["To the zoo", "To the amusement park", "To the museum"],
                    "answer": 1
                },
                {
                    "question": "What hit Jimin's back on the subway?",
                    "options": ["A ball", "A backpack", "An umbrella"],
                    "answer": 1
                },
                {
                    "question": "What did the girls buy in the gift shop?",
                    "options": ["T-shirts", "Hairbands with rabbit ears", "Toys"],
                    "answer": 1
                }
            ],
            "Intermediate": [
                {
                    "question": "What happened when they stood in line for the roller coaster?",
                    "options": ["Someone cut in line", "The ride broke down", "They gave up waiting"],
                    "answer": 0
                },
                {
                    "question": "Who held the door for the girls at the gift shop?",
                    "options": ["A store employee", "A nice man", "Their friend"],
                    "answer": 1
                },
                {
                    "question": "Why couldn't Jimin and Sora see the stage at the magic show?",
                    "options": ["They arrived late", "Two boys with rabbit ears sat in front", "The lights were off"],
                    "answer": 1
                }
            ],
            "Advanced": [
                {
                    "question": "What public service announcement was made on the subway?",
                    "options": ["Stand behind the yellow line", "Wear your backpack on the front", "Give up seats to elderly"],
                    "answer": 1
                },
                {
                    "question": "What did Jimin conclude about small acts?",
                    "options": ["They don't matter much", "They possess substantial power to influence others", "They only affect yourself"],
                    "answer": 1
                },
                {
                    "question": "What does the story emphasize about considerate conduct?",
                    "options": ["It's only important at home", "It contributes to collective well-being and social cohesion", "It's unnecessary in public"],
                    "answer": 1
                }
            ]
        },
        "Unit 4 - My Family Tradition": {
            "Beginner": [
                {
                    "question": "Where is Yubin's father from?",
                    "options": ["Korea", "India", "China"],
                    "answer": 1
                },
                {
                    "question": "When does Yubin's family go to the baseball park?",
                    "options": ["Every spring", "Every summer", "Every winter"],
                    "answer": 0
                },
                {
                    "question": "What game does the family play after dinner?",
                    "options": ["Chess", "Pachisi", "Cards"],
                    "answer": 1
                }
            ],
            "Intermediate": [
                {
                    "question": "What are both of Yubin's parents' jobs?",
                    "options": ["Teachers", "Computer engineers", "Doctors"],
                    "answer": 1
                },
                {
                    "question": "What is Yubin's father's favorite dish?",
                    "options": ["Korean kimchi", "Indian chicken curry", "Chinese noodles"],
                    "answer": 1
                },
                {
                    "question": "Where does the special curry powder come from?",
                    "options": ["A local store", "Yubin's grandmother in India", "A restaurant"],
                    "answer": 1
                }
            ],
            "Advanced": [
                {
                    "question": "What does opening day attendance represent for the family?",
                    "options": ["Just entertainment", "A familial bonding experience and celebration of Korean cultural participation", "A business meeting"],
                    "answer": 1
                },
                {
                    "question": "What functions does the game pachisi serve?",
                    "options": ["Only entertainment", "Entertainment, strategic thinking development, and cultural transmission", "Physical exercise"],
                    "answer": 1
                },
                {
                    "question": "What do family traditions provide according to the passage?",
                    "options": ["Only fun memories", "Continuity, meaning, and a sense of belonging", "Extra work for family members"],
                    "answer": 1
                }
            ]
        }
    }
    
    # 기본값 제공
    if unit_title not in quiz_questions:
        return [
            {
                "question": f"What is the main topic of {unit_title}?",
                "options": ["Option 1", "Option 2", "Option 3"],
                "answer": 0
            },
            {
                "question": "What is the key content of the passage?",
                "options": ["Content 1", "Content 2", "Content 3"],
                "answer": 0
            },
            {
                "question": "What is important regarding this topic?",
                "options": ["Perspective 1", "Perspective 2", "Perspective 3"],
                "answer": 0
            }
        ]
    
    return quiz_questions.get(unit_title, {}).get(difficulty_label, [])


def get_mission_info():
    """미션 정보 반환"""
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
    return missions


# ============================================================================
# 4. STEP FUNCTIONS FOR 4-STEP FLOW
# ============================================================================

def show_step1_quiz(assignment_data):
    """Step 1: 퀴즈 풀기"""
    st.header("Step 1️⃣ 퀴즈 풀기")
    
    # 지문을 session_state에 저장 (다른 활동에서 사용)
    st.session_state.reading_text = assignment_data.get("text", "")
    
    st.subheader("📖 지문")
    st.text_area(
        "지문 내용",
        value=assignment_data.get("text", ""),
        height=150,
        disabled=True,
        key="quiz_text_display"
    )
    
    st.divider()
    st.subheader("❓ 객관식 문제")
    
    quiz_questions = assignment_data.get("quiz", [])
    
    if not quiz_questions:
        st.error("퀴즈 데이터를 불러올 수 없습니다.")
        return None
    
    # quiz_answers 초기화 (처음에만)
    if 'quiz_answers' not in st.session_state:
        st.session_state.quiz_answers = []
    
    # 새로운 quiz라면 초기화
    if len(st.session_state.quiz_answers) != len(quiz_questions):
        st.session_state.quiz_answers = []
    
    for idx, q in enumerate(quiz_questions):
        st.write(f"**{idx+1}. {q['question']}**")
        answer = st.radio(
            "정답 선택",
            options=q['options'],
            key=f"quiz_{idx}"
        )
        
        # quiz_answers 리스트 업데이트
        if idx >= len(st.session_state.quiz_answers):
            st.session_state.quiz_answers.append({})
        
        st.session_state.quiz_answers[idx] = {
            "question": q['question'],
            "selected": answer,
            "correct": q['options'][q['answer']],
            "is_correct": answer == q['options'][q['answer']]
        }
        st.divider()
    
    if st.button("✅ 정답 제출하기", use_container_width=True, key="submit_quiz"):
        correct_count = sum(1 for a in st.session_state.quiz_answers if a['is_correct'])
        total_count = len(st.session_state.quiz_answers)
        score = int((correct_count / total_count) * 100) if total_count > 0 else 0
        
        st.session_state.quiz_score = score
        st.session_state.quiz_correct = correct_count
        st.session_state.quiz_total = total_count
        st.session_state.step = 2
        st.success(f"✅ 제출 완료! 점수: {score}점 ({correct_count}/{total_count})")
        st.rerun()


def show_step2_mission_selection(quiz_score):
    """Step 2: 미션 선택"""
    st.header("Step 2️⃣ 활동 선택")
    
    st.info(f"📊 **당신의 퀴즈 점수: {quiz_score}점**")
    
    if quiz_score >= 80:
        recommended_mission = "베스트셀러 작가 (상)"
        recommended_id = "writer"
    elif quiz_score >= 60:
        recommended_mission = "미스터리 스무고개 (중)"
        recommended_id = "mystery_20_questions"
    else:
        recommended_mission = "이미지 탐정 (하)"
        recommended_id = "image_detective"
    
    st.write(f"🤖 **AI 추천**: {recommended_mission}")
    st.divider()
    
    missions = get_mission_info()
    cols = st.columns(3)
    
    for idx, mission in enumerate(missions):
        with cols[idx]:
            is_recommended = mission['id'] == recommended_id
            
            if is_recommended:
                st.markdown(
                    f"""<div style="border: 3px solid #FFD700; border-radius: 12px; padding: 16px; text-align: center; background: rgba(255, 215, 0, 0.1);">
                        <div style="font-size: 40px; margin-bottom: 8px;">{mission['emoji']}</div>
                        <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">{mission['title']}</div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;">난이도: {mission['difficulty']}</div>
                        <div style="font-size: 13px; margin-bottom: 12px;">{mission['description']}</div>
                        <div style="background: #FFD700; color: black; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; display: inline-block; margin-bottom: 12px;">👍 AI 추천</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""<div style="border: 2px solid #e2e8f0; border-radius: 12px; padding: 16px; text-align: center;">
                        <div style="font-size: 40px; margin-bottom: 8px;">{mission['emoji']}</div>
                        <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">{mission['title']}</div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;">난이도: {mission['difficulty']}</div>
                        <div style="font-size: 13px;">{mission['description']}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            if st.button(f"선택하기", key=f"mission_{mission['id']}", use_container_width=True):
                st.session_state.selected_mission = mission['id']
                st.session_state.selected_mission_title = mission['title']
                st.session_state.step = 3
                st.rerun()


# ============================================================================
# [수정] Step 3: 이미지 탐정 전용 함수 (독립 함수로 분리)
# ============================================================================
def show_step3_image_detective():
    """Step 3: 이미지 탐정 활동 - 장면 묘사 문장 선택 1문제"""
    st.subheader("🎨 이미지 탐정")
    st.write("**AI가 그린 장면을 가장 잘 묘사한 문장을 고르세요!**")
    
    # 세션 초기화
    if "detective_sentence_data" not in st.session_state:
        text = st.session_state.get("reading_text", "The dog runs in the park.")
        with st.spinner("🤖 AI가 문제를 만들고 있어요..."):
            # 1) 지문 전체를 입력으로 핵심 장면 요약 문장 1개 생성
            try:
                api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
                if api_key:
                    client = OpenAI(api_key=api_key)
                    core_resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{
                            "role": "user",
                            "content": (
                                "From the following passage, write ONE short, literal English sentence (S+V+O) that best describes the single core scene that can be illustrated for young learners.\n\n"
                                f"Passage:\n{text}\n\n"
                                "Rules:\n- Use only what the passage explicitly states.\n- Keep under 12 words.\n- No extra details, no proper nouns unless present.\n- Return ONLY the sentence, nothing else."
                            )
                        }],
                        temperature=0.2
                    )
                    correct_sentence = (core_resp.choices[0].message.content or "").strip().strip('"')
                else:
                    # API 미사용 시: 첫 문장을 기반으로 사용
                    sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
                    correct_sentence = sentences[0] if sentences else "The dog runs in the park."
            except Exception as e:
                st.warning(f"핵심 장면 문장 생성 실패: {e}")
                sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
                correct_sentence = sentences[0] if sentences else "The dog runs in the park."

            # 2) 오답 3개 생성 후 품질/중복 필터링
            distractors_raw = get_sentence_distractors(correct_sentence, text)
            candidates = [
                (distractors_raw.get("subject_wrong", "The girl is running to school."), "subject_wrong"),
                (distractors_raw.get("verb_wrong", "The boy is walking to school."), "verb_wrong"),
                (distractors_raw.get("object_wrong", "The boy is running to the park."), "object_wrong"),
            ]

            def is_sensible(s: str) -> bool:
                if not s:
                    return False
                words = s.split()
                if len(words) < 3 or len(words) > 16:
                    return False
                if not any(ch.isalpha() for ch in s):
                    return False
                return True

            # 중복/정답 동일/비정상 문장 제거
            seen = set([correct_sentence.strip().lower()])
            filtered = []
            for sent, kind in candidates:
                norm = (sent or "").strip().strip('"').rstrip('.').lower()
                corr_norm = correct_sentence.strip().rstrip('.').lower()
                if not is_sensible(sent):
                    continue
                if norm == corr_norm:
                    continue
                if norm in seen:
                    continue
                seen.add(norm)
                filtered.append((sent.strip().strip('"'), kind))

            # 부족하면 안전한 기본 오답으로 채우되 중복 방지
            fallbacks = [
                ("The girl is running to school.", "fallback_subject"),
                ("The boy is walking to school.", "fallback_verb"),
                ("The boy is running to the park.", "fallback_object"),
            ]
            for sent, kind in fallbacks:
                if len(filtered) >= 3:
                    break
                norm = sent.rstrip('.').lower()
                if norm not in seen and is_sensible(sent):
                    seen.add(norm)
                    filtered.append((sent, kind))

            # 최종 4개 선택지 구성 (정답 + 3 오답), 모두 상이 보장
            options_with_types = [(correct_sentence, "correct")] + filtered[:3]
            random.shuffle(options_with_types)

            # 3) 이미지 생성은 correct_sentence만 사용
            image_result = generate_image_with_dalle("", correct_sentence)

            # 데이터 저장
            st.session_state.detective_sentence_data = {
                "correct_sentence": correct_sentence,
                "image": image_result,
                "options": [opt[0] for opt in options_with_types],
                "option_types": {opt[0]: opt[1] for opt in options_with_types}
            }
    
    data = st.session_state.detective_sentence_data
    
    # 이미지 표시
    if data["image"]:
        try:
            st.image(data["image"], caption="이 장면을 가장 잘 나타내는 문장은?", use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ 이미지를 로드할 수 없습니다. ({str(e)})")
    else:
        st.warning("⚠️ 이미지를 준비하지 못했습니다.")
    
    st.divider()
    st.write("**아래 문장 중 정답을 선택하세요:**")
    
    # 4개 선택지 버튼 (2x2 배치)
    for idx in range(0, 4, 2):
        col1, col2 = st.columns(2)
        with col1:
            if idx < len(data["options"]):
                option = data["options"][idx]
                if st.button(f"{chr(65+idx)}. {option}", key=f"detect_sent_{idx}", use_container_width=True):
                    correct = data["correct_sentence"]
                    answer_type = data["option_types"].get(option, "unknown")
                    
                    # 정답 체크
                    if option == correct:
                        st.session_state.activity_score = 100
                        st.success("🎉 정답입니다!")
                    else:
                        st.session_state.activity_score = 30
                        st.error(f"❌ 틀렸습니다. 정답은 '{correct}'입니다.")
                    
                    # 리포트용 데이터 저장
                    st.session_state.detective_target = correct
                    st.session_state.detective_answer = option
                    st.session_state.detective_answer_type = answer_type
                    
                    # 초기화
                    st.session_state.detective_sentence_data = None
                    
                    st.session_state.step = 4
                    st.rerun()
        
        with col2:
            if idx + 1 < len(data["options"]):
                option = data["options"][idx + 1]
                if st.button(f"{chr(65+idx+1)}. {option}", key=f"detect_sent_{idx+1}", use_container_width=True):
                    correct = data["correct_sentence"]
                    answer_type = data["option_types"].get(option, "unknown")
                    
                    # 정답 체크
                    if option == correct:
                        st.session_state.activity_score = 100
                        st.success("🎉 정답입니다!")
                    else:
                        st.session_state.activity_score = 30
                        st.error(f"❌ 틀렸습니다. 정답은 '{correct}'입니다.")
                    
                    # 리포트용 데이터 저장
                    st.session_state.detective_target = correct
                    st.session_state.detective_answer = option
                    st.session_state.detective_answer_type = answer_type
                    
                    # 초기화
                    st.session_state.detective_sentence_data = None
                    
                    st.session_state.step = 4
                    st.rerun()


# ============================================================================
# [수정] 통합 활동 관리 함수
# ============================================================================
def show_step3_activity(selected_mission):
    """Step 3: 활동 수행 메인 함수"""
    st.header("Step 3️⃣ 활동 수행")
    
    if selected_mission == "image_detective":
        show_step3_image_detective()
        
    elif selected_mission == "mystery_20_questions":
        st.subheader("🕵️ 미스터리 스무고개")
        st.write("💡 **빈칸에 들어갈 단어를 맞춰보세요!**")
        
        # 세션 초기화
        if "mystery_target_word" not in st.session_state or st.session_state.mystery_target_word is None:
            # 지문에서 단어 추출 (간단히 공백 기준 분리)
            text = st.session_state.get("reading_text", "The dog is a friendly animal.")
            words = [w.strip('.,!?;:"()[]') for w in text.split() if len(w.strip('.,!?;:"()[]')) > 3]
            target = random.choice(words) if words else "dog"
            
            st.session_state.mystery_target_word = target
            st.session_state.mystery_text_with_blank = text.replace(target, "[ ❓ ]", 1)
            st.session_state.mystery_hint_level = 0  # 0: 숨김, 1~10: 단계별 힌트
        
        # 빈칸이 있는 지문 표시
        st.info(st.session_state.mystery_text_with_blank)
        
        st.divider()
        
        # 힌트 버튼
        if st.session_state.mystery_hint_level < 10:
            if st.button("💡 힌트 보기", key="mystery_hint_btn"):
                st.session_state.mystery_hint_level += 1
                st.rerun()
        
        # 힌트 표시 (10단계)
        target_word = st.session_state.mystery_target_word
        hint_level = st.session_state.mystery_hint_level
        
        if hint_level > 0:
            st.success(f"**힌트 1:** 이 단어는 지문에 나온 중요한 단어입니다.")
        if hint_level > 1:
            st.success(f"**힌트 2:** 단어의 길이는 {len(target_word)}글자입니다.")
        if hint_level > 2 and len(target_word) > 0:
            st.success(f"**힌트 3:** 첫 글자는 '{target_word[0].upper()}'입니다.")
        if hint_level > 3 and len(target_word) > 1:
            st.success(f"**힌트 4:** 마지막 글자는 '{target_word[-1].lower()}'입니다.")
        if hint_level > 4 and len(target_word) > 2:
            st.success(f"**힌트 5:** 두 번째 글자는 '{target_word[1].lower()}'입니다.")
        if hint_level > 5:
            vowels = [c for c in target_word.lower() if c in 'aeiou']
            st.success(f"**힌트 6:** 이 단어에는 모음이 {len(vowels)}개 있습니다.")
        if hint_level > 6 and len(target_word) > 3:
            revealed = target_word[0] + '_' * (len(target_word) - 2) + target_word[-1]
            st.success(f"**힌트 7:** 단어 패턴: {revealed}")
        if hint_level > 7 and len(target_word) > 2:
            mid_char = target_word[len(target_word)//2]
            st.success(f"**힌트 8:** 가운데 글자는 '{mid_char.lower()}'입니다.")
        if hint_level > 8:
            revealed = ''.join([c if i % 2 == 0 else '_' for i, c in enumerate(target_word)])
            st.success(f"**힌트 9:** 더 많은 글자: {revealed}")
        if hint_level > 9:
            st.success(f"**정답:** {target_word}")
        
        st.divider()
        
        # 답 입력
        answer = st.text_input("정답을 입력하세요:", key="mystery_answer_input")
        if st.button("정답 제출하기", use_container_width=True, key="submit_mystery"):
            target = st.session_state.mystery_target_word
            if target and answer.strip().lower() == target.lower():
                st.session_state.activity_score = 100
                st.success(f"🎉 정답입니다! '{target}'")
            else:
                st.session_state.activity_score = 50
                st.error(f"❌ 틀렸습니다. 정답은 '{target}'입니다.")
            
            st.session_state.activity_answer = answer
            st.session_state.mystery_target_word = None  # 초기화
            st.session_state.step = 4
            st.rerun()
            
    elif selected_mission == "writer":
        st.subheader("✍️ 베스트셀러 작가")
        
        # 세션 초기화
        if "writer_keywords" not in st.session_state:
            # 지문에서 키워드 3개 추출 (간단히 긴 단어 3개)
            text = st.session_state.get("reading_text", "The dog runs in the park.")
            words = [w.strip('.,!?;:"()[]') for w in text.split() if len(w.strip('.,!?;:"()[]')) > 3]
            keywords = random.sample(words, min(3, len(words))) if words else ["dog", "runs", "park"]
            st.session_state.writer_keywords = keywords
        
        st.write("✍️ **다음 키워드를 사용해서 이야기를 만들어보세요!**")
        st.info(f"**키워드:** {', '.join(st.session_state.writer_keywords)}")
        
        st.caption("(50자 이상 작성 권장)")
        story = st.text_area(
            "이야기 작성",
            height=200,
            placeholder="키워드를 사용해서 이야기를 작성하세요...",
            key="writer_story_input"
        )
        
        if st.button("작품 제출하기", use_container_width=True, key="submit_writer"):
            if len(story.strip()) < 10:
                st.error("최소 10자 이상 작성해주세요.")
            else:
                st.session_state.activity_answer = story
                st.session_state.activity_score = 85
                # 이번 제출에서 사용한 키워드 보존
                st.session_state.writer_keywords_used = st.session_state.get("writer_keywords", [])
                st.session_state.writer_keywords = None  # 초기화
                st.session_state.step = 4
                st.rerun()


def show_step4_report(quiz_score, activity_score, selected_mission_title):
    """Step 4: 최종 리포트"""
    st.header("Step 4️⃣ 최종 리포트")
    
    # 분석 리포트 변수 초기화 (예외 발생 시에도 참조 가능하도록)
    insights = None
    
    # Firestore에 결과 저장
    try:
        db = get_firestore_client()
        
        # mission_id 결정
        if selected_mission_title == "🎨 이미지 탐정":
            mission_id = "image_detective"
        elif selected_mission_title == "🕵️ 미스터리 스무고개":
            mission_id = "mystery_20_questions"
        elif selected_mission_title == "✍️ 베스트셀러 작가":
            mission_id = "writer"
        else:
            mission_id = "unknown"
        
        # 기본 데이터
        submission_data = {
            "student_name": st.session_state.get("student_name") or st.session_state.get("user_name", "Anonymous"),
            "access_code": st.session_state.get("current_access_code", "N/A"),
            "timestamp": datetime.now(),
            "quiz_score": quiz_score,
            "activity_score": activity_score,
            "total_score": int((quiz_score * 0.4 + activity_score * 0.6)),
            "mission_id": mission_id,
            "quiz_correct": st.session_state.get("quiz_correct", 0),
            "quiz_total": st.session_state.get("quiz_total", 0),
        }
        
        # mission_details: 미션 타입별 상세 정보
        mission_details = {}
        
        if mission_id == "image_detective":
            mission_details = {
                "result_type": st.session_state.get("detective_answer_type", "unknown"),
                "target_word": st.session_state.get("detective_target", ""),
                "student_answer": st.session_state.get("detective_answer", ""),
                "interpretation_lens": st.session_state.get("detective_interpretation_lens", "사물"),
            }
        
        elif mission_id == "mystery_20_questions":
            mission_details = {
                "hints_used": st.session_state.get("mystery_hint_level", 0),
                "target_word": st.session_state.get("mystery_target_word", ""),
                "student_answer": st.session_state.get("activity_answer", ""),
            }
        
        elif mission_id == "writer":
            mission_details = {
                "student_text": st.session_state.get("activity_answer", ""),
                "keywords_used": st.session_state.get("writer_keywords_used", []),
            }
        
        submission_data["mission_details"] = mission_details

        # OpenAI 학습 분석 리포트 생성 (저장 전에 먼저 생성)
        try:
            with st.spinner("🧠 학습 분석 리포트를 생성 중..."):
                insights = generate_report_insights_with_openai(submission_data, mission_details)
        except Exception as e:
            st.warning(f"리포트 생성 중 오류: {str(e)}")
            insights = None
        
        # 실패/예외 시 Fallback (항상 유효한 insights 보장)
        if not insights:
            st.warning("⚠️ AI 분석 리포트 생성 실패 - 기본 피드백을 사용합니다.")
            insights = {
                "one_line_feedback": "오늘 활동에 성실히 참여해서 정말 잘했어요! 다음에는 그림을 더 자세히 관찰하며 단어의 의미를 생각해보는 연습을 해보세요."
            }
        
        # 분석 결과를 저장에 포함 (insights 생성 후)
        submission_data["report_insights"] = insights
        submission_data["report_insights_model"] = "gpt-4o-mini"

        # Firestore 저장
        db.collection("readfit_submissions").add(submission_data)
        
        st.toast("✅ 선생님께 결과가 전송되었습니다!")
    
    except Exception as e:
        st.warning(f"⚠️ 결과 저장 중 오류: {str(e)}")
    
    total_score = int((quiz_score * 0.4 + activity_score * 0.6))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📝 퀴즈 점수", f"{st.session_state.quiz_score}점")
    
    with col2:
        st.metric("🎯 활동 점수", f"{activity_score}점")
    
    with col3:
        st.metric("⭐ 최종 점수", f"{total_score}점")
    
    st.balloons()
    
    st.divider()
    
    st.markdown(
        f"""<div style="text-align: center; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 12px; color: white;">
            <div style="font-size: 48px; margin-bottom: 16px;">🎉</div>
            <div style="font-size: 28px; font-weight: bold; margin-bottom: 8px;">참 잘했어요!</div>
            <div style="font-size: 16px; margin-bottom: 16px;">오늘 학습을 완료했습니다!</div>
            <div style="font-size: 14px;">선택한 활동: {selected_mission_title}</div>
        </div>""",
        unsafe_allow_html=True
    )
    
    st.divider()
    
    st.subheader("📊 오늘의 학습 요약")
    
    # 이미지 탐정 미션 오답 유형 분석
    if selected_mission_title == "🎨 이미지 탐정" and hasattr(st.session_state, "detective_answer_type"):
        answer_type = st.session_state.detective_answer_type
        
        st.markdown("**📈 상세 분석:**")
        
        if answer_type == "correct":
            st.success("✅ 정답을 정확히 맞췄습니다! 단어와 이미지를 잘 연결했어요.")
        elif answer_type == "semantic":
            st.info("🔍 **의미적 오답**: 비슷한 의미의 단어를 선택했어요.")
            st.caption("💡 **학습 팁**: 단어의 정확한 의미 차이를 공부해보세요. 비슷해 보이지만 다른 뜻을 가진 단어들이 많아요!")
        elif answer_type == "spelling":
            wrong_word = st.session_state.get('detective_wrong_answer', '')
            correct_word = st.session_state.get('detective_word', '')
            st.info("📝 **철자적 오답**: 철자가 비슷한 단어를 선택했어요.")
            st.caption(f"💡 **학습 팁**: 단어를 소리 내어 읽고 철자를 주의 깊게 확인해보세요. '{wrong_word}' vs '{correct_word}'의 철자 차이를 눈여겨보세요!")
        elif answer_type == "random":
            st.info("🤔 **랜덤 오답**: 전혀 관계없는 단어를 선택했어요.")
            st.caption("💡 **학습 팁**: 이미지를 더 자세히 관찰해보세요. 그림 속 힌트들을 놓치지 마세요!")
        
        st.divider()

    # OpenAI 학습 분석 리포트 출력 섹션 (한 줄 평)
    try:
        st.subheader("👏 선생님의 한 마디")
        if insights and insights.get("one_line_feedback"):
            st.success(insights["one_line_feedback"])
        else:
            st.info("분석 리포트를 생성하지 못했습니다. 다음 학습으로 핵심 단어 복습과 예문 작성부터 시도해보세요.")
    except Exception:
        st.info("분석 리포트 표시 중 문제가 발생했습니다. 다음 학습으로 핵심 단어 복습을 권장합니다.")
    
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.write("✅ **완료한 활동:**")
        st.write(f"• 퀴즈: {st.session_state.quiz_correct}/{st.session_state.quiz_total} 정답")
        st.write(f"• {selected_mission_title} 완료")
    
    with summary_col2:
        st.write("📈 **학습 결과:**")
        st.write(f"• 총 점수: **{total_score}점**")
        if total_score >= 80:
            st.write("• 레벨: 🌟 우수")
        elif total_score >= 60:
            st.write("• 레벨: ⭐ 좋음")
        else:
            st.write("• 레벨: 🔄 다시 도전")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏠 메인으로 돌아가기", use_container_width=True, key="back_to_main"):
            st.session_state.step = 1
            st.rerun()
    
    with col2:
        if st.button("🔄 다시 풀기", use_container_width=True, key="retry"):
            st.session_state.step = 1
            st.rerun()


# ============================================================================
# 5. LOGIN PAGE
# ============================================================================

def show_login_page():
    """로그인 페이지 표시"""
    apply_global_styles()
    
    st.markdown("<div class='login-hero'><h1>📚 ReadFit</h1></div>", unsafe_allow_html=True)
    st.markdown("<div class='login-sub'>영어 학습 플랫폼 - 퀴즈 & 활동으로 영어 실력 UP!</div>", unsafe_allow_html=True)
    
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
# 6. TEACHER RESULTS
# ============================================================================

def show_teacher_results():
    """교사 대시보드 - 과제 결과 조회"""
    st.header("📊 과제 결과 조회")
    
    # 과제 코드 입력
    access_code = st.text_input(
        "과제 코드 입력",
        placeholder="학생들에게 배포한 과제 코드를 입력하세요",
        key="teacher_code_input"
    )
    
    if not access_code:
        st.info("📌 과제 코드를 입력하면 학생들의 제출 결과를 조회할 수 있습니다.")
        return
    
    # Firestore에서 데이터 조회
    try:
        db = get_firestore_client()
        query = db.collection("readfit_submissions").where("access_code", "==", access_code)
        docs = list(query.stream())
        
        if not docs:
            st.warning("제출된 과제가 없습니다.")
            return
        
        # 데이터 정리
        submissions = []
        for doc in docs:
            data = doc.to_dict()
            submissions.append({
                "doc_id": doc.id,
                "data": data
            })
        
        # Summary 데이터프레임 생성
        import pandas as pd
        summary_data = []
        for sub in submissions:
            data = sub["data"]
            mission_name_map = {
                "image_detective": "🎨 이미지 탐정",
                "mystery_20_questions": "🕵️ 스무고개",
                "writer": "✍️ 작가"
            }
            mission_name = mission_name_map.get(data.get("mission_id", "unknown"), data.get("mission_id", "알 수 없음"))
            
            summary_data.append({
                "학생명": data.get("student_name", "이름 없음"),
                "활동": mission_name,
                "퀴즈 점수": f"{data.get('quiz_score', 0)}점",
                "활동 점수": f"{data.get('activity_score', 0)}점",
                "최종 점수": f"{data.get('total_score', 0)}점",
                "제출 시간": data.get("timestamp", "알 수 없음")
            })
        
        # 데이터프레임 표시
        st.subheader(f"📋 제출 현황 ({len(submissions)}명)")
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # 개별 상세 정보
        st.subheader("📝 개별 결과 상세")
        
        for idx, sub in enumerate(submissions):
            data = sub["data"]
            student_name = data.get("student_name", "이름 없음")
            mission_id = data.get("mission_id", "unknown")
            mission_details = data.get("mission_details", {})
            
            with st.expander(f"👤 {student_name} - {data.get('total_score', 0)}점", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("퀴즈 점수", f"{data.get('quiz_score', 0)}점")
                with col2:
                    st.metric("활동 점수", f"{data.get('activity_score', 0)}점")
                
                st.divider()
                
                # 미션별 상세 정보
                if mission_id == "writer":
                    st.subheader("✍️ 작품")
                    student_text = mission_details.get("student_text", "텍스트 없음")
                    st.text_area(
                        "학생 작품:",
                        value=student_text,
                        height=200,
                        disabled=True,
                        key=f"writer_text_{idx}"
                    )
                    
                elif mission_id == "mystery_20_questions":
                    st.subheader("🕵️ 스무고개 결과")
                    st.write(f"**목표 단어:** {mission_details.get('target_word', 'N/A')}")
                    st.write(f"**학생 답:** {mission_details.get('student_answer', 'N/A')}")
                    st.write(f"**사용한 힌트:** {mission_details.get('hints_used', 0)}개")
                    
                elif mission_id == "image_detective":
                    st.subheader("🎨 이미지 탐정 결과")
                    result_type = mission_details.get("result_type", "unknown")
                    result_type_map = {
                        "correct": "✅ 정답",
                        "semantic": "🔍 의미적 오답",
                        "spelling": "📝 철자적 오답",
                        "random": "🤔 무관한 오답"
                    }
                    
                    st.write(f"**목표 단어:** {mission_details.get('target_word', 'N/A')}")
                    st.write(f"**학생 답:** {mission_details.get('student_answer', 'N/A')}")
                    st.write(f"**답변 유형:** {result_type_map.get(result_type, result_type)}")
                
                # 리포트 인사이트 (모든 미션에 대해 표시)
                st.divider()
                report_insights = data.get("report_insights")
                if report_insights and isinstance(report_insights, dict):
                    st.subheader("🧠 학습 분석 리포트 (강점 · 다음 학습)")
                    strengths = report_insights.get("strengths", [])
                    next_steps = report_insights.get("next_steps", [])
                    closing = report_insights.get("closing")
                    
                    if strengths:
                        st.markdown("**강점**")
                        for s in strengths:
                            st.write(f"- {s}")
                    if next_steps:
                        st.markdown("**다음 학습**")
                        for n in next_steps:
                            st.write(f"- {n}")
                    if closing:
                        st.info(closing)
                else:
                    st.info("📊 AI 학습 분석 리포트가 생성되지 않았습니다.")
    
    except Exception as e:
        st.error(f"⚠️ 데이터 조회 중 오류 발생: {str(e)}")


# ============================================================================
# 6. TEACHER DASHBOARD
# ============================================================================

def show_teacher_dashboard():
    """교사 대시보드 - ReadFit 버전"""
    apply_global_styles()
    st.title("🎓 교사 대시보드")
    
    # 사이드바 메뉴
    with st.sidebar:
        st.write(f"### 👤 {st.session_state.user_name}")
        st.write("**역할**: 교사")
        st.divider()
        
        menu_choice = st.radio("메뉴", ["과제 생성", "결과 보기"], key="teacher_menu")
        
        st.divider()
        
        if st.button("로그아웃", use_container_width=True):
            logout()
    
    # 메뉴 선택에 따른 화면 표시
    if menu_choice == "과제 생성":
        st.subheader("📚 ReadFit - 과제 생성")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_unit = st.selectbox(
                "📖 단원 선택",
                ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
                key="teacher_unit_select"
            )
        
        with col2:
            difficulty = st.selectbox(
                "📊 난이도 선택",
                ["Beginner (초급)", "Intermediate (중급)", "Advanced (고급)"],
                key="teacher_difficulty_select"
            )
        
        st.divider()
        
        # 선택된 지문과 퀴즈 미리보기
        unit_data = YBM_TEXTBOOK[selected_unit]
        unit_title = unit_data["title"]
        difficulty_key = difficulty.split()[0]
        text_content = unit_data[difficulty_key]
        
        st.subheader(f"🎯 {unit_title} ({difficulty})")
        
        # 지문 미리보기 및 수정
        st.markdown("### 📖 지문 내용")
        st.caption("💡 지문 내용을 직접 수정할 수 있습니다.")
        edited_text = st.text_area(
            "학생들에게 제공될 지문",
            value=text_content,
            height=200,
            key=f"preview_text_{difficulty_key}"
        )
        # 수정된 지문 사용
        text_content = edited_text
        
        st.divider()
        
        # 퀴즈 미리보기
        st.markdown("### ❓ 자동 생성 퀴즈 (미리보기)")
        quiz_questions = generate_simple_quiz(text_content, unit_title, difficulty)
        
        st.markdown("---")
        for idx, q in enumerate(quiz_questions):
            st.markdown(f"**{idx+1}.** {q['question']}")
            st.write("")
            for opt_idx, option in enumerate(q['options']):
                marker = "①" if opt_idx == 0 else "②" if opt_idx == 1 else "③"
                if opt_idx == q['answer']:
                    st.markdown(f"{marker} {option} &nbsp;&nbsp; ✅ **(정답)**")
                else:
                    st.write(f"{marker} {option}")
            st.write("")
            if idx < len(quiz_questions) - 1:
                st.markdown("---")
        
        st.divider()
        
        # 과제 생성 버튼
        st.markdown("### 🚀 과제 배포")
        st.caption("위의 지문과 퀴즈를 확인하셨다면 아래 버튼을 눌러 과제를 생성하세요.")
        
        if st.button("✅ 과제 생성 및 배포", use_container_width=True, type="primary", key="create_assignment_btn"):
            access_code = generate_access_code()
            
            try:
                db = get_firestore_client()
                assignment_data = {
                    "unit": selected_unit,
                    "difficulty": difficulty,
                    "access_code": access_code,
                    "text": text_content,
                    "quiz": quiz_questions,
                    "teacher_name": st.session_state.user_name,
                    "created_at": datetime.now()
                }
                db.collection("readfit_assignments").document(access_code).set(assignment_data)
                
                st.success(f"✅ 과제가 생성되었습니다!\n\n**학생 접근 코드: `{access_code}`**")
                st.info(
                    f"📚 **단원**: {unit_title}\n"
                    f"📊 **난이도**: {difficulty}\n"
                    f"❓ **문제 수**: 3개 (객관식)"
                )
                st.balloons()
            except Exception as e:
                st.error(f"과제 생성 실패: {str(e)}")
    
    elif menu_choice == "결과 보기":
        show_teacher_results()


# ============================================================================
# 7. STUDENT WORKSPACE
# ============================================================================

def show_student_workspace():
    """학생 워크스페이스 - ReadFit 4-step 플로우"""
    apply_global_styles()
    st.title("👨‍🎓 학생 학습 공간")
    
    # 사이드바
    with st.sidebar:
        st.write(f"### 👤 {st.session_state.user_name}")
        st.write("**역할**: 학생")
        st.write(f"**학습 코드**: {st.session_state.current_access_code}")
        
        # 진행 상황 표시
        if hasattr(st.session_state, 'step'):
            step_labels = {
                0: "📚 대기 중",
                1: "❓ Step 1 - 퀴즈",
                2: "🎯 Step 2 - 활동 선택",
                3: "🎪 Step 3 - 활동 수행",
                4: "🏆 Step 4 - 최종 리포트"
            }
            st.write(f"**진행도**: {step_labels.get(st.session_state.step, '시작')}")
        
        st.divider()
        
        if st.button("로그아웃", use_container_width=True):
            logout()
    
    # Step 초기화
    if 'step' not in st.session_state:
        st.session_state.step = 1
    
    # 필요한 session_state 값들 초기화
    if 'detective_target_word' not in st.session_state:
        st.session_state.detective_target_word = None
    if 'mystery_target_word' not in st.session_state:
        st.session_state.mystery_target_word = None
    if 'mystery_text_with_blank' not in st.session_state:
        st.session_state.mystery_text_with_blank = ""
    if 'mystery_hint_level' not in st.session_state:
        st.session_state.mystery_hint_level = 0
    if 'reading_text' not in st.session_state:
        st.session_state.reading_text = ""
    
    # ReadFit 컬렉션에서 과제 데이터 로드
    try:
        db = get_firestore_client()
        doc = db.collection("readfit_assignments").document(st.session_state.current_access_code).get()
        if doc.exists:
            assignment = doc.to_dict()
        else:
            st.error("과제를 불러올 수 없습니다.")
            return
    except Exception as e:
        st.error(f"데이터 로드 오류: {str(e)}")
        return
    
    if not assignment:
        st.error("과제 정보를 불러올 수 없습니다.")
        return
    
    # 📚 지문 정보 표시
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(assignment.get("unit", "제목 없음"))
    with col2:
        st.metric("난이도", assignment.get("difficulty", "N/A"))
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 4-step 플로우 실행
    if st.session_state.step == 1:
        show_step1_quiz(assignment)
    
    elif st.session_state.step == 2:
        show_step2_mission_selection(st.session_state.quiz_score)
    
    elif st.session_state.step == 3:
        show_step3_activity(st.session_state.selected_mission)
    
    elif st.session_state.step == 4:
        show_step4_report(
            st.session_state.quiz_score,
            st.session_state.activity_score,
            st.session_state.selected_mission_title
        )


# ============================================================================
# 8. PAGE CONFIG & INITIALIZATION
# ============================================================================

st.set_page_config(
    page_title="ReadFit - 영어 학습 플랫폼",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State 초기화
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "current_access_code" not in st.session_state:
    st.session_state.current_access_code = None


# ============================================================================
# 9. MAIN APP LOGIC
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
