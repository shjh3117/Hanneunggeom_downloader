# KHPT Downloader

한국사능력검정시험(KHPT)의 기출 문제지와 정답표를 자동으로 내려받기 위한 파이썬 모듈입니다. 모바일 공식 사이트(m.historyexam.go.kr)의 공개 자료만을 대상으로 하며, 회차·난이도·문서 유형을 분석해 규칙적인 파일명으로 저장합니다.

## 요구 사항

- Python 3.8 이상
- `requests`, `beautifulsoup4` 패키지

```bash
pip install requests beautifulsoup4
# 또는 프로젝트에서 사용하는 패키지 관리자에 맞춰 설치하세요.
```

## 주요 기능

- **회차/난이도 판별**: 게시글 제목을 분석해 기본/심화 및 회차 정보를 추출합니다.
- **문서 분류**: 첨부파일 이름으로 문제지/정답표를 구분합니다.
- **파일명 정규화**: `63회 한국사_문제지(심화).pdf`와 같은 일관된 이름으로 저장합니다.
- **네트워크 안정성**: 재시도 정책과 지연 옵션을 적용해 서버 차단 가능성을 줄입니다.
- **필터링**: 기본 또는 심화 난이도만 선택적으로 내려받을 수 있습니다.

## CLI 사용

모듈에는 CLI 파서를 노출하는 함수가 포함되어 있어 별도의 엔트리 포인트에서 활용할 수 있습니다. 예를 들어 루트 스크립트 없이 모듈만 있을 경우 다음과 같이 실행할 수 있습니다.

```bash
python downloader.py --dest downloads --max-pages 2 --levels advanced --delay 1.5
```

### CLI 옵션

| 옵션 | 설명 |
| --- | --- |
| `--dest` | 내려받은 파일을 저장할 디렉터리 (기본값: `./downloads`) |
| `--max-pages` | 자료실 목록을 최대 몇 페이지까지 탐색할지 지정. 미지정 시 가능한 모든 페이지를 순회 |
| `--overwrite` | 동일 이름 파일이 존재해도 다시 다운로드 |
| `--delay` | 각 요청 사이에 둘 지연시간(초). 기본 1초 |
| `--levels` | `basic`, `advanced`를 공백으로 구분해 지정. 생략 시 두 난이도 모두 다운로드 |


## Python API

```python
from pathlib import Path
from khpt_downloader import download_past_exams, build_parser

# 직접 함수 호출
downloaded = download_past_exams(
    dest=Path("downloads"),
    max_pages=2,
    overwrite=False,
    delay=1.0,
    levels={"basic", "advanced"},
)
print("다운로드 수:", downloaded)

# 커스텀 CLI 구성 시
parser = build_parser()
args = parser.parse_args()
```

### `download_past_exams` 인자

- `dest (Path)` : 결과 파일을 저장할 경로.
- `max_pages (Optional[int])` : 목록 페이지 최대 수. `None`이면 가능한 모든 페이지를 탐색.
- `overwrite (bool)` : 동일 파일명이 존재할 때 다시 다운로드할지 여부.
- `delay (float)` : 각 요청 사이의 지연(초). 서버 부하나 차단을 방지하기 위해 0 이상 값을 권장.
- `levels (Optional[Set[str]])` : `{"basic", "advanced"}` 중 일부 또는 전체. `None`이면 모두 다운로드.

반환값은 새로 다운로드한 파일 수(int)입니다.


## 파일명 규칙

- 기본 템플릿: `{회차}회 한국사_{문서종류}({난이도}).pdf`
- 문서종류: `문제지` 또는 `정답표`
- 난이도: `기본`, `심화`
- 회차, 난이도, 문서종류를 판별할 수 없는 경우에는 원본 첨부파일명을 기반으로 저장합니다.


## 개발 및 테스트 참고

- 모바일 웹 사이트 구조가 변경되면 파서 수정이 필요할 수 있습니다.
- 대량 다운로드 시 서버 측 정책이 적용될 수 있으므로 `--delay` 값을 조정하거나 `max_pages`를 제한해 사용하세요.
- 모듈은 공개 자료만 수집하도록 설계되었습니다.


## 라이선스

모듈을 포함하는 저장소의 라이선스 정책을 따릅니다. 별도의 라이선스 파일이 있다면 해당 내용을 참고하세요.
