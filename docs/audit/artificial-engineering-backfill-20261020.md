# Artificial Engineering Edition 1–64 백필 감사 기록

검사일: 2026-10-20. 이번 작업은 사용자가 명시적으로 요청한 일회성 백필이며 새 스케줄은 만들지 않았습니다.

검증을 마친 한국어 원고는 **62개**이며, 미확인 번호는 **1, 2**입니다. 이번 작업의 Discord 전송은 **0개**, 새 메시지 ID는 없습니다. 1호의 번호 근거를 확보하지 못해 엄격한 오름차순 발행을 시작하지 않았습니다.

## 확인 방법과 편집

- 8개 배치로 나누어 6개 조사 에이전트를 병렬 실행하고, 완료된 에이전트에 남은 배치를 배정했습니다. 조사와 원고는 분리된 디렉터리에서 작성했으며 부모 에이전트가 공통 파일과 최종 manifest를 관리했습니다.
- LinkedIn 공개 원문 전체와 저자 공개 아카이브를 확인했습니다. 로그인 제한을 우회하지 않았습니다. 검색 결과의 발췌만으로 본문을 검증하지 않았습니다.
- 확인된 호는 원본 표지의 번호를 직접 읽고, canonical URL과 원문 제목 및 JSON-LD의 저자·실제 발행일을 대조했습니다. 날짜 간격으로 발행번호를 채우지 않았습니다.
- 원문에서 작성자 본문을 추출한 UTF-8 텍스트의 SHA-256을 기록했습니다. 호별 추출 방식은 manifest의 source_hash_method에 있습니다. 원문 HTML·전문·표지 이미지는 공개 저장소에 넣지 않았습니다.
- 본문은 3~5문단, 250~350 공백 어절의 한국어 해설입니다. 제목·메타데이터·프로젝트 목록·편집주는 본문 어절 계산에서 제외합니다. 저자의 주장과 편집자의 적용 해석을 구분했습니다.
- 초기 호는 별도 말미 목록 없이 주제별 기술 소개가 글 전체에 분산되어 있습니다. 이 경우 원문에 연결된 모든 소개를 원래 순서대로 목록에 보존했습니다.
- 검증된 원고의 프로젝트·기술 소개 항목은 총 611개입니다. 목록 개수·이름·원문 링크와 Markdown ID·해시를 manifest와 대조했습니다.

## 확인이 끝나지 않은 번호

- **Edition 1**: 공개 원문 후보와 실제 발행일·전체 소개는 확인했지만, 원문 표지·본문·공유 게시물에서 Edition 1 번호를 명시한 근거를 확인하지 못했습니다. 발행순서와 날짜로 번호를 추정하지 않았습니다.
- **Edition 2**: 공개 원문 후보와 실제 발행일·전체 소개는 확인했지만, 원문 표지·본문·공유 게시물에서 Edition 2 번호를 명시한 근거를 확인하지 못했습니다. 발행순서와 날짜로 번호를 추정하지 않았습니다.

번호가 확인되지 않은 원문 후보의 실제 제목·URL·발행일은 manifest의 unassigned_candidate_articles에 별도로 기록했습니다. 후보 글을 해당 번호의 확정 원고로 저장하거나 발행하지 않았습니다.

## 원문의 불일치

- Edition 50 도입부는 주요 글 외에 26개 주제가 있다고 설명하지만, 공개 HTML과 공개 웹 본문 모두 완결된 말미 목록은 25개입니다. 마지막 항목과 감사 인사까지 확인했고 실제 25개를 전부 수록했습니다. 원문에 없는 항목은 만들지 않았으며 원고에 이 불일치를 편집주로 밝혔습니다.
- Edition 26은 말미 목록 7개 외에 마지막에 추가된 GitHub Spec Kit 링크까지 포함해 8개 자료를 보존했습니다.

## 전송 안전장치와 검증

