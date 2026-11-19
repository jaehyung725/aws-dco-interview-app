import copy
import math
import random
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

import streamlit as st

from content import load_questions
from storage import Store, empty_profile
from personal import render_feedback, render_personal

st.set_page_config(page_title="DCO 면접 연습", page_icon="🧰", layout="centered")
QUESTION = load_questions()
STAR = ("상황 (Situation)", "과제 (Task)", "행동 (Action)", "결과 (Result)")
PAGES = ("홈", "질문은행", "모의면접", "맞춤형", "기록")

token = st.query_params.get("practice", "")
if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
    token = secrets.token_urlsafe(32)
    st.query_params["practice"] = token

try:
    store = Store(token)
    revision, profile = store.load()
except (OSError, sqlite3.Error):
    st.error("저장소를 열 수 없습니다. 잠시 후 새로고침해 주세요.")
    st.stop()

state = st.session_state
if state.get("profile_token") != token:
    state.clear()
    state.profile_token = token
state.setdefault("page", "홈")
state.setdefault("language", "한국어")


def commit(updated):
    global profile, revision
    try:
        revision = store.save(revision, updated)
    except (OSError, sqlite3.Error):
        st.error("저장하지 못했습니다. 이 탭의 답변을 유지했습니다. 다른 탭을 닫고 다시 시도해 주세요.")
        return False
    profile = updated
    return True


def navigate(page, question_id=None):
    state.page = page
    state.question_id = question_id
    state.review_id = None


def title_for(question):
    return question["en"] if state.language == "English" else question["ko"]


def has_answer(answer):
    return any(part.strip() for part in answer)


def show_question(question):
    st.caption(f'{question["id"]} · {question["kind"]} · {question["tag"]} · {question["level"]}')
    st.markdown(f'#### {title_for(question)}')


def edit_answer(scope, question, saved):
    labels = STAR if question["kind"] == "행동" else ("답변",)
    return [
        st.text_area(label, value=saved[index] if index < len(saved) else "",
                     key=f"answer_{scope}_{index}", height=110, max_chars=4000)
        for index, label in enumerate(labels)
    ]


def attempt(question, answer, session_id=None):
    return dict(question=question, answer=answer, checks=[], submitted=time.time(),
                session_id=session_id)


def review(attempt_id, entry):
    question = entry["question"]
    show_question(question)
    labels = STAR if question["kind"] == "행동" else ("답변",)
    for label, answer in zip(labels, entry["answer"]):
        st.markdown(f"**{label}**")
        st.text(answer or "미작성")
    st.markdown("**자기점검**")
    selected = [
        index for index, label in enumerate(question["checks"])
        if st.checkbox(label, value=index in entry["checks"], key=f"check_{attempt_id}_{index}")
    ]
    st.caption(f'{len(question["checks"])}개 중 {len(selected)}개 확인')
    if selected != entry["checks"]:
        updated = copy.deepcopy(profile)
        updated["attempts"][attempt_id]["checks"] = selected
        if commit(updated):
            st.caption("자기점검 저장 완료")
    st.markdown("**해설**")
    st.write(question["guide"])
    st.markdown("**꼬리질문**")
    st.write(question["follow"])


def home():
    st.markdown("### 기술 면접과 STAR 답변을 연습하세요")
    st.write("장애 상황에서 무엇을 먼저 확인할지 설명하고, 실제 경험에서 본인이 한 일을 정리해 보세요.")
    completed = {entry["question"]["id"] for entry in profile["attempts"].values()}
    left, right = st.columns(2)
    left.metric("완료 문항", f"{len(completed)} / {len(QUESTION)}")
    right.metric("제출한 답변", len(profile["attempts"]))
    mock = profile["mock"]
    if mock and mock["status"] == "active":
        st.button("모의면접 이어서 열기", type="primary", on_click=navigate, args=("모의면접",))
    if profile["drafts"]:
        latest = max(profile["drafts"], key=lambda key: profile["drafts"][key]["updated"])
        if latest in QUESTION:
            st.button("초안 이어서 연습", on_click=navigate, args=("질문은행", latest))
    standard, personal = st.columns(2)
    with standard:
        st.markdown("#### 표준형")
        st.write("기존 한·영 40문항과 자기점검으로 연습합니다.")
        st.button("표준형으로 시작", type="primary", on_click=navigate, args=("질문은행",))
    with personal:
        st.markdown("#### 맞춤형")
        st.write("내 경험으로 질문을 만들고 AI 답변 피드백을 받습니다.")
        st.button("맞춤형으로 시작", type="primary", on_click=navigate, args=("맞춤형",))


