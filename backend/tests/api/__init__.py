from pathlib import Path

# pytest 기본 모드에서 시험 패키지와 앱 패키지가 같은 이름으로 로드된다.
if __name__ == "api":
    __path__.append(str(Path(__file__).resolve().parents[2] / "api"))
