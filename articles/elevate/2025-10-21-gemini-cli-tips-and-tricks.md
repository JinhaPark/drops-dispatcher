---
id: "elevate:gemini-cli-tips-and-tricks"
source_id: "elevate"
archive_index: 52
canonical_url: "https://addyo.substack.com/p/gemini-cli-tips-and-tricks"
author: "Addy Osmani"
published_at: "2025-10-21"
source_sha256: "2363596d670ceeddcfa7006317dc747999f633938c6093b89247c3ece6f06cd7"
source_sha256_method: "Complete web-rendered public article body, assembled by source line number with zero missing lines; navigation, reaction counts and comments excluded; link markers reduced to labels; whitespace normalized within paragraphs; UTF-8 SHA-256"
editorial_version: "ko-300eojeol-v1"
status: "ready"
---

# [Gemini CLI Tips & Tricks](https://addyo.substack.com/p/gemini-cli-tips-and-tricks)

2025.10.21 · Addy Osmani · Elevate

Gemini CLI는 터미널에서 질문에 답하고 파일과 명령줄 도구를 활용하는 코딩 에이전트입니다. Addy Osmani는 이 도구를 반복 가능한 개발 환경으로 사용하는 방법을 소개합니다. 핵심은 매번 긴 설명을 다시 입력하는 대신 프로젝트 문맥과 자주 쓰는 작업을 정리하는 것입니다. 지침 파일과 사용자 명령, 외부 도구 연결을 함께 구성하면 에이전트가 무엇을 알고 무엇을 실행할지 더 명확히 다룰 수 있습니다. 글은 발행 당시의 여러 기능을 실용적인 사용 사례로 묶습니다.

프로젝트의 규칙은 GEMINI.md에 담고, 파일이나 이미지를 명시적으로 지정해 필요한 근거를 제공합니다. MCP 연결과 확장 기능은 외부 시스템을 활용하는 통로이며, 사용자 명령은 반복 작업의 입력을 표준화합니다. 긴 대화에서는 문맥을 정리하고, 작업을 되돌릴 수 있는 기능을 활용합니다. 실행 환경과 권한 설정도 함께 다뤄야 합니다. 사용할 수 있는 도구가 많아질수록 무엇을 맡겼는지 이해하고 결과를 확인하는 일도 중요해집니다.

저자는 토큰과 캐시 사용량, 실행 기록을 관찰하는 방법도 소개합니다. 편집기와 자동화 환경의 연결은 대화를 실제 개발 흐름으로 이어 줍니다. 이러한 기능이 있다고 해서 모든 작업을 무조건 자동 승인하라는 뜻은 아닙니다. 글의 예제에는 설명용 설정도 포함되어 있으며, 명령과 기본값은 버전에 따라 달라질 수 있습니다. 따라서 이 자료는 당시 활용 방식을 이해하는 안내로 읽고 현재 적용할 설정은 별도로 확인해야 합니다.

팀에 도입하는 상황을 가정하면 첫 작업을 저장소 전체의 수정으로 잡기보다 읽기와 설명부터 시작하는 방법이 있습니다. 에이전트가 프로젝트의 테스트 경로와 빌드 절차를 제대로 찾는지 확인하고, 그다음 범위가 작은 변경을 맡길 수 있습니다. 지침 파일에는 추상적인 품질 구호보다 실제로 검토할 수 있는 완료 조건을 적는 편이 낫습니다. 예를 들어 수정한 동작을 어떤 방식으로 확인했는지 남기도록 하면 후속 검토의 출발점이 생깁니다. 또한 도구가 실행됐다는 기록과 의도한 결과가 나왔다는 증거를 구분해야 합니다. 이렇게 도입 단계를 설계하면 기능 목록을 많이 활성화하는 일보다 자신의 작업에서 문맥과 실행, 검증이 어떻게 연결되는지 배우는 데 집중할 수 있습니다.