def question_bank():
    st.header("질문은행")
    question_id = state.get("question_id")
    if question_id in QUESTION:
        st.button("질문 목록", on_click=navigate, args=("질문은행",))
        practice(QUESTION[question_id])
        return

    all_label = "전체"
    kind = st.selectbox("유형", (all_label, "기술", "행동"), key="kind_filter")
    available = [q for q in QUESTION.values() if kind in (all_label, q["kind"])]
    topics = sorted({q["tag"] for q in available})
    tag = st.selectbox("주제 또는 Leadership Principle", [all_label, *topics], key=f"tag_{kind}")
    level = st.selectbox("난이도", (all_label, "기초", "심화"), key="level_filter")
    matches = [q for q in available if tag in (all_label, q["tag"]) and level in (all_label, q["level"])]
    st.caption(f"{len(matches)}문항")
    if not matches:
        st.info("선택한 조건에 맞는 문항이 없습니다.")
    st.button("필터 초기화", on_click=reset_filters)
    completed = {entry["question"]["id"] for entry in profile["attempts"].values()}
    for q in matches:
        question_id = q["id"]
        progress = " · 초안" if question_id in profile["drafts"] else ""
        if not progress and question_id in completed:
            progress = " · 완료"
        st.button(f'{question_id} · {title_for(q)}{progress}', key=f'open_{q["id"]}', width="stretch",
                  on_click=navigate, args=("질문은행", q["id"]))


def reset_filters():
    for key in ("kind_filter", "level_filter", "tag_전체", "tag_기술", "tag_행동"):
        state.pop(key, None)


def practice(question):
    question_id = question["id"]
    reviewed = state.get("review_id")
    if reviewed in profile["attempts"]:
        review(reviewed, profile["attempts"][reviewed])
        st.button("다시 풀기", on_click=navigate, args=("질문은행", question_id))
        return
    show_question(question)
    draft = profile["drafts"].get(question_id, {})
    saved = draft.get("answer", [])
    answer = edit_answer(question_id, question, saved)
    if answer != saved and (saved or has_answer(answer)):
        updated = copy.deepcopy(profile)
        if has_answer(answer):
            updated["drafts"][question_id] = dict(answer=answer, updated=time.time())
        else:
            updated["drafts"].pop(question_id, None)
        if commit(updated):
            st.caption("초안 저장 완료")
    if question["kind"] == "행동" and has_answer(answer) and not all(part.strip() for part in answer):
        st.caption("미작성 항목이 있습니다.")
    if st.button("제출하고 검토", type="primary", disabled=not has_answer(answer)):
        updated = copy.deepcopy(profile)
        attempt_id = uuid.uuid4().hex
        updated["attempts"][attempt_id] = attempt(question, answer)
        updated["drafts"].pop(question_id, None)
        if commit(updated):
            state.review_id = attempt_id
            st.rerun()


def start_mock():
    technical = [q for q in QUESTION.values() if q["kind"] == "기술"]
    behavioral = [q for q in QUESTION.values() if q["kind"] == "행동"]
    selected = random.sample(technical, 3) + random.sample(behavioral, 2)
    updated = copy.deepcopy(profile)
    updated["mock"] = dict(id=uuid.uuid4().hex, questions=selected, index=0,
                           deadline=time.time() + 900, answers={}, skipped=[], status="active")
    if commit(updated):
        st.rerun()


def finish_mock(updated, status):
    mock = updated["mock"]
    if mock["status"] != "active":
        return
    mock["status"] = status
    for q in mock["questions"]:
        answer = mock["answers"].get(q["id"], [])
        if has_answer(answer):
            attempt_id = f'{mock["id"]}_{q["id"]}'
            updated["attempts"][attempt_id] = attempt(q, answer, mock["id"])
    if commit(updated):
        st.rerun()


@st.fragment(run_every="1s")
def timer(deadline):
    remaining = max(0, math.ceil(deadline - time.time()))
    minutes, seconds = divmod(remaining, 60)
    st.markdown(f"**남은 시간 {minutes:02d}:{seconds:02d}**")
    if remaining == 0:
        st.rerun()


