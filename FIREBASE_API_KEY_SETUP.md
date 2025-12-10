# 🔑 Firebase Web API Key 설정 가이드

## Firebase Web API Key란?

**Web API Key**는 클라이언트 측(브라우저/Streamlit 앱)에서 Firebase와 통신할 때 사용하는 공개 API 키입니다.

- **공개해도 안전**: .gitignore에 포함되어 있음
- **용도**: Firestore, Storage 등에 직접 접근 (선택사항)

## 🎯 Web API Key 가져오기

### 1단계: Firebase Console 접속
1. [Firebase Console](https://console.firebase.google.com/) → 프로젝트 선택
2. **⚙️ 프로젝트 설정** → **일반** 탭

### 2단계: Web API Key 확인
"웹 API 키" 섹션에서 다음과 같은 형태의 키 확인:
```
AIzaSyD_l-dH2bU2g_xxxxxxxxxxxxxxxxxxxxxxx
```

---

## 📝 로컬 개발 환경 설정

### 방법 1: .env 파일 사용 (권장)

1. **`.env` 파일 생성**
```bash
cp .env.example .env
```

2. **`.env` 파일 수정**
```bash
FIREBASE_WEB_API_KEY=AIzaSyD_l-dH2bU2g_xxxxxxxxxxxxxxxxxxxxxxx
```

3. **저장** (`.gitignore`에 `.env`가 포함되어 있으므로 안전)

### 방법 2: `.streamlit/secrets.toml` 수정 (로컬 테스트용)

```toml
[firebase]
# 기존 설정...

# Web API Key 추가
web_api_key = "AIzaSyD_l-dH2bU2g_xxxxxxxxxxxxxxxxxxxxxxx"
```

---

## ☁️ Streamlit Cloud 배포 설정

1. **Streamlit Community Cloud 로그인**
2. **앱 설정** → **Secrets** 클릭
3. 다음 내용 추가:

```toml
[firebase]
type = "service_account"
# ... Service Account 정보 ...

# Web API Key
web_api_key = "AIzaSyD_l-dH2bU2g_xxxxxxxxxxxxxxxxxxxxxxx"
```

4. **저장** → **배포**

---

## 💻 코드에서 사용하기

```python
from firebase_config import get_web_api_key

# Web API Key 가져오기
api_key = get_web_api_key()

if api_key:
    print(f"API Key 로드 성공: {api_key[:10]}...")
else:
    print("경고: Web API Key를 찾을 수 없습니다")
```

---

## �� 보안 주의사항

✅ **안전한 방법**
- `.env` 파일 사용 (`.gitignore`에 포함)
- `.streamlit/secrets.toml` (`.gitignore`에 포함)

❌ **위험한 방법**
- 하드코딩: `web_api_key = "AIzaSyD..."`
- 환경 변수 노출

---

## 📋 환경별 설정 요약

| 환경 | 설정 파일 | 로드 순서 |
|------|---------|---------|
| 로컬 개발 | `.env` | `.env` → secrets.toml |
| Streamlit Cloud | secrets.toml | secrets.toml → `.env` |

---

## ✅ 확인 방법

### 터미널에서 확인
```bash
python -c "
from firebase_config import get_web_api_key
key = get_web_api_key()
if key:
    print(f'✅ API Key 로드 성공')
    print(f'   Key: {key[:20]}...')
else:
    print('❌ API Key를 찾을 수 없습니다')
"
```

### Streamlit 앱에서 확인
```python
from firebase_config import get_web_api_key
api_key = get_web_api_key()
st.info(f"Web API Key: {api_key[:20] if api_key else '없음'}...")
```

---

## 🚀 문제 해결

### "Web API Key를 찾을 수 없습니다" 에러
1. `.env` 파일이 있는지 확인
2. `.env`에 `FIREBASE_WEB_API_KEY=...` 있는지 확인
3. Streamlit Cloud: Secrets에 `web_api_key` 추가했는지 확인

### 키가 정확한지 확인하려면
- Firebase Console → 프로젝트 설정 → 일반 탭
- "웹 API 키" 섹션에서 다시 확인

---

## 📚 참고 자료

- [Firebase Web Setup](https://firebase.google.com/docs/web/setup)
- [Streamlit Secrets](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [python-dotenv Documentation](https://python-dotenv.readthedocs.io/)
