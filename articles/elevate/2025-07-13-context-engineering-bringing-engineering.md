---
id: "elevate:context-engineering-bringing-engineering"
source_id: "elevate"
archive_index: 47
canonical_url: "https://addyo.substack.com/p/context-engineering-bringing-engineering"
author: "Addy Osmani"
published_at: "2025-07-13"
source_sha256: "2d48db3904eb28c31400ec9fa5d3a516c0254fbc4af77f53d1f6708cfe0a39c3"
editorial_version: "ko-300eojeol-v1"
full_source_verified: true
status: "ready"
---

# [Context Engineering: Bringing Engineering Discipline to Prompts](https://addyo.substack.com/p/context-engineering-bringing-engineering)

2025.07.13 · Addy Osmani · Elevate

AI의 답이 좋지 않을 때 질문의 표현만 바꾸면 해결되지 않는 경우가 있습니다. Addy Osmani는 모델이 작업에 필요한 정보와 도구를 제때 받도록 구성하는 일을 컨텍스트 엔지니어링으로 설명합니다. 컨텍스트는 모델이 한 번에 참고하는 작업 자료입니다. 여기에는 지시문뿐 아니라 관련 문서, 코드, 이전 결정과 도구 실행 결과가 들어갑니다. 핵심은 긴 질문을 만드는 기술보다 정보를 선택하고 전달하는 시스템을 설계하는 데 있습니다.

이 시스템은 요청에 따라 필요한 자료를 검색하고, 현재 작업과 연결하며, 결과를 다시 다음 단계에 반영합니다. 코드 수정이라면 관련 파일을 찾고 테스트 실패 내용을 전달하는 반복 과정이 한 예입니다. 자료의 형식도 중요합니다. 무엇이 지시이고 무엇이 참고 문서인지 구분하면 해석을 돕습니다. 반대로 관련 없는 자료를 많이 넣으면 비용이 늘고 중요한 정보가 묻힐 수 있으므로 선택과 압축이 함께 필요합니다.

긴 작업에서는 지난 실패나 잘못된 가정이 누적되어 다음 판단을 흐릴 수 있습니다. 저자는 핵심 결정과 현재 상태를 요약하고, 작업 단계가 바뀔 때 불필요한 맥락을 정리하는 방법을 소개합니다. 그러나 좋은 컨텍스트가 논리 오류나 허위 생성을 완전히 제거하지는 않는다고 인정합니다. 권한 관리, 실행 흐름, 평가와 관찰도 별도로 필요합니다. 팀은 최종 답뿐 아니라 모델에 어떤 자료가 들어갔는지 추적해야 합니다.

적용 상황을 하나 구성하면, 여러 학기의 강의계획서로 수강 조건을 안내하는 도우미를 생각할 수 있습니다. 과목 이름이 같아도 학기와 담당 교수가 다르면 선수 과목이 달라질 수 있습니다. 이때 관련 문서를 많이 찾는 것만으로는 충분하지 않습니다. 현재 문의가 어느 학기를 대상으로 하는지 먼저 정하고, 해당 조건을 답변의 근거와 연결해야 합니다. 이는 원문의 원칙을 설명하기 위해 만든 예시입니다. 틀린 안내가 나왔을 때도 문서를 못 찾았는지, 다른 학기 자료를 섞었는지, 찾은 조건을 잘못 해석했는지 구별할 수 있습니다. 문제를 이렇게 나누면 막연히 모델을 바꾸기 전에 입력 자료와 처리 과정에서 고칠 부분을 찾기 쉬워집니다.