def mock_interview():
    st.header("모의면접")
    mock = profile["mock"]
    if not mock:
        st.write("기술 3문항과 행동 2문항을 15분 동안 연습합니다. 검토는 종료 후 열립니다.")
        if st.button("15분 모의면접 시작", type="primary"):
            start_mock()
        return
    if mock["status"] != "active":
        label = "시간 만료" if mock["status"] == "expired" else "연습 종료"
        st.success(label)
        for q in mock["questions"]:
            attempt_id = f'{mock["id"]}_{q["id"]}'
            entry = profile["attempts"].get(attempt_id)
            result = "응답" if entry else ("건너뜀" if q["id"] in mock["skipped"] else "미응답")
            with st.expander(f'{q["id"]} · {result} · {title_for(q)}'):
                if entry:
                    review(attempt_id, entry)
                else:
                    st.write(q["guide"])
                    st.write(q["follow"])
        if st.button("새 모의면접 시작"):
            start_mock()
        return

    index = mock["index"]
    question = mock["questions"][index]
    question_id = question["id"]
    st.progress((index + 1) / 5, text=f"문항 {index + 1} / 5")
    expired = time.time() >= mock["deadline"]
    if not expired:
        timer(mock["deadline"])
    show_question(question)
    st.caption("입력란 밖을 클릭하거나 Tab을 누르면 작성 내용이 저장됩니다.")
    saved = mock["answers"].get(question_id, [])
    answer = edit_answer(f'{mock["id"]}_{question_id}', question, saved)
    updated = copy.deepcopy(profile)
    active = updated["mock"]
    if saved or has_answer(answer):
        active["answers"][question_id] = answer
    if has_answer(answer) and question_id in active["skipped"]:
        active["skipped"].remove(question_id)
    if expired:
        finish_mock(updated, "expired")
        return
    prev, next_col, skip = st.columns(3)
    previous = prev.button("이전", disabled=index == 0)
    following = next_col.button("다음", disabled=index == 4)
    skipping = skip.button("건너뛰기", disabled=has_answer(answer) or question_id in active["skipped"])
    if st.button("종료하고 검토", type="primary"):
        finish_mock(updated, "completed")
    elif previous or following or skipping:
        active["index"] = index - 1 if previous else min(index + 1, 4)
        if skipping and question_id not in active["skipped"]:
            active["skipped"].append(question_id)
        if commit(updated):
            st.rerun()
    elif updated != profile and commit(updated):
        st.caption("초안 저장 완료")


def history():
    st.header("연습 기록")
    for question_id in sorted(profile["drafts"], key=lambda key: profile["drafts"][key]["updated"], reverse=True):
        if question_id in QUESTION:
            st.button(f"초안 이어서 풀기 · {question_id}", on_click=navigate, args=("질문은행", question_id))
    personal_attempts = profile.get("personal_attempts", {})
    mode = st.radio("기록 유형", ("전체", "표준형", "맞춤형"), horizontal=True)
    entries = []
    if mode != "맞춤형":
        entries.extend((key, "표준형", entry) for key, entry in profile["attempts"].items())
    if mode != "표준형":
        entries.extend((key, "맞춤형", entry) for key, entry in personal_attempts.items())
    if not entries:
        st.info("제출한 답변이 없습니다.")
    for attempt_id, kind, entry in sorted(entries, key=lambda item: item[2]["submitted"], reverse=True):
        q = entry["question"]
        when = datetime.fromtimestamp(entry["submitted"], timezone(timedelta(hours=9)))
        label = f'{q["id"]} · {title_for(q)}' if kind == "표준형" else f'문항 {entry["index"] + 1} · {q["kind"]}'
        with st.expander(f'{when:%m/%d %H:%M} KST · {kind} · {label}'):
            if kind == "맞춤형":
                render_feedback(entry)
            else:
                review(attempt_id, profile["attempts"][attempt_id])
                if q["id"] in QUESTION:
                    st.button("다시 풀기", key=f"retry_{attempt_id}", on_click=navigate,
                              args=("질문은행", q["id"]))
    if profile != empty_profile():
        confirmed = st.checkbox("경험 카드, 초안, 모의면접을 포함한 전체 기록 삭제에 동의합니다.")
        if st.button("전체 기록 삭제", disabled=not confirmed) and commit(empty_profile()):
            state.clear()
            st.rerun()


st.title("DCO 면접 연습")
st.caption("AWS 데이터센터 운영 직무 대비 · 자체 제작 연습 문항")
with st.sidebar:
    st.header("DCO 연습")
    st.radio("메뉴", PAGES, key="page")
    st.radio("질문 언어", ("한국어", "English"), key="language", horizontal=True)
    st.caption("현재 주소로 기록을 다시 열 수 있습니다. 이 주소를 공유하지 마세요.")
    st.caption("호스팅 저장소가 초기화되면 기존 기록이 사라질 수 있습니다.")
    st.markdown("[AWS DCO 직무](https://www.amazon.jobs/en/jobs/10597810/clearable-data-center-technician-adc-infraops-dco) · "
                "[Amazon 면접 안내](https://www.amazon.jobs/content/en/how-we-hire/interview-loop)")

{"홈": home, "질문은행": question_bank, "모의면접": mock_interview,
 "맞춤형": lambda: render_personal(profile, commit, state.language), "기록": history}[state.page]()




