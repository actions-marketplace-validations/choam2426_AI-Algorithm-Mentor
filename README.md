# 🤖 AI Algorithm Mentor

> **AI 기반 알고리즘 코드 리뷰 시스템**  
> 온라인 저지 플랫폼의 알고리즘 문제 풀이를 자동으로 분석하고 전문적인 피드백을 제공하는 GitHub Action

[![GitHub release](https://img.shields.io/github/release/choam2426/AI-Algorithm-Mentor.svg)](https://github.com/choam2426/AI-Algorithm-Mentor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 주요 기능

### 🧠 **지능형 코드 분석**
- 알고리즘 문제의 핵심 요구사항과 제약 조건 자동 파악
- 시간/공간 복잡도 분석 및 최적화 제안
- 코딩 컨벤션 및 가독성 개선 제안

### 🔗 **Online Judge 자동 감지 & 크롤링**
- 변경 파일의 첫 줄 주석에서 문제 URL 자동 감지
- 플랫폼 감지: 백준(지원), 프로그래머스/LeetCode(확장 예정)
- 백준 문제 페이지를 크롤링해 제목/설명/입출력/예제를 Markdown으로 수집

### 💬 **자동 커밋 코멘트**
- LLM 결과를 GitHub Commit 코멘트로 자동 게시

### 🌐 **다중 플랫폼 지원**
- **백준** (acmicpc.net) - 지원
- **프로그래머스** (programmers.co.kr) - 예정
- **LeetCode** (leetcode.com) - 예정

### 🤖 **다중 AI 모델 지원**
- **OpenAI** (GPT-4, GPT-4o, GPT-4o-mini)
- **Google AI** (Gemini-2.5-Pro)
- **Anthropic** (Claude-3-Sonnet)

### 🌏 **다국어 리뷰**
- 리뷰 응답 언어 선택 가능
- 한국어, 영어 등 LLM이 지원하는 모든 언어

---

## 🚀 사용 방법

### 1. API 키 준비

지원하는 AI 제공자 중 하나의 API 키를 준비하세요:

| 제공자 | API 키 발급 | 환경변수명 |
|--------|------------|-----------|
| **OpenAI** | [OpenAI API](https://openai.com/api/) | `OPENAI_API_KEY` |
| **Google AI** | [Google AI Studio](https://aistudio.google.com/) | `GOOGLE_API_KEY` |
| **Anthropic** | [Anthropic Console](https://console.anthropic.com/) | `ANTHROPIC_API_KEY` |

### 2. GitHub Repository 설정

1. **Secrets 등록**: Repository → Settings → Secrets and variables → Actions
   ```
   OPENAI_API_KEY=your_api_key_here  # 또는 다른 제공자의 API 키
   ```

2. **GitHub Action 워크플로우 생성**: `.github/workflows/ai-review.yml`
   ```yaml
   name: 🤖 AI Algorithm Mentor
   
   on:
     push:
       branches: [ main, master ]
   
   jobs:
     ai-review:
       runs-on: ubuntu-latest
       permissions:
         contents: write
       steps:
          - uses: choam2426/AI-Algorithm-Mentor@v4
           with:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
             LLM_PROVIDER: openai              # openai, google, anthropic
             LLM_MODEL: gpt-4o                 # 모델명 (선택사항)
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
             REVIEW_LANGUAGE: korean           # korean, english, etc..
   ```

### 3. 코드 작성 및 커밋

직접 커밋으로 알고리즘 문제 풀이를 올리면 자동으로 AI 리뷰가 생성됩니다!

❗❗❗코드의 첫 줄에는 반드시 해당 문제의 URL을 주석으로 추가해주세요!❗❗❗
예) `# https://www.acmicpc.net/problem/1000`
---

## 📖 코드 예시

```python
# https://www.acmicpc.net/problem/1000
a, b = map(int, input().split())
print(a + b)
```

## ⚙️ 설정 옵션

### 환경 변수

| 변수명 | 설명 | 기본값 | 예시 |
|--------|------|-------|------|
| `LLM_PROVIDER` | AI 제공자 | `openai` | `openai`, `google`, `anthropic` |
| `LLM_MODEL` | 사용할 모델 | `gpt-4o` | `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-pro`, `claude-3-sonnet` |
| `REVIEW_LANGUAGE` | 리뷰 언어 | `korean` | `korean`, `english` |
| `OPENAI_API_KEY` | OpenAI API 키 | - | 필수 (openai 사용시) |
| `GOOGLE_API_KEY` | Google AI API 키 | - | 필수 (google 사용시) |
| `ANTHROPIC_API_KEY` | Anthropic API 키 | - | 필수 (anthropic 사용시) |
| `GITHUB_TOKEN` | GitHub API 토큰 | GitHub Actions 기본 제공 | 커밋 코멘트 게시에 필요 |

## 🏗️ 아키텍처

```mermaid
graph TD
    A[GitHub Action] --> B[AI Algorithm Mentor]
    B --> C[설정 관리 (config)]
    B --> D[Git 변경 파일 수집 (github_service)]
    B --> E[OJ 감지 (online_judge)]
    B --> F[문제 크롤러 (problem_info_crawler)]
    B --> G[프롬프트 (prompt)]
    B --> H[LLM 팩토리 (llm_factory)]
    B --> I[GitHub 코멘트 (github_service)]

    H --> H1[OpenAI]
    H --> H2[Google AI]
    H --> H3[Anthropic]
```

### 기여하기

1. Fork 후 feature branch 생성
2. 변경사항 구현 및 테스트
3. Pull Request 생성

---

## 📋 지원 범위

- **프로그래밍 언어**: Python, Java, C++, C, JavaScript, Go, Rust
- **문제 플랫폼**: 백준
- **리뷰 언어**: 한국어, 영어 등 LLM이 지원하는 언어

---

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

---

## 📞 문의

- **Issues**: [GitHub Issues](https://github.com/choam2426/AI-Algorithm-Mentor/issues)
- **개발자**: [choam2426](https://github.com/choam2426)

### 관련 프로젝트

- [사용 예시](https://github.com/choam2426/OnlineJudge) - 개발자가 실제 적용하고 있는 레포