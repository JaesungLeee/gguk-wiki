# 조회 규칙

위키와 코드 레포를 조회할 때 따른다. 공통 규칙은 [`AGENTS.md`](../AGENTS.md)에 있다.

## 읽는 기준

위키와 코드 레포 모두 각 레포의 GitHub default 브랜치(`origin/HEAD`)를 읽는다. 작업 폴더는 읽지 않는다.

```bash
git -C ~/gguk/Team-MINO-Node fetch --quiet origin
git -C ~/gguk/Team-MINO-Node remote set-head origin --auto     # default 브랜치 변경을 따라간다
git -C ~/gguk/Team-MINO-Node grep -n -I RefundPolicy origin/HEAD
git -C ~/gguk/Team-MINO-Node show origin/HEAD:<경로>
```

- 같은 세션에서 직전 fetch 후 일정 시간이 지나지 않았으면 fetch를 생략한다.
- 오프라인이면 마지막으로 fetch한 상태로 답하고, 기준 시각을 함께 표시한다.

## 위키 조회

1. `wiki/index.md`로 질문에 맞는 도메인을 고르고, 그 도메인 페이지(`wiki/domains/<도메인>.md`)를 읽는다. 맞는 도메인이 없으면 건너뛴다.
2. [질의 정규화](#질의-정규화) 규칙으로 검색어를 만든다.
3. grep으로 보충한다. 도메인 태그가 틀렸거나 빠진 문서를 찾기 위해서다.
4. 후보 결정의 본문을 읽는다.
5. 대체된 결정(`status: superseded`)은 빼고 답한다. 이력을 묻는 질문일 때만 넣고 `(대체됨 → 새 결정 경로)`를 함께 표시한다.
6. 위키에서 답을 찾지 못하면 없다고 답한다. 추측으로 채우지 않는다.

- 미결을 물으면 도메인 페이지의 미결 목록을 읽는다.
- 최근 바뀐 결정을 물으면 `wiki/log.md`를 읽는다.
- 액션 아이템을 물으면 `wiki/action-items.md`를 읽는다. 기한이 지났는지는 오늘 날짜로 판단해 답에 표시한다.

## 질의 정규화

1. 명사와 어간으로 검색한다. 조사(은/는/이/가/에서/으로 등), 어미(합니다/하는/되나요 등), 불용어(확인, 설명 등)를 붙이지 않는다.
2. `RefundPolicy.calculate`, `v1.2` 같은 식별자는 쪼개지 않고 하나의 검색어로 유지한다.
3. 기획 용어가 [용어집](../wiki/glossary.md)에 있으면 레포별 심볼명을, 없으면 영어 직역을 검색어로 추가한다.
4. 결과가 없으면 동의어나 영어 이름으로 바꿔 다시 찾는다.

| 질문 | 검색어 |
| --- | --- |
| 환불 기한은 어떻게 되나요? | `환불`, `기한` + 영어 직역 `refund` |
| 보관함에서 방을 지우면 어떻게 돼? | `보관함`, `삭제` + 용어집 `SavedRoom`(Node, Android), `Archive`(iOS) |

## 코드 조회

- 레포는 `~/gguk/` 아래의 `Team-MINO-Node`, `Team-MINO-Android`, `Team-MINO-iOS`다. 없으면 `scripts/setup-workspace.sh` 실행을 안내한다.
- 구현 위치(경로, 줄 번호)는 위키에 적지 않는다. 조회할 때마다 코드에서 찾는다.
- 용어집의 심볼이 코드에서 찾히지 않으면 "용어집 심볼 `SavedRoom`을 Team-MINO-Node default 브랜치에서 찾지 못함"으로 표시하고, 영어 직역과 동의어로 다시 찾는다. 새 이름을 찾으면 용어집 수정을 제안만 한다. 반영은 채팅 입력으로 ingest한다.
- 위키 없이 코드만 물어도 된다. 예: "iOS는 푸시 토큰을 언제 서버에 보내?" → Team-MINO-iOS만 찾는다.

## 답변 형식

1. 참조한 위키 페이지, 원본(`raw/`), 날짜를 붙인다.
2. 코드는 `레포:경로 (브랜치 @ 짧은 커밋 SHA)`로 출처를 붙인다. 예: `Team-MINO-Node:src/.../refund.ts (main @ a1b2c3d)`
3. 위키와 코드가 다르면 불일치로 표시하고 양쪽 출처를 모두 붙인다.
4. 오프라인이라 fetch하지 못했으면 기준 시각을 붙인다.
