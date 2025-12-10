"""
Firebase 초기화 및 설정 모듈
로컬 firebase-credentials.json 또는 Streamlit secrets.toml에서 인증 정보를 로드합니다.
"""

import json
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage
import streamlit as st

# .env 파일 로드 (로컬 개발용)
load_dotenv()


def get_web_api_key():
    """
    Firebase Web API Key를 로드합니다.
    1. 우선순위: .env 파일
    2. 차선책: Streamlit secrets
    """
    # .env 파일에서 먼저 로드 (로컬 개발용)
    api_key = os.getenv("FIREBASE_WEB_API_KEY")
    if api_key:
        return api_key
    
    # Streamlit Cloud 환경에서 secrets.toml 확인
    try:
        if hasattr(st, 'secrets') and "web_api_key" in st.secrets:
            return st.secrets["web_api_key"]
    except Exception as e:
        print(f"Streamlit secrets에서 Web API Key 로드 실패: {e}")
    
    print("경고: Firebase Web API Key를 찾을 수 없습니다.")
    return None


def load_firebase_credentials():
    """
    Firebase 인증 정보를 로드합니다.
    1. 우선순위: 로컬 firebase-credentials.json 파일
    2. 차선책: Streamlit secrets (Cloud 배포용)
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
