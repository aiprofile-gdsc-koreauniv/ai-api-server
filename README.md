# ai-api-server

## 1. Build & Run



1. 해당 레포지토리를 클론합니다.

   ```bash
   git clone https://github.com/aiprofile-gdsc-koreauniv/ai-api-server
   ```
2. Crendential을 작업폴더에 넣습니다.
   - GCP Credential과 현재 폴더에 위치합니다.
   - .env 파일 또는 환경변수를 설정합니다.

3. Docker 이미지 빌드
   ```bash
   docker build -t MY_CONTAINER_NAME -f dev.dockerfile .
   ```

4. Docker 실행
   ```bash
   docker run -d \
      -p 9001:9001 \
      -p 5672:5672 \
      -e ENV_VAR1=VALUE1 \
      MY_CONTAINER_NAME
   ```

## 참고사항
- 해당 Docker 명령은 다운받은 작업폴더를 볼륨바인딩을 진행하여 작동합니다.
- `tail -f $PWD/server.log` 를 통해 현재 로그를 확인할 수 있습니다.