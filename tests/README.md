# CodeSynapse 테스트 가이드

이 디렉토리에는 CodeSynapse 프로젝트의 모든 테스트가 포함되어 있습니다.

## 테스트 구조

```
tests/
├── conftest.py          # 공통 픽스처와 설정
├── test_rules.py        # rules.py 모듈 테스트
├── test_parser.py       # parser.py 모듈 테스트  
├── test_builder.py      # builder.py 모듈 테스트
├── test_visualizer.py   # visualizer.py 모듈 테스트
├── test_init.py         # __init__.py (메인 함수) 테스트
└── README.md           # 이 파일
```

## 테스트 실행

### 전체 테스트 실행
```bash
pytest
```

### 특정 모듈 테스트
```bash
# rules 모듈만 테스트
pytest tests/test_rules.py

# parser 모듈만 테스트
pytest tests/test_parser.py

# builder 모듈만 테스트
pytest tests/test_builder.py
```

### 커버리지와 함께 실행
```bash
pytest --cov=src/codesynapse --cov-report=html
```

### 자세한 출력으로 실행
```bash
pytest -v -s
```

## 테스트 의존성 설치

```bash
pip install -e ".[test]"
```

또는

```bash
pip install pytest pytest-cov pytest-mock
```

## 테스트 픽스처

### `temp_project_dir`
테스트용 임시 프로젝트 디렉토리를 생성합니다. 다음과 같은 구조를 가집니다:

```
temp_project/
├── main.py              # 메인 모듈
├── utils.py             # 유틸리티 모듈 (클래스 포함)
└── models/
    ├── __init__.py
    ├── user.py          # User 클래스
    └── base.py          # BaseModel 클래스
```

### `sample_graph`
테스트용 NetworkX 그래프를 생성합니다. 노드와 엣지가 미리 설정되어 있어 그래프 관련 테스트에 사용됩니다.

## 테스트 범위

### test_rules.py
- NodeType과 EdgeType 열거형 검증
- VISUAL_RULES 상수의 구조와 완성도 확인
- 색상, 크기 등 시각적 속성 유효성 검사

### test_parser.py
- CodeParser의 AST 파싱 기능
- 모듈, 클래스, 함수 노드 생성 확인
- import 관계와 상속 관계 감지
- 오류 처리 및 예외 상황 대응

### test_builder.py
- GraphBuilder의 그래프 구축 기능
- 파서 데이터를 NetworkX 그래프로 변환
- 외부 라이브러리 노드 자동 추가
- 그래프 구조 무결성 검사

### test_visualizer.py
- visualize_graph 함수의 HTML 생성 기능
- pyvis Network 객체와의 상호작용
- 노드와 엣지 스타일링 적용
- 파일 출력 및 레이아웃 설정

### test_init.py
- generate_graph 메인 함수의 통합 테스트
- 전체 파이프라인 동작 확인
- 매개변수 처리 및 출력 메시지
- 예외 상황 처리

## 테스트 작성 가이드

1. **Given-When-Then 패턴** 사용
2. **Mock 객체**로 외부 의존성 격리
3. **실제 통합 테스트**와 **단위 테스트** 균형
4. **테스트 이름**은 한국어로 명확하게 작성
5. **예외 상황**과 **엣지 케이스** 포함

## 주의사항

- 테스트 실행 시 임시 파일이 생성되지만 자동으로 정리됩니다
- 일부 테스트는 실제 파일 시스템을 사용하므로 권한이 필요할 수 있습니다
- pyvis 라이브러리는 브라우저 환경이 아닌 곳에서도 HTML 파일 생성이 가능합니다 