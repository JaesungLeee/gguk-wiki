---
source:                       # raw/ 아래 원본 경로. 이 파일의 경로도 원본 경로를 따른다
items:
  - question:
    domains: []               # domains.yml에서 1개 이상
    kind:                     # product(사용자에게 보이는 동작, 정책, 화면 규칙, 디자인) | tech(두 플랫폼 이상이 함께 지키는 계약과 기술 결정)
    status: open              # open(정해지지 않음) | resolved(결정으로 해소됨) | dropped(결정 없이 더 다루지 않음)
    # resolved_by:            # resolved일 때 필수. 해소한 결정 경로
---
