# 배포와 운영

호스팅 서버의 레포 최신화, 배포, 모니터링, 백업을 정한다. 위키 자체의 운영 방침은 [operations.md](../../operations.md)를 따른다.

## 레포 최신화

- syncer가 5분마다 4개 레포의 기본 브랜치를 `git fetch --depth 1` 후 `reset --hard`로 맞춘다. grep에는 최신 상태만 있으면 된다.
- 위키 merge는 최대 5분 늦게 반영된다. 이 지연이 문제가 되면 `/webhooks/github`로 바꾼다.
- 3회 연속 실패하면 `#봇-알림`에 알린다.

## 배포

1. main에 push하면 Actions가 이미지 3개를 빌드해 ECR에 커밋 SHA 태그로 올린다.
2. Actions가 OIDC로 배포 역할을 받는다.
3. `ssm send-command`로 서버에서 `render-env.sh`를 실행한 뒤 `TAG=<sha> docker compose pull && docker compose up -d`를 실행한다.
4. 되돌릴 때는 이전 SHA로 3번을 실행한다.

ECR 수명 주기 정책으로 최근 이미지 몇 개만 남긴다.

## 모니터링과 백업

| 항목 | 방식 |
| --- | --- |
| 컨테이너 | `restart: unless-stopped`, 헬스체크 |
| 서비스 감시 | 외부 업타임 체크(healthchecks.io 등)가 터널 URL의 `/health`를 확인하고, 실패하면 `#봇-알림`에 알린다 |
| 인스턴스 | EC2 상태 검사 실패 시 CloudWatch 알람으로 자동 복구 |
| OS | `unattended-upgrades`로 보안 업데이트 자동 적용 |
| sqlite | 매일 `.backup`을 떠 S3에 올리고 30일 보관 |
| EBS | Data Lifecycle Manager로 주 1회 스냅샷 |

훅은 시간 제한을 넘기면 조용히 통과하므로, 서버 장애가 개발 작업을 막지 않는다.
