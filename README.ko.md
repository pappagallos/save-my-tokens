# Save My Tokens

[English](README.md) · [한국어](README.ko.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

긴 로그에서 질문에 필요한 줄을 골라 보내고, 요청마다 작업에 맞는 모델을 선택합니다. 어떤 모델을 쓸지는 컴퓨터에서 규칙으로 판단하므로 분류 자체에 모델 호출이 들지 않습니다.

![질문의 단서로 긴 로그를 발췌한 뒤 모델 하나가 답하는 과정](docs/how-it-works.webp)

## 작동 원리

1. 파일에서 단서가 담긴 원문과 앞뒤 내용을 찾습니다. 기본 한도는 4,096바이트입니다. 원문 위치도 함께 남겨서 `--at BYTE`로 더 읽을 수 있습니다. 전체 발생 횟수는 파일 전체를 검색하세요.
2. 요청 문구를 보고 단순 추출·범위가 좁은 작업·일반 구현·깊은 추론 중 하나를 고르고, 선택한 플랫폼이 제공하는 모델에 연결합니다. 터미널에서 로그와 `--ask`를 함께 주면 질문과 발췌문을 Codex에 보냅니다.
3. 그림에서는 Sol 하나가 답합니다. 평소에는 한 번만 실행하고, 직접 비교를 요청할 때만 적용 전후의 답을 각각 얻습니다.

## 플랫폼별 설치

저장소를 내려받고 그 폴더에서 아래 명령을 실행하세요. `/path/to/project`에는 작업할 프로젝트 경로를, `cursor` 자리에는 표의 설치 ID를 넣으세요. 각 설치본에는 원문 발췌와 모델 선택에 필요한 파이썬 파일이 들어 있습니다. 프로젝트를 다시 열고 `save-my-tokens` 스킬을 선택하세요.

```sh
git clone https://github.com/pappagallos/save-my-tokens.git
cd save-my-tokens
python3 install.py --platform cursor --project /path/to/project
```

Codex 전용 플러그인은 내려받은 저장소에서 아래 명령으로 설치합니다. 새 Codex 대화에서 선택할 수 있습니다. 설치 후에도 저장소 폴더를 유지하세요.

```sh
codex plugin marketplace add .
codex plugin add save-my-tokens@save-my-tokens-local
codex plugin list --marketplace save-my-tokens-local --json
```

Python 3.9 이상과 Git이 필요합니다. 모델을 실행하려면 사용할 플랫폼의 CLI도 설치하세요. 작업 프로젝트에서 실행하려면 아래처럼 개인 명령 폴더에 연결할 수 있습니다.

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/save-my-tokens" "$HOME/.local/bin/save-my-tokens"
```

| 플랫폼 | 설치 ID | 프로젝트 폴더 | 터미널 모델 선택 |
|---|---|---|---|
| Codex CLI | `codex` | `.agents/skills/` | CLI 모델 목록 · `codex` |
| Claude Code | `claude` | `.claude/skills/` | 공급사 별칭 · `claude` |
| Cursor | `cursor` | `.cursor/skills/` | CLI 모델 목록 · `agent` |
| Gemini CLI | `gemini` | `.gemini/skills/` | ACP 모델 목록 · `gemini --acp` |
| Grok Build | `grok` | `.grok/skills/` | CLI 모델 목록 · `grok` |
| GitHub Copilot | `copilot` | `.github/skills/` | ACP 모델 목록 · `copilot --acp` |
| Devin | `devin` | `.devin/skills/` | ACP 모델 목록 · `devin acp` |
| OpenCode | `opencode` | `.opencode/skills/` | ACP 모델 목록 · `opencode acp` |
| Google Antigravity | `antigravity` | `.agent/skills/` | ACP 모델 목록 · `agy_acp_server.par` |
| Kiro | `kiro` | `.kiro/skills/` | ACP 모델 목록 · `kiro-cli acp` |
| TRAE | `trae` | `.trae/skills/` | ACP 모델 목록 · `traecli acp serve` |
| TRAE China | `trae-cn` | `.trae-cn/skills/` | ACP 모델 목록 · `traecli acp serve` |
| Qoder | `qoder` | `.qoder/skills/` | ACP 모델 목록 · `qodercli --acp` |
| Mistral Vibe | `vibe` | `.vibe/skills/` | ACP 모델 목록 · `vibe-acp` |
| Pi | `pi` | `.pi/skills/` | ACP 모델 목록 · `pi-acp` |
| Hermes Agent | `hermes` | `.hermes/skills/` | ACP 모델 목록 · `hermes acp` |
| DeepSeek Harness | `deepseek` | `.dsh/skills/` | ACP 모델 목록 · `dsh --profile acp` |
| Oh My Pi | `omp` | `.omp/skills/` | ACP 모델 목록 · `omp acp` |
| Replit Agent | `replit` | `.agents/skills/` | 외부 엔진 직접 선택 |
| Rovo Dev | `rovodev` | `.rovodev/skills/` | 외부 엔진 직접 선택 |
| Veto | `veto` | `.veto/skills/` | 외부 엔진 직접 선택 |

ACP는 터미널이 코딩 도구에 사용 가능한 모델을 묻고 질문을 보내기 전에 모델을 바꾸는 통신 방식입니다. 아래에 표시된 실행 파일을 설치하고 해당 계정에 로그인하세요. 편집기 안에서는 설치한 스킬로 로그를 바로 발췌할 수도 있습니다. Hermes는 프로젝트에서 `hermes skills trust`를 실행하고, Trae는 설치 후 다시 여세요. 개인 스킬만 읽는 Veto에서는 `--project "$HOME"`으로 설치합니다.

Claude의 연속 대화에는 `claude-agent-acp` 실행 파일이 추가로 필요합니다. ACP 방식은 해당 버전이 모델 목록을 제공해야 동작하며, 도구 실행 권한은 그대로 적용됩니다.

표의 각 행은 스킬을 설치할 수 있는 대상입니다. 실제 로그인 계정으로 답을 받은 환경은 Codex와 Claude Code입니다. 나머지 어댑터는 모의 CLI 또는 통신 응답으로 검사했습니다.

## 요청마다 모델 고르기

`route`는 모델 선택 결과를 보여줍니다. `task`는 질문을 실행합니다. `chat`은 같은 대화를 이어 가면서 매번 모델을 다시 고릅니다. 끝내려면 `/exit`를 입력하세요. 모델이 바뀌는 곳은 이 명령이 연 대화입니다. 이미 열려 있는 앱 대화의 모델은 앱이 관리합니다. 표에 ‘외부 엔진 직접 선택’이라고 표시된 플랫폼에서는 프로젝트 터미널에서 `--engine codex`처럼 로그인한 엔진을 명시하세요.

```sh
save-my-tokens route --engine codex '오류 코드를 추출해 줘'
save-my-tokens task --engine claude '파서를 구현해 줘'
save-my-tokens chat --engine codex
save-my-tokens build.log -q failure_code --ask '오류 코드를 추출해 줘'
```

각 단계에서 우선순위가 높은 모델 계열을 찾아 그 안에서 목록에 나온 가장 높은 버전을 고릅니다. 작업과 계열을 연결하는 규칙은 이 프로젝트에서 정했습니다. 목록은 계정·지역·CLI 버전에 따라 다릅니다. 제공 모델이 하나면 네 단계 모두 같은 모델을 씁니다. Claude 단건 실행은 공급사가 연결하는 Haiku·Sonnet·Opus 별칭을 씁니다. 목록이 비면 중단합니다. `--model ID`로 직접 지정하거나 `--tiers 경량 집중 일반 심층`으로 기준을 바꿀 수 있습니다. ‘계속해’는 직전 단계를 유지합니다. [Codex](https://learn.chatgpt.com/docs/non-interactive-mode) · [Claude Code](https://code.claude.com/docs/en/model-config) · [Cursor](https://cursor.com/docs/cli/reference/parameters) · [Grok Build](https://docs.x.ai/build/cli/reference) · [Gemini](https://geminicli.com/docs/cli/model/) · [ACP](https://agentclientprotocol.com/protocol/v1/session-config-options) · [ACP registry](https://github.com/agentclientprotocol/registry)

아래는 이 플러그인이 먼저 찾는 모델 계열입니다. 두 단계가 한 모델을 공유할 수 있습니다. 여러 회사의 모델을 연결하는 플랫폼은 그 계정의 목록에서 고릅니다. Claude Fable은 계정이 허용할 때 `--model fable`로 지정할 수 있습니다. 별칭은 공급사가 실제 버전에 연결하며 요금 조건도 공급사를 따릅니다.

| 작업 | 단순 추출 | 범위가 좁은 작업 | 일반 구현 | 깊은 추론 |
| --- | --- | --- | --- | --- |
|  | 문자열 추출·번역·짧은 요약 | 화면 캡처 확인, 한 파일이나 함수 안의 수정 | 기능 구현·일반 디버깅·리팩터링 | 간헐적 데이터 유실, 동시성 문제, 여러 서비스에 걸친 원인 분석 |
| Codex | Luna | Terra | Sol | Astra |
| Claude Code / Kiro | Haiku | Sonnet | Sonnet | Opus |
| Gemini / Antigravity | Flash-Lite | Flash | Flash | Pro |
| Cursor | Mini / Haiku | Composer / Terra | Sonnet / Sol | Opus / Astra |
| Grok Build | Non-reasoning / Fast | Build / Code | Build / Grok | Reasoning / Heavy / Grok |
| Copilot | Mini / Haiku | Terra / Flash | Sol / Sonnet | Astra / Opus |
| Devin | Haiku / Fast | SWE / Terra | Sonnet / Sol | Opus / Astra |
| Qoder | Efficient | Efficient | Performance / Fast | Ultimate |
| Mistral Vibe | Small / Mini | Devstral Small | Devstral / Medium | Large / Medium |
| DeepSeek Harness | Flash | Flash / Coder | Pro / Chat | Pro / Reasoner |
| TRAE / TRAE China | Flash / Mini | Coder / Seed | Sonnet / GLM / Qwen | Opus / Pro / Reasoner |
| OpenCode / Hermes / Pi / Oh My Pi | Luna / Haiku / Flash-Lite | Terra / Flash / Sonnet | Sol / Sonnet / Composer | Astra / Opus / Pro |

Replit과 Rovo Dev는 프로젝트 터미널에서 명시한 외부 CLI를 씁니다. Rovo 자체 대화는 `/models` 메뉴로 변경할 수 있습니다. oleg-koval의 Veto CLI에서 `task --host veto --engine codex`는 선택한 모델로 `veto start`를 실행합니다. 다른 Veto 제품은 프로젝트 터미널에서 외부 CLI를 직접 선택할 수 있습니다. [Devin](https://docs.devin.ai/cli/models) · [Copilot](https://docs.github.com/en/copilot/reference/ai-models/supported-models) · [OpenCode](https://opencode.ai/docs/models/) · [Qoder](https://docs.qoder.com/cli/model) · [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/) · [Mistral](https://docs.mistral.ai/models) · [Rovo](https://support.atlassian.com/rovo/docs/switch-between-large-language-models-in-rovo-dev-cli/) · [Veto](https://github.com/oleg-koval/veto)

```sh
save-my-tokens models --engine codex
save-my-tokens models --engine gemini
save-my-tokens models --engine qoder
save-my-tokens route --host replit --engine claude 'fix a typo'
```

## 질문 하나의 적용 전후 비교

같은 로그와 같은 질문을 준비합니다. `compare`는 계정에서 두 번 실행합니다. 파일을 주면 기본으로 같은 모델을 써서 발췌 효과만 비교합니다. 파일 없이 실행하면 일반 모델로 답한 결과와 자동 선택한 모델로 답한 결과를 비교합니다. 첫 모델은 `--baseline-model`로 바꿀 수 있습니다. 실제 사용량 비교는 Codex와 Claude Code에서 지원합니다. 다른 플랫폼에서도 `measure`로 원문과 발췌문의 크기를 기기에서 비교할 수 있습니다. 이 값은 OpenAI의 `o200k_base` 방식으로 센 추정치입니다.

```sh
python3 experiments/benchmark.py --write-log /tmp/smt-example.log
question='Extract the missing key and failure code. Return both values.'
./save-my-tokens compare "$question" --file /tmp/smt-example.log -q failure_code \
  --expect SNAPSHOT_CLOCK --expect E7429 --out results.jsonl
./save-my-tokens compare --engine claude "$question" --file /tmp/smt-example.log -q failure_code
uv run --with tiktoken==0.12.0 -- ./save-my-tokens measure "$question" --file /tmp/smt-example.log -q failure_code
```

질문마다 양쪽 모델, 입력·캐시 입력·출력·합계, 소요 시간, 두 답변, 기대 문자열 포함 여부를 기록합니다. 캐시 입력은 입력에 이미 포함됩니다. 절감량은 적용 전 합계에서 적용 후 합계를 뺀 값이며 음수면 더 사용한 것입니다. `--out`을 지정하면 질문과 답변이 해당 파일에 누적됩니다.

## 실제 측정 결과

| 질문 | 모델 | 적용 전 → 후 (총 토큰) | 감소율 | 답변 확인 |
|---|---|---|---|---|
| 빠진 설정 키와 오류 코드 | Luna | 21,259 → 16,243 | 23.59% | 양쪽 정답 |
| 257번 모듈의 경과 시간 | Luna | 21,262 → 16,249 | 23.58% | 양쪽 모두 `15` |
| 빠진 설정 키와 오류 코드 | Haiku 5.5 | 13,112 → 4,070 | 68.96% | 양쪽 정답 |
| 뜻이 모호한 단위 이름 질문 | Sol | 25,882 → 20,871 | 19.36% | 두 답변이 다름 |

같은 합성 로그에서 질문·모델 조합당 한 쌍씩 실행했습니다. 단위 이름을 모호하게 물은 경우 `milliseconds`와 `module_257`로 답이 갈렸습니다. 문자열이 포함됐는지만 검사하면 의미가 맞았는지 판단하기 어렵습니다. 합계에는 서비스가 붙인 지침도 포함됩니다. 구독 한도·요금·평균 절감률은 이 실험으로 측정하지 않았습니다. 모델을 바꾸면 캐시 재사용량도 달라질 수 있습니다. [JSONL](experiments/observations.jsonl) · [v0.2.0 · 한국어](experiments/v0.2.ko.md)

## 연구와 README 설계 근거

Nature의 OpenScholar 연구는 질문에 맞는 문단을 찾아 출처를 남기는 방법을 평가했습니다. npj Digital Medicine 연구는 긴 입력에서 근거 위치를 바꿔 답의 정확성을 비교했습니다. 이를 참고해 파일 중간도 검색하고 원문 위치를 남겼습니다. 플러그인은 문자열 검색을 사용하며, 절감 효과는 로그 실험에서 따로 측정했습니다. [Nature · OpenScholar](https://www.nature.com/articles/s41586-025-10072-4) · [npj Digital Medicine](https://www.nature.com/articles/s41746-025-01651-w) · [2025 JIF](https://www.nature.com/nature-portfolio/about-journals/journal-metrics)

Superpowers는 작업 흐름과 플랫폼별 설치를 먼저 보여줍니다. Context7은 같은 요청의 결과를 비교하고, RTK는 절감량을 측정하는 명령을 제공합니다. Impeccable은 예시 그림과 지원 표를 붙여 놓았습니다. 이 README에는 정답 유지 여부와 답이 달라진 경우도 함께 실었습니다. [Superpowers](https://github.com/obra/superpowers) · [Context7](https://github.com/upstash/context7) · [RTK](https://github.com/rtk-ai/rtk) · [Impeccable](https://github.com/pbakaus/impeccable/tree/d41d9860b0094dcb68030657da63461212835aaa)

추천 점수가 보인 Codex 글 중에는 같은 파일을 거듭 읽거나 긴 명령 출력을 보내는 일을 줄였다는 경험담이 +298점이었습니다. 모델 자동 선택을 직접 다룬 글 중에는 가벼운 작업을 Luna에 맡긴 글이 +21점이었습니다. 11월에는 여러 작업에서 모델을 나눠 썼을 때 비용과 정확도를 비교한 Claude Code 후속 실험도 공개됐습니다. 점수는 검색 당시 표시값이며 각 실험은 작성자의 작업 환경에 한정됩니다. [r/codex · +298](https://www.reddit.com/r/codex/comments/1tyxkzj/how_i_cut_codex_token_use_from_138mday_to_20mday/) · [r/codex · +21](https://www.reddit.com/r/codex/comments/1vdbi4s/luna_just_got_80_cheaper_so_i_rebuilt_my_codex/) · [r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1xxyc5a/does_delegating_to_cheaper_models_actually_save/)
