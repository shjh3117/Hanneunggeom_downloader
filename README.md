# KHPT Downloader

한국사능력검정시험(KHPT) 기출 문제지와 정답표를 자동으로 내려받는 파이썬 모듈입니다. 모바일 공식 사이트(m.historyexam.go.kr)의 공개 자료만을 대상으로 하며, 회차·난이도·문서 유형을 판별해 규칙적인 파일명으로 저장합니다.

## 요구 사항

- Python 3.8 이상
- `requests`, `beautifulsoup4`

```bash
pip install requests beautifulsoup4
```

## 주요 기능

- **회차/난이도 판별**: 게시글 제목을 분석해 기본/심화 여부와 회차를 추출합니다.
- **문서 분류**: 첨부파일 이름으로 문제지/정답표를 구분합니다.
- **파일명 정규화**: `63회 한국사_문제지(심화).pdf`처럼 일관된 이름으로 저장합니다.
- **안정성 강화**: 재시도·지연을 적용해 일시적인 네트워크 차단을 완화합니다.
- **난이도 필터링**: 기본 또는 심화만 선택적으로 내려받을 수 있습니다.

## CLI 사용

모듈 디렉터리(`khpt_downloader/`)에서 다음과 같이 실행합니다.

```bash
python downloader.py --dest downloads --max-pages 2 --levels advanced --delay 1.5
```

### CLI 옵션

| 옵션 | 설명 |
| --- | --- |
| `--dest` | 저장할 디렉터리. 기본값은 `./downloads` 입니다. |
| `--max-pages` | 자료실 목록을 몇 페이지까지 탐색할지 지정합니다. 미지정 시 가능한 모든 페이지를 순회합니다. |
| `--delay` | 요청 사이에 둘 지연 시간(초). 기본값은 1초입니다. |
| `--levels` | `basic`, `advanced` 중 원하는 난이도를 공백으로 구분해 지정합니다. 생략하면 두 난이도 모두 내려받습니다. |
| `--download-existing` | 기존 파일이 있어도 다시 다운로드합니다. 기본값은 건너뛰기입니다. |

기본적으로 기존 파일이 있으면 건너뛰며, `--download-existing` 옵션을 사용하면 다시 받을 수 있습니다.

## Python API

```python
from pathlib import Path
from khpt_downloader import download_past_exams, build_parser

# 함수 직접 호출
count = download_past_exams(
    dest=Path("downloads"),
    max_pages=2,
    skip_existing=True,
    delay=1.0,
    levels={"basic", "advanced"},
)
print("다운로드한 파일 수:", count)

# 커스텀 CLI 구성 시
parser = build_parser()
args = parser.parse_args()
```

### `download_past_exams` 매개변수

- `dest (Path)` : 결과 파일을 저장할 경로.
- `max_pages (Optional[int])` : 목록 페이지 제한. `None`이면 가능한 모든 페이지를 탐색합니다.
- `skip_existing (bool)` : 기존 파일이 있을 때 건너뛸지 여부. CLI 기본값은 `True`이며 `--download-existing` 옵션으로 끌 수 있습니다.
- `delay (float)` : 각 요청 사이의 지연(초). 서버 부하나 차단을 완화하려면 0 이상 값을 사용하세요.
- `levels (Optional[Set[str]])` : `{"basic", "advanced"}` 중 일부 또는 전체. `None`이면 두 난이도를 모두 내려받습니다.

반환값은 새로 내려받은 파일 수(int)입니다.

## 파일명 규칙

- 기본 템플릿: `{회차}회 한국사_{문서종류}({난이도}).pdf`
- 문서종류: `문제지` 또는 `정답표`
- 난이도: `기본`, `심화`
- 회차·난이도·문서종류를 판별할 수 없는 경우에는 원본 이름을 기반으로 저장합니다.

## 개발 참고 사항

- 모바일 사이트 구조가 변경되면 파서 로직을 수정해야 할 수 있습니다.
- 대량 다운로드 시 서버 정책에 따라 차단될 수 있으므로 `--delay` 값을 조정하거나 `max_pages`를 제한해 사용하세요.
- 모듈은 공개 자료만 수집하도록 설계되어 있습니다.