# AWS DCO 면접 연습

한국어 UI에서 한·영 질문 40개를 연습하는 Streamlit 앱입니다. 기술 답변, STAR 답변, 자기점검, 15분 모의면접을 제공합니다. 질문과 검토 기준은 자체 제작했습니다.

## 로컬 실행

Python 3.11 기준입니다. 이 폴더에서 다음 명령을 실행합니다.

```powershell
python -m pip install -r requirements.txt
python content.py
python -m streamlit run app.py
```

## Streamlit Community Cloud 배포

1. 이 폴더의 소스 파일과 숨김 폴더 `.streamlit`을 GitHub 저장소 루트에 커밋합니다.
2. [Streamlit Community Cloud](https://share.streamlit.io/)에서 **Create app**을 선택합니다.
3. 저장소와 브랜치를 지정하고 **Main file path**에 `app.py`를 입력합니다. Advanced settings에서 Python 3.11을 선택합니다.
4. **Deploy**를 누른 뒤 배포 주소에서 기술 문항 답변과 기록 복원을 확인합니다.

[Streamlit 공식 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## 기록과 타이머

- 답변은 서버의 SQLite에 저장됩니다. 브라우저 주소의 무작위 `practice` 값이 개인 기록에 접근하는 키입니다. 기존 기록을 다시 열려면 그 주소를 보관하고 공유할 때는 쿼리가 없는 기본 앱 주소를 사용하세요.
- 저장소 기본 위치는 `data/practice.sqlite3`입니다. Community Cloud의 로컬 디스크는 영구 저장소로 보장되지 않습니다. 자체 호스팅에서는 영구 볼륨의 파일 경로를 환경 변수 `DCO_DB_PATH`에 지정할 수 있습니다.
- 답변 입력을 마치면 Tab을 누르거나 입력란 밖을 클릭해 저장합니다. Streamlit이 입력값을 서버에 전달하기 전에 시간이 끝나거나 페이지가 닫히면 그 입력 내용은 복구할 수 없습니다.
- 새 모의면접을 시작하면 이전 세션 요약은 교체되고 제출한 답변은 기록에 남습니다.

## 표준형과 맞춤형

- **표준형**은 API 키 없이 사용합니다. 기존 질문 40개, STAR, 15분 모의면접과 자기점검을 제공합니다.
- **맞춤형**은 경험 카드 최대 3개를 저장하고 선택한 언어로 기술 3개, 행동 2개를 생성합니다. 답변별 피드백은 한국어로 표시됩니다. 경험이 없는 영역은 가상 상황으로 표시됩니다.
- 앱의 OpenAI API 키 입력란을 사용하거나, 운영자가 Streamlit Cloud의 **App settings → Secrets**에 아래 값을 넣을 수 있습니다. 키 입력란의 값은 연습 기록에 저장되지 않습니다. 공개 앱에 운영자 키를 설정하면 방문자의 요청이 운영자 계정에 과금될 수 있습니다. 공개 앱에서 각 사용자 키를 받으려면 운영자 키를 설정하지 마세요.
- 전송 버튼을 누르기 전에 열어볼 수 있는 패널에서 경험, 현재 질문, 답변 등 전송 항목을 확인할 수 있습니다. 앱은 연결된 경험과 현재 답변만 피드백에 사용합니다. 키를 비워도 저장된 맞춤형 질문과 피드백은 열 수 있습니다.
- 경험 카드, 질문, 초안, AI 결과도 SQLite에 저장되며 **기록 → 전체 기록 삭제**로 정리할 수 있습니다. 앱에서의 삭제는 외부 서비스의 데이터 보존 설정에 영향을 주지 않습니다.

```toml
OPENAI_API_KEY = "YOUR_API_KEY"
OPENAI_MODEL = "gpt-4.1-mini"
```

로컬에서는 환경 변수 또는 `.streamlit/secrets.toml`에 설정할 수 있습니다. 실제 키를 GitHub에 커밋하지 마세요. 모델은 JSON Schema 기반 Structured Outputs를 지원해야 합니다.

[OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses/create)
