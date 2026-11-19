import re
from pathlib import Path

TOPICS = ("서버 하드웨어", "Linux·부팅", "네트워크·광케이블", "랙·현장 운영")
LP = ("Ownership", "Dive Deep", "Earn Trust", "Bias for Action",
      "Learn and Be Curious", "Insist on the Highest Standards", "Deliver Results",
      "Customer Obsession")


def load_questions():
    questions = {}
    source = Path(__file__).with_name("questions.txt")
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        key, tag, level, ko, en, checks, guide, follow = line.split("|")
        kind = "기술" if key.startswith("T") else "행동"
        valid_tags = TOPICS if kind == "기술" else LP
        criteria = checks.split(" / ")
        if (key in questions or not re.fullmatch(r"[TB][0-9]{2}", key)
                or tag not in valid_tags or level not in ("기초", "심화")
                or not all(part.strip() for part in (ko, en, *criteria, guide, follow))
                or not 3 <= len(criteria) <= 5):
            raise ValueError(f"문항 데이터 오류 [{key}]")
        questions[key] = dict(id=key, revision=1, kind=kind, tag=tag, level=level,
                              ko=ko, en=en, checks=criteria, guide=guide, follow=follow)
    if sum(q["kind"] == "기술" for q in questions.values()) != 24 or len(questions) != 40:
        raise ValueError("기술 24문항과 행동 16문항이 필요합니다.")
    return questions


if __name__ == "__main__":
    print(f"{len(load_questions())} questions validated")
