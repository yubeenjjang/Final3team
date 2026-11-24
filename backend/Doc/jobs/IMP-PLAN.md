# 정기 작업 운영 예시

Claude가 대상 DB에 001~021 적용을 확인한 뒤 관리자 환경에서 022를 파일 단위 트랜잭션으로 적용한다. 배포 호스트에서는 API의 기존 `DB_*` 설정과 `DATA_GO_KR_SERVICE_KEY`를 사용한다. 좌표 보정이 필요한 환경은 기존 Kakao 설정을 함께 전달한다. 크론과 timer 중에서 호스트별로 하나를 선택한다. [022 마이그레이션](../../../Docs/Step%202/db/022_jobs.sql)

아래는 경로를 지정하는 예시다. 실제 체크아웃, 가상 환경, 보호된 환경 파일의 경로에 맞춘다. cron은 KST와 UTC 호스트에서 모두 매시 정각에 호출하며, 프로그램이 KST 06:00을 판정한다.

## cron

학원 노트북의 시연 계정 crontab 예시

```cron
0 * * * * cd "$HOME/noldaga" && (set -a; . "$HOME/.config/noldaga/api.env" && set +a && PYTHONPATH=backend "$HOME/noldaga/.venv/bin/python" -m api.jobs.scheduler) >> "$HOME/noldaga-jobs.log" 2>&1
```

AWS의 서비스 계정 crontab 예시

```cron
0 * * * * cd /opt/noldaga && (set -a; . /etc/noldaga/api.env && set +a && PYTHONPATH=backend /opt/noldaga/.venv/bin/python -m api.jobs.scheduler) >> /var/log/noldaga/jobs.log 2>&1
```

로그 경로에 서비스 계정 쓰기 권한을 부여하고 DB 7-0의 서버·워커 로그 정책에 따라 14일을 보존한다. 환경 파일은 해당 서비스 계정만 읽을 수 있게 배치한다.

## systemd timer

학원 노트북은 사용자 서비스(`~/.config/systemd/user/noldaga-jobs.service`) 예시다.

```ini
[Unit]
Description=Noldaga scheduled jobs

[Service]
Type=oneshot
WorkingDirectory=%h/noldaga
Environment=PYTHONPATH=backend
EnvironmentFile=%h/.config/noldaga/api.env
ExecStart=%h/noldaga/.venv/bin/python -m api.jobs.scheduler
```

AWS는 시스템 서비스(`/etc/systemd/system/noldaga-jobs.service`) 예시다.

```ini
[Unit]
Description=Noldaga scheduled jobs
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=noldaga
WorkingDirectory=/opt/noldaga
Environment=PYTHONPATH=backend
EnvironmentFile=/etc/noldaga/api.env
ExecStart=/opt/noldaga/.venv/bin/python -m api.jobs.scheduler
```

두 환경의 `noldaga-jobs.timer`에는 같은 설정을 사용한다.

```ini
[Unit]
Description=Run Noldaga jobs every hour

[Timer]
OnCalendar=*-*-* *:00:00 Asia/Seoul
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
```

- 학원 노트북은 `systemctl --user enable --now noldaga-jobs.timer`와 `journalctl --user -u noldaga-jobs.service`를 사용한다. 로그인 전 실행이 필요한 환경은 사용자 서비스 유지 설정을 배포 담당자가 적용한다.
- AWS는 `sudo systemctl enable --now noldaga-jobs.timer`와 `journalctl -u noldaga-jobs.service`를 사용한다.
- `purge_route_results`의 `status=ok` 간격이 65분을 넘거나 실행기가 0 이외 코드로 나오면 경보로 잡는다. 일일 작업은 당일 06:00 회차의 `status=ok`를 확인한다. cron의 로그 수집기와 systemd의 journal에서 작업별 한 줄을 확인한다.

## 검증과 되돌리기

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
bash 'Docs/Step 2/db/run_tests.sh'
```

DB 표시 시험은 001~022를 적용한 일회용 DB의 `TEST_DB_URL`로 실행한다. 시험 DB 관리자 연결로 서비스·앱 역할을 바꾸고 임시 LangGraph 테이블을 검증한다. 시험은 KST 회차, 중복 실행과 재시도, 권한, 022 적용·되돌리기·재적용과 보존값 경계를 확인한다. 022를 되돌릴 때는 먼저 예약 실행을 중지하고 `022_jobs_down.sql`을 사용한다. 이미 만료 처리한 데이터를 복원할 때는 DB 7-0의 백업·복원 정책을 적용한다.
