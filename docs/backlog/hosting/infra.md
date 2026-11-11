# 인프라

호스팅 서버의 AWS 구성을 정한다. 서버가 맡는 역할은 [실행 위치](README.md#실행-위치)를 따른다.

## 서버

| 항목 | 선택 | 이유 |
| --- | --- | --- |
| 서버 | EC2 `t3.medium` (2 vCPU / 4GB), 서울 리전 | Agent SDK가 질문마다 Claude Code 프로세스를 띄워 메모리 여유가 필요하다. ARM(`t4g`)은 이미지를 arm64로도 빌드해야 해서 처음에는 x86으로 간다 |
| 디스크 | EBS gp3 80GB | Android·iOS 레포는 리소스 때문에 클 수 있다 |
| OS | Ubuntu 24.04 LTS | |
| 실행 | Docker Compose | 서버를 다시 만드는 데 몇 분이면 된다 |

## 네트워크

| 항목 | 선택 | 이유 |
| --- | --- | --- |
| 외부 노출 | Cloudflare Tunnel | 들어오는 포트 0개. HTTPS 인증서가 자동으로 처리된다 |
| 운영자 셸 | SSM Session Manager | SSH 포트를 열지 않고, SSH 키도 관리하지 않는다 |
| 보안 그룹 | 인바운드 규칙 없음 | 모든 연결을 서버에서 밖으로 연다 |

클라이언트별 접속 방식과 인증은 [security.md](security.md#외부-노출과-인증)를 따른다.

## AWS 서비스

| 항목 | 선택 | 이유 |
| --- | --- | --- |
| 이미지 저장소 | ECR | 인스턴스 역할로 pull한다. 서버에 레지스트리 자격 증명을 두지 않는다 |
| 비밀값 | SSM Parameter Store (SecureString) | 배포 때 읽어 `.env`(권한 600)로 쓴다. 목록은 [비밀값 위치](security.md#권한과-비밀값) |
| 백업 | S3 | 인스턴스 역할로 올린다 |

## 인스턴스 역할

인스턴스 역할에는 아래 권한만 준다.

- SSM 관리 (`AmazonSSMManagedInstanceCore`)
- ECR pull
- Parameter Store `/gguk/*` 읽기
- 백업 버킷 쓰기

AWS 키는 서버와 레포 어디에도 저장하지 않는다. 배포는 [deploy.md](deploy.md#배포)를 따른다.
