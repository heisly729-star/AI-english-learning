"""
Firebase 초기화 및 설정 모듈
로컬 firebase-credentials.json 또는 Streamlit secrets.toml에서 인증 정보를 로드합니다.
"""

import json
import os
import tomllib
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
import streamlit as st

# .env 파일 로드 (로컬 개발용)
load_dotenv()


def _load_local_streamlit_secrets():
    """로컬 .streamlit/secrets.toml을 로드 (TOML 또는 JSON 형태 모두 허용)."""
    try:
        base_dir = os.path.dirname(__file__)
        secrets_path = os.path.join(base_dir, ".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            with open(secrets_path, "rb") as f:
                data = f.read()
                text = data.decode()
                stripped = text.lstrip()
                # JSON 형태로 시작하면 JSON 우선 시도 (추가 TOML 라인이 있어도 {})까지만 파싱)
                if stripped.startswith("{"):
                    try:
                        closing = text.rfind("}")
                        if closing != -1:
                            json_part = text[: closing + 1]
                            return json.loads(json_part)
                    except Exception:
                        pass
                # TOML 시도
                try:
                    return tomllib.loads(text)
                except Exception:
                    pass
                # JSON 시도 (Streamlit secrets에 JSON을 붙여넣은 경우)
                try:
                    return json.loads(text)
                except Exception as e:
                    print(f"로컬 secrets.toml 로드 실패: {e}")
    except Exception as e:
        print(f"로컬 secrets.toml 로드 실패: {e}")
    return {}


def get_web_api_key():
    """
    Firebase Web API Key를 로드합니다.
    1. 우선순위: .env 파일 (로컬 개발)
    2. 차선책: Streamlit secrets (Cloud)
    3. 예외: 로컬 secrets.toml 직접 로드 (Streamlit 미실행 시)
    """
    # 1) .env
    api_key = os.getenv("FIREBASE_WEB_API_KEY")
    if api_key:
        return api_key
    
    # 2) st.secrets
    try:
        if hasattr(st, "secrets") and "web_api_key" in st.secrets:
            return st.secrets["web_api_key"]
    except Exception as e:
        print(f"Streamlit secrets에서 Web API Key 로드 실패: {e}")
    
    # 3) 로컬 secrets.toml 직접 로드
    local_secrets = _load_local_streamlit_secrets()
    if local_secrets and "web_api_key" in local_secrets:
        return local_secrets["web_api_key"]
    if local_secrets and "firebase" in local_secrets and "web_api_key" in local_secrets["firebase"]:
        return local_secrets["firebase"].get("web_api_key")
    
    print("경고: Firebase Web API Key를 찾을 수 없습니다.")
    return None


def load_firebase_credentials():
    """
    Firebase 인증 정보를 로드합니다.
    1. 우선순위: 로컬 firebase-credentials.json 파일
    2. 차선책: Streamlit secrets (Cloud 배포용)
    3. 예외: 로컬 .streamlit/secrets.toml 직접 로드 (Streamlit 미실행 시)
    """
    # 로컬 파일에서 먼저 로드 시도
    credentials_path = os.path.join(
        os.path.dirname(__file__), "firebase-credentials.json"
    )
    
    if os.path.exists(credentials_path):
        try:
            return credentials.Certificate(credentials_path)
        except Exception as e:
            print(f"로컬 파일 로드 실패: {e}")
    
    # Streamlit Cloud 환경에서 secrets.toml 확인
    try:
        if "firebase" in st.secrets:
            creds_dict = dict(st.secrets["firebase"])
            return credentials.Certificate(creds_dict)
    except Exception as e:
        print(f"Streamlit secrets 로드 실패: {e}")
    
    # 로컬 .streamlit/secrets.toml 직접 로드 (로컬 실행 + st.secrets 미사용 시)
    local_secrets = _load_local_streamlit_secrets()
    if local_secrets:
        # Case 1: TOML 형태 [firebase] 섹션
        if "firebase" in local_secrets:
            try:
                creds_dict = dict(local_secrets["firebase"])
                return credentials.Certificate(creds_dict)
            except Exception as e:
                print(f"로컬 secrets.toml Firebase 로드 실패: {e}")
        # Case 2: JSON을 그대로 붙여넣은 형태 (service_account 객체 최상위)
        elif "type" in local_secrets and "private_key" in local_secrets:
            try:
                return credentials.Certificate(local_secrets)
            except Exception as e:
                print(f"로컬 secrets(JSON) 로드 실패: {e}")
    
    raise FileNotFoundError(
        "Firebase 인증 정보를 찾을 수 없습니다. "
        "firebase-credentials.json 파일이 있는지 확인하거나 "
        "Streamlit Cloud의 Secrets에 Firebase 정보를 추가하세요."
    )


def initialize_firebase():
    """
    Firebase Admin SDK를 초기화합니다.
    중복 초기화 방지 로직을 포함합니다.
    """
    try:
        if not firebase_admin._apps:
            creds = load_firebase_credentials()
            firebase_admin.initialize_app(creds, {
                "storageBucket": "ai-english-learning-be011.appspot.com"
            })
    except Exception as e:
        print(f"Firebase 초기화 오류: {e}")
        raise


def get_firestore_client():
    """Firestore 클라이언트를 반환합니다."""
    initialize_firebase()
    return firestore.client()


def get_storage_bucket():
    """Firebase Storage 버킷을 반환합니다."""
    initialize_firebase()
    return storage.bucket()
