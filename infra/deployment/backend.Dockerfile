# 놀다가 백엔드 이미지 (W64 초안, R04 한태경 · 2026-11-24)
# - 기준: Python 3.14 (팀장 11/24 결정), 빌드 위치는 저장소 루트
#     docker build -f infra/deployment/backend.Dockerfile -t noldaga-backend .
# - 비밀값(비밀번호·키)은 이미지에 넣지 않는다: ENV·ARG·COPY 모두 금지. 실행할 때 환경변수로만 받는다(SEC-07).
# - 하나의 이미지로 API(uvicorn)·마이그레이션(migrate)·계정 비밀번호 설정을 모두 실행한다. 실행 명령은 compose.yaml에서 고른다.
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # API는 api.*, 공통 DB 코드는 backend.* 로 불러온다(backend/tests/conftest.py와 같은 경로).
    PYTHONPATH=/app:/app/backend

WORKDIR /app

# 의존성만 먼저 설치해 코드가 바뀌어도 이 층을 다시 쓰게 한다.
COPY backend/api/requirements.txt /tmp/requirements/api.txt
COPY backend/agents/requirements.txt /tmp/requirements/agents.txt
RUN pip install -r /tmp/requirements/api.txt -r /tmp/requirements/agents.txt \
 && rm -rf /tmp/requirements

# 앱 코드와 마이그레이션 SQL (migrate.py가 저장소 기준 Docs/Step 2/db를 읽는다)
COPY backend /app/backend
COPY ["Docs/Step 2/db", "/app/Docs/Step 2/db"]
COPY infra/deployment/set_role_passwords.py /app/infra/deployment/set_role_passwords.py

# root가 아닌 계정으로 실행
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin noldaga
USER noldaga

WORKDIR /app/backend
EXPOSE 8000

# /api/v1/health는 DB 없이 응답한다(기동 여부 확인용).
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
