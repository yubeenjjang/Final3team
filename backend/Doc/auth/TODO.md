# 자체 인증 작업 현황

- [x] A32 가입과 001·009의 계정·프로필 제약 연결
- [x] A33 Argon2id 검증, Access JWT·Refresh 발급, IP별 로그인 한도
- [x] A34 Refresh 교체·동시 요청 차단·재사용 시 계정 전체 Refresh 폐기
- [x] A35 본인 Refresh·Access 폐기 및 DB-19 요청용 RLS 의존성 연결
- [x] 기본 모의 모드 유지, DB 모드 단위·로그 차단·PostgreSQL 시험 작성
- [ ] 공통 Redis 연결 뒤 인증 상태 어댑터를 교체하고 여러 API 프로세스에서 폐기·요청 제한을 검증
