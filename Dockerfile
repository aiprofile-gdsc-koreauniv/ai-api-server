# 기반이 될 이미지 선택
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일을 컨테이너로 복사
COPY cloud-storage-credentials.json /app/
COPY config.py /app/
COPY logger.py /app/
COPY app.py /app/
COPY models.py /app/
COPY presets /app/presets
COPY requirements.txt /app/
COPY upload.py /app/
COPY utils.py /app/
COPY .env /app/

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt


# 컨테이너 실행 시 실행할 명령
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9001"]