- 기존 로컬 discord-feed 스킬 코드는 변경하지 않았습니다. 이미 완성된 Markdown만 기존 sender가 분할하고 Discord로 전송합니다. 별도 모델 API를 호출하지 않았습니다.
- manifest가 active인 경우에만 1~64호를 숫자 순서대로 처리합니다. 첫 미확인 호에서 멈춥니다. 현재 manifest는 held입니다.
- 각 호를 보내기 전에 원격 main에 in-flight 표식을 저장하고, 완료 후 메시지 ID가 담긴 ledger를 원격 main에 저장·재조회한 다음 다음 호로 진행합니다.
- 원격 충돌 때는 최신 main의 다른 변경과 기존 ledger 기록을 보존합니다. 메시지 ID·내용 해시 충돌, 불확실한 전송, 남은 in-flight 표식은 수동 대조가 필요하며 무조건 재실행하지 않습니다.
- 기존 4개 분할 테스트와 13개 백필 테스트가 로컬에서 통과했습니다. 테스트에는 순서·누락호 중지·중복 생략·실패 중지·불확실성·실제 로컬 bare Git 저장소의 동시 변경 보존·완료 후 기존 피드 복귀가 포함됩니다.
- 안전장치 PR #1은 main에 병합되었고 Actions 검증에 성공했습니다: [PR 검증](https://github.com/JinhaPark/drops/actions/runs/39416304248), [main 검증](https://github.com/JinhaPark/drops/actions/runs/39416357067). 최종 아카이브 변경의 추가 Actions 결과는 해당 PR/커밋의 Checks에서 확인할 수 있습니다.

## 기존 전송 이력과 보존

- 기준 main: f98f2b750d4ff099eee09afe2ecde8bb4a26658d. 기존 ledger에는 스모크 테스트 1건, Elevate 5건, Artificial Engineering 65~69호 5건의 완료 기록이 있습니다.
- 과거 Actions 39356371117은 Discord 전송 단계 성공 뒤 원격 main 변경으로 ledger push가 거절되어 실패했습니다. 이후 최신 실행 39358438901은 성공했고 기존 11개 기록은 모두 complete입니다. 과거 실패 이력을 삭제하거나 성공으로 바꾸지 않았습니다.
- 기존 65~69호, Elevate 원고 10개와 ledger의 바이트를 보존했습니다. 이번 백필에서 이를 수정하거나 재전송하지 않았습니다.
- 기존 ledger SHA-256: `917298b13bb3602f692dd33fac6ebaa7fa92bbdb5e1c2cc0499e30513d0dbd1a`.

| 보존 파일 | SHA-256 |
|---|---|
| `articles/elevate/2026-08-27-audit-your-agent-files.md` | `36c90f313decaebd04c756f2998966291559a2619aac296f278ae1a34a37b7cb` |
| `articles/elevate/2026-08-31-agentic-skill-decay.md` | `e26b48ab09554e25552280a53e3b4499fdab162af94fc3b2be19559e4486a8c6` |
| `articles/elevate/2026-09-14-brownfield-agentic-engineering.md` | `6a618c1e8a3c4ac0f73e54f8d7ffbeae58eea9ff570883308cc8b89539325626` |
| `articles/elevate/2026-09-28-the-code-nobody-reads.md` | `71f4c54f34adfc825c52211435c71cf6d399ab93beb32206bfd94ee8bddef949` |
| `articles/elevate/2026-10-14-agentic-verification.md` | `e8ce15e72082f4511418058fdf2c73a5a3b18ae8f4b532be04f626ca8764584e` |
| `articles/artificial-engineering/2026-07-25-edition-65.md` | `b0400aefde0177baee7a62a277fdc0d9df3b108292fd7096e44506d7049d1f6a` |
| `articles/artificial-engineering/2026-08-01-edition-66.md` | `dc3d317945735c6008059fe769bf3e18c80d784093a5794751872f422539c78f` |
| `articles/artificial-engineering/2026-08-08-edition-67.md` | `2763ecb177de87d9386a8c387bb8615ad25a832aeaf873fcea7e6e0860d575a7` |
| `articles/artificial-engineering/2026-08-15-edition-68.md` | `8e251885b6e30aad705cd9d4a85537e4880afa9d8b8e9b357866e6c11ac0ba2d` |
| `articles/artificial-engineering/2026-08-22-edition-69.md` | `1e434a09f9218d5d8b7f83bfa3398e673f45541345be44177939b29c86d5d092` |

