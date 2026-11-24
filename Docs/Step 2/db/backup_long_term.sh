#!/usr/bin/env bash
# 012 적용 DB의 7일 보존용 논리 백업. pg_dump 접속 및 출력 옵션을 그대로 전달한다.
set -euo pipefail
exec pg_dump --format=custom --exclude-table-data=public.route_results "$@"
