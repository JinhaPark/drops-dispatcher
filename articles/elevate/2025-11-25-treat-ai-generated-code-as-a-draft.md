---
id: "elevate:treat-ai-generated-code-as-a-draft"
source_id: "elevate"
archive_index: 55
canonical_url: "https://addyo.substack.com/p/treat-ai-generated-code-as-a-draft"
author: "Addy Osmani"
published_at: "2025-11-25"
source_sha256: "701276bee90e47eef4426e6871162a569aeabe5da2414ace62a38d86f72cf104"
source_sha256_method: "Complete web-rendered public article body, assembled by source line number with zero missing lines; navigation, reaction counts and comments excluded; link markers reduced to labels; whitespace normalized within paragraphs; UTF-8 SHA-256"
editorial_version: "ko-300eojeol-v1"
status: "ready"
---

# [Treat AI-Generated code as a draft](https://addyo.substack.com/p/treat-ai-generated-code-as-a-draft)

2025.11.25 · Addy Osmani · Elevate

AI가 작성한 코드는 완성품이 아니라 검토가 필요한 초안이라는 것이 Addy Osmani의 주장입니다. 코드를 읽고 이해하는 일을 건너뛰면 동작과 의도의 연결을 설명할 사람이 사라집니다. 저자는 결과를 저장소에 넣는 개발자와 조직이 책임을 유지해야 한다고 강조합니다. 생성 속도가 빨라도 정확성과 유지보수 기준은 달라지지 않습니다. 핵심은 AI가 틀릴 수 있다는 경고를 반복하는 데 있지 않습니다. 누가 어떤 근거로 변경을 받아들였는지 분명하게 만드는 일입니다.

AI에 과도하게 의존하면 학습과 비판적 사고를 연습할 기회가 줄 수 있다는 우려도 다룹니다. 코드를 직접 이해하고 디버깅하는 과정은 다음 문제를 판단하는 기반이기 때문입니다. 동시에 큰 변경이 빠르게 쌓이면 검토자가 처리해야 할 양도 늘어납니다. 저자는 자신이 이해하지 못한 코드를 병합하지 않고, 변경을 작은 단위로 나누며, 테스트와 설명을 통해 판단 근거를 확보하는 습관을 권합니다. 도구의 도움과 인간의 이해를 함께 유지하려는 접근입니다.

팀 차원의 합의도 필요합니다. AI를 어디에 사용했는지 공유하고, 제출자가 검토와 결과에 책임을 지며, 불확실한 부분은 질문할 수 있어야 합니다. 저자는 학습을 지속할 기회와 검토 기준을 명시하라고 제안합니다. AI 사용과 능력 저하에 관한 관찰을 모든 개발자에게 동일하게 적용할 수는 없습니다. 다만 이해 없이 받아들이는 습관을 줄이고 결과를 설명하는 책임을 유지하자는 실무적 원칙은 분명합니다.

이 원칙을 확인하는 간단한 방법으로 변경 설명을 읽은 동료가 실제 동작을 예상할 수 있는지 살펴볼 수 있습니다. 예를 들어 캐시를 추가한 코드라면 무엇을 언제 저장하고 어떤 조건에서 오래된 값을 버리는지 제출자가 설명할 수 있어야 합니다. 테스트가 통과했다는 한 문장만으로는 이러한 약속이 드러나지 않습니다. 검토자는 정상 동작뿐 아니라 가정이 깨지는 조건을 함께 질문할 수 있습니다. 이때 AI가 작성했다는 사실을 별도의 낙인으로 삼을 필요는 없습니다. 사람이 직접 쓴 코드에도 같은 설명 책임을 적용하면 됩니다. 초안이라는 표현은 출처를 낮게 평가하려는 말이 아니라, 검토를 거쳐 팀이 이해하고 책임지는 변경으로 전환하는 단계가 필요하다는 뜻으로 활용할 수 있습니다.