## 발행번호별 기록

Markdown은 저장소 경로이며, 링크가 없는 행은 번호 검증이 끝나지 않아 원고를 생성하지 않은 항목입니다. 전송 보류 상태에서 Discord 메시지 ID를 임의로 만들지 않았습니다.

| Edition | Markdown 경로 | 원문 | 원고 검증 | Discord 전송 | Discord 메시지 ID |
|---:|---|---|---|---|---|
| 1 | — | 미확정 | 미완료 | 미전송 | — |
| 2 | — | 미확정 | 미완료 | 미전송 | — |
| 3 | [articles/artificial-engineering/2025-05-18-edition-3.md](../../articles/artificial-engineering/2025-05-18-edition-3.md) | [원문](https://www.linkedin.com/pulse/architecting-ai-from-visualization-trust-andr%C3%A9-lindenberg-zcoie) | 완료 · 281어절 · 7항목 | 순서 보류 | — |
| 4 | [articles/artificial-engineering/2025-05-25-edition-4.md](../../articles/artificial-engineering/2025-05-25-edition-4.md) | [원문](https://www.linkedin.com/pulse/profiting-from-code-ethics-efficiency-ai-engineering-andr%C3%A9-lindenberg-yaf9e) | 완료 · 286어절 · 4항목 | 순서 보류 | — |
| 5 | [articles/artificial-engineering/2025-06-01-edition-5.md](../../articles/artificial-engineering/2025-06-01-edition-5.md) | [원문](https://www.linkedin.com/pulse/from-legacy-fear-smart-platforms-ais-role-software-andr%C3%A9-lindenberg-h5hoe) | 완료 · 286어절 · 7항목 | 순서 보류 | — |
| 6 | [articles/artificial-engineering/2025-06-08-edition-6.md](../../articles/artificial-engineering/2025-06-08-edition-6.md) | [원문](https://www.linkedin.com/pulse/building-ai-from-foundations-future-opportunities-andr%C3%A9-lindenberg-216ke) | 완료 · 289어절 · 6항목 | 순서 보류 | — |
| 7 | [articles/artificial-engineering/2025-06-15-edition-7.md](../../articles/artificial-engineering/2025-06-15-edition-7.md) | [원문](https://www.linkedin.com/pulse/mastering-ai-driven-transformation-scaling-migration-andr%C3%A9-lindenberg-fnife) | 완료 · 286어절 · 9항목 | 순서 보류 | — |
| 8 | [articles/artificial-engineering/2025-06-22-edition-8.md](../../articles/artificial-engineering/2025-06-22-edition-8.md) | [원문](https://www.linkedin.com/pulse/convergence-ai-architecture-from-decomposition-reuse-andr%C3%A9-lindenberg-mbwje) | 완료 · 295어절 · 7항목 | 순서 보류 | — |
| 9 | [articles/artificial-engineering/2025-06-29-edition-9.md](../../articles/artificial-engineering/2025-06-29-edition-9.md) | [원문](https://www.linkedin.com/pulse/adaptive-ai-scalable-architectures-reinventing-andr%C3%A9-lindenberg-5xbie) | 완료 · 273어절 · 7항목 | 순서 보류 | — |
| 10 | [articles/artificial-engineering/2025-07-06-edition-10.md](../../articles/artificial-engineering/2025-07-06-edition-10.md) | [원문](https://www.linkedin.com/pulse/navigating-dual-paths-ai-integration-andr%C3%A9-lindenberg-1ejfe) | 완료 · 265어절 · 8항목 | 순서 보류 | — |
| 11 | [articles/artificial-engineering/2025-07-13-edition-11.md](../../articles/artificial-engineering/2025-07-13-edition-11.md) | [원문](https://www.linkedin.com/pulse/ai-memory-revolution-agentic-systems-motion-andr%C3%A9-lindenberg-lpoxe) | 완료 · 277어절 · 6항목 | 순서 보류 | — |
| 12 | [articles/artificial-engineering/2025-07-20-edition-12.md](../../articles/artificial-engineering/2025-07-20-edition-12.md) | [원문](https://www.linkedin.com/pulse/pioneering-mindsets-ai-development-andr%C3%A9-lindenberg-qokae) | 완료 · 276어절 · 5항목 | 순서 보류 | — |
| 13 | [articles/artificial-engineering/2025-07-27-edition-13.md](../../articles/artificial-engineering/2025-07-27-edition-13.md) | [원문](https://www.linkedin.com/pulse/engineering-evolution-ai-from-autonomy-efficiency-andr%C3%A9-lindenberg-zglqe) | 완료 · 276어절 · 7항목 | 순서 보류 | — |
| 14 | [articles/artificial-engineering/2025-08-03-edition-14.md](../../articles/artificial-engineering/2025-08-03-edition-14.md) | [원문](https://www.linkedin.com/pulse/evolution-agentic-ai-system-transformation-andr%C3%A9-lindenberg-e71ge) | 완료 · 267어절 · 7항목 | 순서 보류 | — |
| 15 | [articles/artificial-engineering/2025-08-10-edition-15.md](../../articles/artificial-engineering/2025-08-10-edition-15.md) | [원문](https://www.linkedin.com/pulse/navigating-ai-agent-landscape-from-tools-threats-andr%C3%A9-lindenberg-8n5ue) | 완료 · 276어절 · 7항목 | 순서 보류 | — |
| 16 | [articles/artificial-engineering/2025-08-17-edition-16.md](../../articles/artificial-engineering/2025-08-17-edition-16.md) | [원문](https://www.linkedin.com/pulse/from-secure-systems-endless-possibilities-andr%C3%A9-lindenberg-3xs7e) | 완료 · 279어절 · 9항목 | 순서 보류 | — |
| 17 | [articles/artificial-engineering/2025-08-24-edition-17.md](../../articles/artificial-engineering/2025-08-24-edition-17.md) | [원문](https://www.linkedin.com/pulse/from-prompt-engineering-ai-driven-ecosystems-building-lindenberg-iavre) | 완료 · 281어절 · 5항목 | 순서 보류 | — |
| 18 | [articles/artificial-engineering/2025-08-31-edition-18.md](../../articles/artificial-engineering/2025-08-31-edition-18.md) | [원문](https://www.linkedin.com/pulse/navigating-intersection-ai-trust-andr%C3%A9-lindenberg-szq1e) | 완료 · 266어절 · 8항목 | 순서 보류 | — |
| 19 | [articles/artificial-engineering/2025-09-07-edition-19.md](../../articles/artificial-engineering/2025-09-07-edition-19.md) | [원문](https://www.linkedin.com/pulse/transformative-shifts-from-trust-tactical-deployments-lindenberg-y9nce) | 완료 · 262어절 · 13항목 | 순서 보류 | — |
| 20 | [articles/artificial-engineering/2025-09-14-edition-20.md](../../articles/artificial-engineering/2025-09-14-edition-20.md) | [원문](https://www.linkedin.com/pulse/orchestrating-ai-agents-from-audits-acceleration-andr%C3%A9-lindenberg-qdsme) | 완료 · 266어절 · 11항목 | 순서 보류 | — |
| 21 | [articles/artificial-engineering/2025-09-21-edition-21.md](../../articles/artificial-engineering/2025-09-21-edition-21.md) | [원문](https://www.linkedin.com/pulse/deterministic-systems-explainable-agents-andr%C3%A9-lindenberg-laose) | 완료 · 280어절 · 13항목 | 순서 보류 | — |
| 22 | [articles/artificial-engineering/2025-09-28-edition-22.md](../../articles/artificial-engineering/2025-09-28-edition-22.md) | [원문](https://www.linkedin.com/pulse/shaping-ai-reasoning-explainability-productivity-andr%C3%A9-lindenberg-reeae) | 완료 · 259어절 · 7항목 | 순서 보류 | — |
| 23 | [articles/artificial-engineering/2025-10-05-edition-23.md](../../articles/artificial-engineering/2025-10-05-edition-23.md) | [원문](https://www.linkedin.com/pulse/unlocking-efficiency-transparency-andr%C3%A9-lindenberg-ndpqe) | 완료 · 262어절 · 9항목 | 순서 보류 | — |
| 24 | [articles/artificial-engineering/2025-10-12-edition-24.md](../../articles/artificial-engineering/2025-10-12-edition-24.md) | [원문](https://www.linkedin.com/pulse/building-thinking-machine-how-ai-moves-from-scale-andr%C3%A9-lindenberg-ei4ae) | 완료 · 267어절 · 11항목 | 순서 보류 | — |
| 25 | [articles/artificial-engineering/2025-10-19-edition-25.md](../../articles/artificial-engineering/2025-10-19-edition-25.md) | [원문](https://www.linkedin.com/pulse/shifting-gears-from-scale-context-ai-andr%C3%A9-lindenberg-p0the) | 완료 · 250어절 · 8항목 | 순서 보류 | — |
| 26 | [articles/artificial-engineering/2025-10-26-edition-26.md](../../articles/artificial-engineering/2025-10-26-edition-26.md) | [원문](https://www.linkedin.com/pulse/specengineering-when-intent-becomes-sourceoftruth-andr%C3%A9-lindenberg-c5m7e) | 완료 · 252어절 · 8항목 | 순서 보류 | — |
| 27 | [articles/artificial-engineering/2025-11-02-edition-27.md](../../articles/artificial-engineering/2025-11-02-edition-27.md) | [원문](https://www.linkedin.com/pulse/navigating-agentic-automation-andr%C3%A9-lindenberg-cwroe) | 완료 · 256어절 · 7항목 | 순서 보류 | — |
| 28 | [articles/artificial-engineering/2025-11-09-edition-28.md](../../articles/artificial-engineering/2025-11-09-edition-28.md) | [원문](https://www.linkedin.com/pulse/memory-sovereignty-talent-andr%C3%A9-lindenberg-glyxe) | 완료 · 254어절 · 9항목 | 순서 보류 | — |
| 29 | [articles/artificial-engineering/2025-11-16-edition-29.md](../../articles/artificial-engineering/2025-11-16-edition-29.md) | [원문](https://www.linkedin.com/pulse/navigating-complexity-ai-leadership-andr%C3%A9-lindenberg-xsqle) | 완료 · 267어절 · 3항목 | 순서 보류 | — |
| 30 | [articles/artificial-engineering/2025-11-23-edition-30.md](../../articles/artificial-engineering/2025-11-23-edition-30.md) | [원문](https://www.linkedin.com/pulse/ai-driven-modernization-from-trustworthy-systems-andr%C3%A9-lindenberg-fodee) | 완료 · 258어절 · 8항목 | 순서 보류 | — |
| 31 | [articles/artificial-engineering/2025-11-30-edition-31.md](../../articles/artificial-engineering/2025-11-30-edition-31.md) | [원문](https://www.linkedin.com/pulse/ai-driven-re-engineering-it-systems-andr%C3%A9-lindenberg-idn2e) | 완료 · 263어절 · 6항목 | 순서 보류 | — |
| 32 | [articles/artificial-engineering/2025-12-07-edition-32.md](../../articles/artificial-engineering/2025-12-07-edition-32.md) | [원문](https://www.linkedin.com/pulse/navigating-ai-geo-intelligence-andr%C3%A9-lindenberg-zewqe) | 완료 · 272어절 · 7항목 | 순서 보류 | — |
| 33 | [articles/artificial-engineering/2025-12-14-edition-33.md](../../articles/artificial-engineering/2025-12-14-edition-33.md) | [원문](https://www.linkedin.com/pulse/enabling-ai-comprehend-legacy-code-senior-engineer-level-lindenberg-upf8f) | 완료 · 262어절 · 5항목 | 순서 보류 | — |
| 34 | [articles/artificial-engineering/2025-12-21-edition-34.md](../../articles/artificial-engineering/2025-12-21-edition-34.md) | [원문](https://www.linkedin.com/pulse/enabling-ainative-data-architectures-one-use-case-time-lindenberg-qiere) | 완료 · 263어절 · 4항목 | 순서 보류 | — |
| 35 | [articles/artificial-engineering/2025-12-28-edition-35.md](../../articles/artificial-engineering/2025-12-28-edition-35.md) | [원문](https://www.linkedin.com/pulse/bridging-data-decision-ais-expanding-role-software-andr%C3%A9-lindenberg-hva4f) | 완료 · 265어절 · 7항목 | 순서 보류 | — |
| 36 | [articles/artificial-engineering/2026-01-04-edition-36.md](../../articles/artificial-engineering/2026-01-04-edition-36.md) | [원문](https://www.linkedin.com/pulse/how-smaller-ai-systems-quietly-winning-andr%C3%A9-lindenberg-ebgwf) | 완료 · 274어절 · 6항목 | 순서 보류 | — |
| 37 | [articles/artificial-engineering/2026-01-11-edition-37.md](../../articles/artificial-engineering/2026-01-11-edition-37.md) | [원문](https://www.linkedin.com/pulse/emerging-era-recursive-language-models-andr%C3%A9-lindenberg-z86ff) | 완료 · 266어절 · 6항목 | 순서 보류 | — |
| 38 | [articles/artificial-engineering/2026-01-18-edition-38.md](../../articles/artificial-engineering/2026-01-18-edition-38.md) | [원문](https://www.linkedin.com/pulse/unpacking-ai-contextual-reasoning-visualization-andr%C3%A9-lindenberg-xwkjf) | 완료 · 263어절 · 7항목 | 순서 보류 | — |
| 39 | [articles/artificial-engineering/2026-01-25-edition-39.md](../../articles/artificial-engineering/2026-01-25-edition-39.md) | [원문](https://www.linkedin.com/pulse/shaping-ai-landscapes-from-memory-systems-geospatial-andr%C3%A9-lindenberg-xrasf) | 완료 · 264어절 · 12항목 | 순서 보류 | — |
| 40 | [articles/artificial-engineering/2026-02-01-edition-40.md](../../articles/artificial-engineering/2026-02-01-edition-40.md) | [원문](https://www.linkedin.com/pulse/why-most-powerful-llms-cant-rewrite-old-erp-yet-andr%C3%A9-lindenberg-jjwsf) | 완료 · 258어절 · 11항목 | 순서 보류 | — |
| 41 | [articles/artificial-engineering/2026-02-07-edition-41.md](../../articles/artificial-engineering/2026-02-07-edition-41.md) | [원문](https://www.linkedin.com/pulse/evals-foundation-reliable-ai-agents-andr%C3%A9-lindenberg-tcgoe) | 완료 · 250어절 · 10항목 | 순서 보류 | — |
| 42 | [articles/artificial-engineering/2026-02-14-edition-42.md](../../articles/artificial-engineering/2026-02-14-edition-42.md) | [원문](https://www.linkedin.com/pulse/when-ai-meets-backend-andr%C3%A9-lindenberg-sotuf) | 완료 · 254어절 · 6항목 | 순서 보류 | — |
| 43 | [articles/artificial-engineering/2026-02-22-edition-43.md](../../articles/artificial-engineering/2026-02-22-edition-43.md) | [원문](https://www.linkedin.com/pulse/ontology-moat-andr%C3%A9-lindenberg-jpowf) | 완료 · 259어절 · 11항목 | 순서 보류 | — |
| 44 | [articles/artificial-engineering/2026-03-01-edition-44.md](../../articles/artificial-engineering/2026-03-01-edition-44.md) | [원문](https://www.linkedin.com/pulse/from-solo-agent-parallel-fleet-andr%C3%A9-lindenberg-ncspf) | 완료 · 252어절 · 16항목 | 순서 보류 | — |
| 45 | [articles/artificial-engineering/2026-03-08-edition-45.md](../../articles/artificial-engineering/2026-03-08-edition-45.md) | [원문](https://www.linkedin.com/pulse/closing-context-gap-why-ontologies-missing-layer-ai-andr%C3%A9-lindenberg-2bhef) | 완료 · 262어절 · 8항목 | 순서 보류 | — |
| 46 | [articles/artificial-engineering/2026-03-14-edition-46.md](../../articles/artificial-engineering/2026-03-14-edition-46.md) | [원문](https://www.linkedin.com/pulse/memory-problem-one-talks-why-ai-agents-need-two-andr%C3%A9-lindenberg-spjvf) | 완료 · 259어절 · 12항목 | 순서 보류 | — |
| 47 | [articles/artificial-engineering/2026-03-21-edition-47.md](../../articles/artificial-engineering/2026-03-21-edition-47.md) | [원문](https://www.linkedin.com/pulse/minimize-surprise-maximize-agency-what-active-teaches-lindenberg-q39tf) | 완료 · 255어절 · 14항목 | 순서 보류 | — |
| 48 | [articles/artificial-engineering/2026-03-28-edition-48.md](../../articles/artificial-engineering/2026-03-28-edition-48.md) | [원문](https://www.linkedin.com/pulse/context-cores-end-memento-nightmare-why-agent-memory-needs-andr%C3%A9-r1q1f) | 완료 · 251어절 · 14항목 | 순서 보류 | — |
| 49 | [articles/artificial-engineering/2026-04-04-edition-49.md](../../articles/artificial-engineering/2026-04-04-edition-49.md) | [원문](https://www.linkedin.com/pulse/why-production-ai-needs-engineering-discipline-more-andr%C3%A9-lindenberg-av02f) | 완료 · 265어절 · 14항목 | 순서 보류 | — |
| 50 | [articles/artificial-engineering/2026-04-11-edition-50.md](../../articles/artificial-engineering/2026-04-11-edition-50.md) | [원문](https://www.linkedin.com/pulse/mempalace-milla-jovovich-48-hour-audit-when-open-andr%C3%A9-lindenberg-1akvf) | 완료 · 266어절 · 25항목 | 순서 보류 | — |
| 51 | [articles/artificial-engineering/2026-04-18-edition-51.md](../../articles/artificial-engineering/2026-04-18-edition-51.md) | [원문](https://www.linkedin.com/pulse/from-consulting-decks-slash-commands-enterprise-goes-andr%C3%A9-lindenberg-sifjf) | 완료 · 268어절 · 19항목 | 순서 보류 | — |
| 52 | [articles/artificial-engineering/2026-04-25-edition-52.md](../../articles/artificial-engineering/2026-04-25-edition-52.md) | [원문](https://www.linkedin.com/pulse/how-ship-token-efficient-coding-agent-your-team-andr%C3%A9-lindenberg-nvirf) | 완료 · 278어절 · 27항목 | 순서 보류 | — |
| 53 | [articles/artificial-engineering/2026-05-02-edition-53.md](../../articles/artificial-engineering/2026-05-02-edition-53.md) | [원문](https://www.linkedin.com/pulse/agentic-primitives-six-levers-agent-sovereignty-andr%C3%A9-lindenberg-vkn3f) | 완료 · 285어절 · 8항목 | 순서 보류 | — |
| 54 | [articles/artificial-engineering/2026-05-09-edition-54.md](../../articles/artificial-engineering/2026-05-09-edition-54.md) | [원문](https://www.linkedin.com/pulse/why-agents-need-world-model-andr%C3%A9-lindenberg-9cc6e) | 완료 · 282어절 · 9항목 | 순서 보류 | — |
| 55 | [articles/artificial-engineering/2026-05-16-edition-55.md](../../articles/artificial-engineering/2026-05-16-edition-55.md) | [원문](https://www.linkedin.com/pulse/substrate-shrinks-when-31gb-rag-becomes-4gb-laptop-andr%C3%A9-lindenberg-p2ngf) | 완료 · 286어절 · 11항목 | 순서 보류 | — |
| 56 | [articles/artificial-engineering/2026-05-23-edition-56.md](../../articles/artificial-engineering/2026-05-23-edition-56.md) | [원문](https://www.linkedin.com/pulse/log-agent-event-sourced-architectures-take-stack-andr%C3%A9-lindenberg-p98af) | 완료 · 276어절 · 17항목 | 순서 보류 | — |
| 57 | [articles/artificial-engineering/2026-05-30-edition-57.md](../../articles/artificial-engineering/2026-05-30-edition-57.md) | [원문](https://www.linkedin.com/pulse/map-only-surface-andr%C3%A9-lindenberg-bp87f) | 완료 · 257어절 · 13항목 | 순서 보류 | — |
| 58 | [articles/artificial-engineering/2026-06-06-edition-58.md](../../articles/artificial-engineering/2026-06-06-edition-58.md) | [원문](https://www.linkedin.com/pulse/modernization-loop-needs-score-andr%C3%A9-lindenberg-6fwqf) | 완료 · 266어절 · 19항목 | 순서 보류 | — |
| 59 | [articles/artificial-engineering/2026-06-13-edition-59.md](../../articles/artificial-engineering/2026-06-13-edition-59.md) | [원문](https://www.linkedin.com/pulse/own-harness-change-model-equation-andr%C3%A9-lindenberg-dueze) | 완료 · 264어절 · 12항목 | 순서 보류 | — |
| 60 | [articles/artificial-engineering/2026-06-20-edition-60.md](../../articles/artificial-engineering/2026-06-20-edition-60.md) | [원문](https://www.linkedin.com/pulse/memory-should-change-future-behavior-andr%C3%A9-lindenberg-genve) | 완료 · 265어절 · 14항목 | 순서 보류 | — |
| 61 | [articles/artificial-engineering/2026-06-27-edition-61.md](../../articles/artificial-engineering/2026-06-27-edition-61.md) | [원문](https://www.linkedin.com/pulse/from-prompts-loops-next-step-agent-engineering-andr%C3%A9-lindenberg-wnqre) | 완료 · 261어절 · 13항목 | 순서 보류 | — |
| 62 | [articles/artificial-engineering/2026-07-04-edition-62.md](../../articles/artificial-engineering/2026-07-04-edition-62.md) | [원문](https://www.linkedin.com/pulse/plan-loop-before-you-build-andr%C3%A9-lindenberg-y0t1e) | 완료 · 264어절 · 14항목 | 순서 보류 | — |
| 63 | [articles/artificial-engineering/2026-07-11-edition-63.md](../../articles/artificial-engineering/2026-07-11-edition-63.md) | [원문](https://www.linkedin.com/pulse/memory-model-isnt-allowed-write-andr%C3%A9-lindenberg-mqjse) | 완료 · 256어절 · 9항목 | 순서 보류 | — |
| 64 | [articles/artificial-engineering/2026-07-18-edition-64.md](../../articles/artificial-engineering/2026-07-18-edition-64.md) | [원문](https://www.linkedin.com/pulse/more-machines-slower-model-still-worth-andr%C3%A9-lindenberg-isufe) | 완료 · 267어절 · 9항목 | 순서 보류 | — |

기계 판독용 전체 메타데이터·원문 해시·Markdown 해시·표지 번호 근거·프로젝트 목록은 [발행 manifest](../../data/artificial-engineering-backfill.json)에 있습니다.
