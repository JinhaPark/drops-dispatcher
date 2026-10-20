---
id: "elevate:good-code-is-like-a-love-letter-to"
source_id: "elevate"
archive_index: 10
canonical_url: "https://addyo.substack.com/p/good-code-is-like-a-love-letter-to"
author: "Addy Osmani"
published_at: "2023-12-21"
source_sha256: "73b7e795360b8fc2506f9fc3efd8f74b6e9e8f275cc3e30d3a634d2b9da1d234"
source_sha256_method: "Web-rendered public article body; navigation, reactions, comments and final subscription prompt excluded; link markers reduced to labels; whitespace normalized within paragraphs; UTF-8 SHA-256"
editorial_version: "ko-300eojeol-v1"
status: "ready"
---

# [Good code is like a love letter to the next developer who will maintain it.](https://addyo.substack.com/p/good-code-is-like-a-love-letter-to)

2023.12.21 · Addy Osmani · Elevate

Addy Osmani는 좋은 코드를 다음 유지보수 담당자와 나누는 의사소통으로 설명합니다. 프로그램이 작동하는 것만으로는 충분하지 않습니다. 작성자가 떠난 뒤에도 다른 사람이 의도와 구조를 이해해야 합니다. 명확한 이름과 일관된 형식, 오류 처리와 테스트는 그 이해를 돕는 장치입니다. 저자는 이런 선택을 동료에 대한 배려로 봅니다. 오늘의 문제를 해결하는 코드가 내일의 팀에 불필요한 부담을 남기지 않도록 작성해야 한다는 주장입니다.

설계 패턴은 반복되는 문제를 설명하는 공통 언어로 활용할 수 있습니다. 그러나 유명한 패턴을 적용했다는 사실 자체가 좋은 설계를 보장하지는 않습니다. 단순한 문제에 과도한 추상화를 넣으면 읽는 사람의 부담이 커집니다. 글은 현대 언어의 함수형 기능도 대안으로 검토하고, 구체적인 문제에 어떤 방식이 명확한지 판단하라고 권합니다. 기존 동작을 유지하면서 구조를 개선하는 리팩터링도 이러한 지속적인 관리의 일부입니다.

AI 코드 생성은 이 논의를 없애기보다 사람이 판단해야 할 지점을 드러냅니다. 빠르게 생성한 코드라도 읽기 어렵다면 이후 수정에서 비용을 치를 수 있습니다. 저자는 AI를 반복 작업을 돕는 협력자로 보되, 맥락에 맞는 설계와 유지보수 가능성은 개발자가 살펴야 한다고 설명합니다. 코드의 가치는 작성 순간의 속도뿐 아니라 다른 사람이 안전하게 이해하고 발전시킬 수 있는지에서도 드러납니다.

이 관점을 실무에 적용해 보면, 예를 들어 할인 금액을 계산하는 함수를 검토할 때 계산식만 확인해서는 부족합니다. 금액의 단위와 반올림 기준, 할인 적용 순서가 이름이나 테스트에서 드러나는지 함께 볼 수 있습니다. 이런 질문은 줄 수를 줄이는 일과도 다릅니다. 짧지만 숨은 전제가 많은 코드보다 필요한 전제가 분명한 코드가 검토하기 쉬울 수 있기 때문입니다. 팀의 검토 기준을 정할 때는 처음 보는 동료가 어떤 질문을 하게 될지 상상해 보는 편이 유용합니다. 그 질문에 답하는 정보가 코드 가까이에 있는지, 변경했을 때 깨지는 약속을 테스트가 알려 주는지 점검할 수 있습니다. 이는 글의 비유를 구체적인 검토 행동으로 옮기는 한 가지 방법입니다.
