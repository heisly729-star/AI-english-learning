# Firebase 설정 가이드

## Firebase 프로젝트 생성

1. [Firebase Console](https://console.firebase.google.com/)에 접속
2. 새 프로젝트 생성
3. 프로젝트 설정 완료

## 서비스 계정 키 생성

1. Firebase Console → 프로젝트 설정 → **서비스 계정** 탭
2. **새 개인 키 생성** 클릭
3. JSON 파일 다운로드
4. 파일명을 `firebase-credentials.json`으로 변경하여 프로젝트 루트에 저장

## Firestore 설정

1. Firebase Console → **Firestore Database** 생성
2. 시작 모드: **테스트 모드** (개발 중)
3. 위치: **asia-northeast1** (한국)
4. 다음 컬렉션 생성:
   - `assignments`
   - `submissions`

## Firebase Storage 설정

1. Firebase Console → **Storage** 활성화
2. 보안 규칙:
```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /student_audio/{allPaths=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Streamlit Cloud 배포

1. 프로젝트 설정 → **Secrets**
2. 다음 형식으로 Firebase 정보 추가:

```toml
[firebase]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_CLIENT_EMAIL"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CLIENT_X509_CERT_URL"
universe_domain = "googleapis.com"
```

**주의**: `private_key`의 개행 문자를 `\n`으로 표현하세요.
