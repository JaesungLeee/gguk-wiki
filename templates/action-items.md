---
source:                       # raw/ 아래 원본 경로. 이 파일의 경로도 원본 경로를 따른다
# domains: []                 # 선택
items:
  - task:
    assignee: []              # 맡은 사람 목록. people.yml의 name. 팀은 그 role의 팀원 전원으로 펼친다. 목록에 없으면 "알 수 없음", 정해지지 않았으면 "미정"
    # due:                    # YYYY-MM-DD. 원본에 있을 때만 쓴다
    status: open              # open(끝나지 않음) | done(끝남) | dropped(하지 않기로 함)
---
