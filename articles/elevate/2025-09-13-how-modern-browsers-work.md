---
id: "elevate:how-modern-browsers-work"
source_id: "elevate"
archive_index: 51
canonical_url: "https://addyo.substack.com/p/how-modern-browsers-work"
author: "Addy Osmani"
published_at: "2025-09-13"
source_sha256: "81d8bdfdc2b42bd4f14d7fed850c8e286aadb007ea6fecfe6c0350bf9b3607f0"
source_sha256_method: "Complete web-rendered public article body, assembled by source line number with zero missing lines; navigation, reaction counts and comments excluded; link markers reduced to labels; whitespace normalized within paragraphs; UTF-8 SHA-256"
editorial_version: "ko-300eojeol-v1"
status: "ready"
---

# [How modern browsers work](https://addyo.substack.com/p/how-modern-browsers-work)

2025.09.13 · Addy Osmani · Elevate

브라우저는 HTML과 CSS, JavaScript를 받아 화면으로 바꾸는 하나의 검은 상자처럼 보입니다. Addy Osmani는 그 안에서 네트워크와 문서 분석, 배치 계산, 그림 그리기, 코드 실행이 협력하는 과정을 설명합니다. 페이지가 느리다는 증상만으로는 어느 단계가 문제인지 알 수 없습니다. 구조를 이해하면 다운로드가 늦은 상황과 화면을 다시 계산하느라 반응이 지연되는 상황을 구분할 수 있습니다. 글은 주로 Chromium을 중심으로 설명하면서 다른 엔진과의 공통점도 짚습니다.

HTML은 문서의 구조를 나타내는 DOM으로 정리하고, CSS는 각 요소의 스타일을 결정하는 데 사용합니다. 브라우저는 이를 바탕으로 크기와 위치를 계산한 뒤 화면을 그리며, 필요한 층을 합성합니다. 문서나 스타일이 바뀌면 후속 단계의 일부를 다시 수행해야 할 수 있습니다. JavaScript 엔진은 해석과 단계적인 컴파일을 조합하고 메모리를 관리합니다. 네트워크와 스크립트, 화면 작업은 서로 영향을 주므로 하나의 단계만 따로 최적화해서는 부족할 수 있습니다.

여러 프로세스와 격리 구조는 웹 콘텐츠의 오류와 위험이 다른 영역으로 번지는 일을 제한합니다. 다만 엔진마다 내부 구현과 자원 사용 방식은 다릅니다. 저자는 개발자 도구로 실제 네트워크와 실행 기록을 확인하고 여러 브라우저에서 동작을 검증하라고 권합니다. 본문은 발행 당시 구현을 설명하는 개요이므로 세부적인 기본값을 고정된 규칙처럼 받아들일 필요는 없습니다. 중요한 것은 화면의 결과를 만드는 여러 단계의 관계입니다.

예를 들어 상품 목록을 스크롤할 때만 끊기는 화면을 조사한다면, 이미지 파일을 줄이는 일부터 시작하는 대신 실제 기록에서 시간을 쓰는 작업을 먼저 볼 수 있습니다. 네트워크가 이미 끝난 뒤에도 지연이 생긴다면 다른 가설을 검토해야 하기 때문입니다. 같은 화면을 항목 수와 사용자 동작을 바꿔 비교하면 어떤 조건에서 문제가 커지는지도 알 수 있습니다. 이러한 진단은 특정 최적화 기법을 외우는 것보다 원인과 결과를 연결하는 연습에 가깝습니다. 개선 후에는 처음 불편을 겪었던 환경에서 다시 확인해야 합니다. 빠른 개발용 컴퓨터의 한 번의 실행으로 결론을 내리지 않고, 사용자가 실제로 하는 동작이 나아졌는지 점검하는 데 브라우저 내부에 대한 이해를 활용할 수 있습니다.
