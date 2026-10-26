---
id: artificial-engineering:what-agents-cant-promise
source_id: artificial-engineering
canonical_url: https://www.linkedin.com/pulse/what-agents-cant-promise-green-main-honest-log-kept-andr%C3%A9-lindenberg-wxeef
author: André Lindenberg
published_at: 2026-10-25
source_sha256: d6937c49f95d02364bc04d70148d14ed4024e61e726a1f4b5bd4bbeb6754736d
editorial_version: ko-300words-v1
status: ready
roundup_verified: true
---

# [What Agents Can't Promise: A Green Main, an Honest Log, a Kept Secret](https://www.linkedin.com/pulse/what-agents-cant-promise-green-main-honest-log-kept-andr%C3%A9-lindenberg-wxeef)

2026-10-25 · André Lindenberg

병렬 코딩 에이전트가 한 저장소에서 하루 수천 건의 변경을 합칠 때, 충돌 없이 병합됐다는 사실과 전체 시스템이 정상 동작한다는 사실은 별개입니다. André Lindenberg는 Anthropic이 자체 소스 관리 시스템 Scion을 설명하면서 제기한 문제를 출발점으로 삼습니다. 전통적인 병합 대기열은 선행 변경을 포함한 상태에서 테스트한 뒤 다음 변경을 받아들입니다. 하지만 규모가 커지면 대기열 자체가 병목이 되므로, Anthropic은 병합 이후이면서 배포 이전인 단계에서 검증하는 방식으로 옮겼다고 소개합니다. 이는 생산성을 높이는 대신, 한동안 main 브랜치가 실패 상태일 가능성을 운영 절차가 받아들여야 한다는 뜻입니다.

오픈소스 프로젝트 gitai는 이 문제에 구체적인 구현 사례를 제시합니다. 각 에이전트가 제출한 변경을 서버가 현재 main 끝에 재배치한 다음, 다른 변경이 먼저 들어오지 않았을 때만 원자적으로 반영하는 compare-and-swap 방식을 사용합니다. 여러 제출은 묶어서 처리할 수도 있습니다. 별도의 검증기 graft-verify는 새로 병합된 코드를 일정 시간 모아 테스트하고, 성공한 커밋을 가리키는 별도의 green 참조를 갱신합니다. 실패하면 먼저 재실행해 불안정한 테스트 가능성을 확인하고, 마지막 정상 상태와 오류 상태 사이의 커밋을 이진 탐색하여 최초 실패 지점을 찾습니다. 자동 되돌리기는 운영자의 허가와 시간당 한도 아래에서만 허용됩니다. 핵심은 코드를 바꾸는 에이전트와 정상 여부를 판정하고 되돌릴 권한을 가진 주체를 분리하는 것입니다.

gitai가 제시한 실험은 에이전트 50개가 총 250개 변경을 같은 브랜치에 제출하고, 그 가운데 20%는 의도적으로 충돌하도록 구성했습니다. 서버가 변경을 묶어 처리할 때 200개가 반영됐지만, 에이전트가 각자 재배치와 재시도를 수행하면 100~106개에 그쳤습니다. 다만 이는 변경을 얼마나 빨리 받아들이는지를 측정했을 뿐, 전체 통합 테스트의 성공률이나 장애 복구 시간을 증명한 것은 아닙니다. 특히 서로 다른 파일을 수정한 두 변경이 합쳐졌을 때만 발생하는 의미적 오류는 단순 충돌 해결만으로 막지 못합니다. 성능 수치를 시스템 안정성의 근거로 오해하지 말아야 하는 이유입니다.

실무에서는 새로운 버전 관리 시스템을 도입하지 않아도 원칙을 적용할 수 있습니다. GitHub Actions가 통합 테스트를 통과한 마지막 커밋만 별도 태그나 브랜치로 표시하고, 다음 에이전트의 작업 시작점과 배포 기준을 그 정상 참조에 맞추는 방식을 검토할 수 있습니다. 빠른 개별 검사는 병합 전에, 전체 검증과 제한된 자동 되돌리기는 병합 후에 배치합니다. 테스트 코드는 에이전트가 마음대로 변경하거나 무력화할 수 없게 보호하고, 실행 환경은 네트워크 및 비밀정보 접근 권한을 제한해야 합니다. 같은 글에서 소개한 Tracekit의 서명된 실행 기록과 Harness²의 비교 실험도 이러한 독립 검증 원칙을 보완합니다. 무엇보다 실패를 빨리 찾아낸 기록과 복구 권한이 에이전트의 자기 보고와 분리돼 있는지가 자동화의 신뢰도를 결정합니다.

### 주간 GitHub 및 기술 프로젝트

- [Tracekit](https://github.com/Cygnux-Labs/Tracekit): 에이전트가 실행한 도구 호출을 해시 체인으로 묶고 기록과 실제 실행을 교차 검증해, 뒤늦게 수정되거나 빠진 호출을 찾아낼 수 있도록 하는 감사 도구입니다.

- [Harness²](https://github.com/google-research/harness2): 동일한 과제에 대해 원본 하네스와 두 가지 변경 후보를 비교하여 성능 근거가 있는 수정만 유지하는 연구 프로젝트입니다. 원문은 비교 없이 하네스를 바꾸면 코딩 점수가 73.4에서 63.2로 낮아졌다고 소개합니다.

