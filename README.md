# Document Style Director

새 DOCX, Word, Google Docs 문서의 맥락을 분석해 적합한 시각 방향을 고르고,
확정된 디자인 토큰을 문서 제작 과정에 전달하는 Codex 스킬입니다.

이 스킬은 `documents` 스킬과 함께 사용하도록 설계되었습니다. 문서 작성과
렌더링은 `documents`가 담당하고, 이 저장소의 스킬은 스타일 선택과 잠금을
담당합니다.

## 다른 머신에 설치

먼저 해당 머신의 Codex에서 GitHub 인증을 완료합니다. 비공개 저장소이므로
GitHub CLI를 사용한다면 다음 명령으로 로그인할 수 있습니다.

```bash
gh auth login -h github.com
```

그다음 Codex 대화창에서 아래 프롬프트를 실행합니다.

```text
$skill-installer https://github.com/ffee21/document-style-director/tree/main/document-style-director
```

설치 후 바로 목록에 나타나지 않으면 Codex를 재시작합니다. `/skills`를 열거나
프롬프트에서 `$document-style-director`를 입력해 설치 여부를 확인할 수 있습니다.

## 사용

```text
$document-style-director 새 사업 제안서의 시각 방향을 정해줘.
```

사용자가 정확한 스타일을 지정하지 않은 새 문서나 대규모 리디자인에서 세 가지
맥락 적합 후보를 제안합니다. 사용자가 판단을 위임하면 추천 후보를 자동으로
선택해 스타일 계약을 잠급니다.

## 업데이트

`$skill-installer`는 같은 이름의 설치 폴더가 이미 있으면 중단합니다. 업데이트할
때는 기존 설치본을 제거한 뒤 위 설치 프롬프트를 다시 실행하거나, 저장소를 직접
clone해 Codex 사용자 스킬 경로에 심볼릭 링크로 연결하세요.

## 검증

```bash
python3 document-style-director/scripts/resolve_style.py --validate
python3 document-style-director/scripts/resolve_style.py --self-test
```

현재 카탈로그에는 13개 시각 시스템, 3개 밀도, 10개 오프닝,
41개 인증 레시피가 포함되어 있습니다.

## 참고

- [OpenAI 공식 스킬 문서](https://developers.openai.com/codex/skills)
- [Agent Skills 명세](https://agentskills.io/specification)
