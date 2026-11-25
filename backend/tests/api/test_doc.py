from pathlib import Path


def test_R17_mock_doc() -> None:
    doc = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    assert doc.is_file()
    content = doc.read_text(encoding="utf-8")
    headings = set(content.splitlines())
    assert {
        "## 실행",
        "## 시험",
        "## A01 서버 상태",
        "## A02 축제 목록",
        "## A03 축제 상세",
        "## A04 귀갓길 접수",
        "## A05 귀갓길 조회",
        "## A25 가는 길 접수·조회",
        "## A06 챗봇 작업 접수",
        "## A06-1 챗봇 작업 조회",
        "## A32 가입",
        "## A33 로그인",
        "## A34 토큰 갱신",
        "## A35 로그아웃",
        "## X-Mock-Scenario",
        "## 가상 축제 6건",
        "## curl 예시",
        "### 축제 목록",
        "### 귀갓길 접수 → 조회",
        "### 챗봇 접수 → 조회",
    } <= headings
    assert "모든 값은 가상이며" in content
    assert "`is_mock: true`" in content
