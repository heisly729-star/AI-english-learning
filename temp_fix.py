def show_step3_image_detective(assignment):
    """Step 3: 이미지 탐정 활동"""
    st.header("Step 3️⃣ 활동 수행")
    st.subheader("🎨 이미지 탐정")
    st.write("**AI가 그린 그림을 보고 단어를 맞춰보세요!**")
    
    # 단어별 오답 사전 (의미적, 철자적 오답 정의)
    WORD_DISTRACTORS = {
        "astronaut": {"semantic": "pilot", "spelling": "astrology"},
        "dog": {"semantic": "cat", "spelling": "log"},
        "cat": {"semantic": "dog", "spelling": "hat"},
        "tree": {"semantic": "flower", "spelling": "three"},
        "house": {"semantic": "building", "spelling": "mouse"},
        "car": {"semantic": "bus", "spelling": "bar"},
        "sun": {"semantic": "star", "spelling": "son"},
        "moon": {"semantic": "star", "spelling": "soon"},
        "flower": {"semantic": "tree", "spelling": "flour"},
        "bird": {"semantic": "butterfly", "spelling": "beard"},
        "book": {"semantic": "magazine", "spelling": "look"},
        "apple": {"semantic": "banana", "spelling": "apply"},
        "hat": {"semantic": "cap", "spelling": "cat"},
        "shoes": {"semantic": "boots", "spelling": "chose"},
        "bicycle": {"semantic": "motorcycle", "spelling": "icicle"}
    }
    
    # 세션 초기화
    if "detective_word" not in st.session_state:
        st.session_state.detective_word = None
        st.session_state.detective_image = None
        st.session_state.detective_options = []
        st.session_state.detective_option_types = {}
    
    # 단어 및 이미지 생성
    if st.session_state.detective_word is None:
        # 지문에서 간단한 영어 단어 추출
        sample_words = ["astronaut", "dog", "cat", "tree", "house", "car", "sun", "moon", "flower", "bird", "book", "apple", "hat", "shoes", "bicycle"]
        selected_word = random.choice(sample_words)
        st.session_state.detective_word = selected_word
        
        # 규칙 기반 오답 생성
        distractors = WORD_DISTRACTORS.get(selected_word, {"semantic": "dog", "spelling": "log"})
        
        # 랜덤 오답: 정답과 전혀 관계없는 단어
        unrelated_words = [w for w in sample_words if w != selected_word and 
                          w != distractors["semantic"] and 
                          w != distractors["spelling"]]
        random_wrong = random.choice(unrelated_words) if unrelated_words else "desk"
        
        # 선택지 생성: 정답 + 3가지 유형의 오답
        options_with_types = [
            (selected_word, "correct"),
            (distractors["semantic"], "semantic"),
            (distractors["spelling"], "spelling"),
            (random_wrong, "random")
        ]
        
        # 섞기
        random.shuffle(options_with_types)
        
        st.session_state.detective_options = [opt[0] for opt in options_with_types]
        st.session_state.detective_option_types = {opt[0]: opt[1] for opt in options_with_types}
        
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
                    st.session_state.detective_answer_type = "correct"
                else:
                    st.session_state.activity_score = 30
                    st.error(f"❌ 틀렸습니다. 정답은 '{st.session_state.detective_word}'입니다.")
                    # 오답 유형 기록
                    answer_type = st.session_state.detective_option_types.get(option, "unknown")
                    st.session_state.detective_answer_type = answer_type
                    st.session_state.detective_wrong_answer = option
                
                # 초기화 및 다음 단계
                st.session_state.detective_word = None
                st.session_state.detective_image = None
                st.session_state.detective_options = []
                st.session_state.step = 4
                st.rerun()
