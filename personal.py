import copy
import os
import time
import uuid

import streamlit as st

from coaching import CoachingError, DEFAULT_MODEL, generate_feedback, generate_questions

STAR = ("상황 (Situation)", "과제 (Task)", "행동 (Action)", "결과 (Result)")


def render_feedback(entry):
    st.text(entry["question"]["question"])
    labels = STAR if entry["question"]["kind"] == "행동" else ("답변",)
    for label, answer in zip(labels, entry["answer"]):
        st.markdown(f"**{label}**")
        st.text(answer or "미작성")
    for key, label in (("strength", "잘 설명한 부분"), ("gap", "보완할 부분"),
                       ("next_step", "다음 답변에 넣을 내용"), ("follow_up", "꼬리질문")):
        st.markdown(f"**{label}**")
        st.text(entry["feedback"][key])


def configuration(key):
    try:
        return st.secrets.get(key, os.environ.get(key, ""))
    except FileNotFoundError:
        return os.environ.get(key, "")


def render_personal(profile, commit, language):
    st.header("맞춤형 면접 연습")
    st.write("경험을 바탕으로 기술 3문항과 행동 2문항을 생성하고 답변별 피드백을 받습니다.")
    key = configuration("OPENAI_API_KEY")
    if not key:
        key = st.text_input("OpenAI API 키", type="password", key="personal_api_key",
                            help="현재 앱 세션에서만 사용합니다. 연습 기록에는 저장하지 않습니다.")
    if not key.strip():
        st.info("맞춤형을 시작하려면 OpenAI API 키가 필요합니다. 표준형은 키 없이 사용할 수 있습니다.")
    model = configuration("OPENAI_MODEL") or DEFAULT_MODEL
    personal = profile.get("personal", {})
    old_cards = personal.get("cards", [])
    with st.form("experience_cards"):
        st.subheader("경험 카드")
        st.caption("최대 3개. 담당 업무·도구, 본인 행동, 결과를 적어 주세요. 연락처나 내부 식별자는 빼 주세요.")
        cards = [st.text_area(f"경험 {i + 1}", value=old_cards[i] if i < len(old_cards) else "",
                              max_chars=1200, placeholder="사내 IT 지원 / 스위치 포트 변경 직후 장애 / 본인이 확인한 근거와 조치")
                 for i in range(3)]
        if st.form_submit_button("경험 카드 저장"):
            updated = copy.deepcopy(profile)
            updated.setdefault("personal", {})["cards"] = [card.strip() for card in cards]
            if commit(updated):
                st.rerun()

    cards = [card for card in old_cards if card]
    if cards:
        with st.expander("질문 생성 시 OpenAI에 전송할 내용"):
            st.text("\n\n".join(cards))
            st.caption(f"질문 언어 · {language}")
        if st.button("경험을 OpenAI에 보내 질문 5개 생성", disabled=not key.strip()):
            try:
                with st.spinner("맞춤 질문을 만드는 중입니다."):
                    questions = generate_questions(key.strip(), model, cards, language)
            except CoachingError as exc:
                st.error(str(exc))
            else:
                updated = copy.deepcopy(profile)
                updated["personal"]["set"] = {
                    "id": uuid.uuid4().hex,
                    "language": language,
                    "questions": [dict(q, experience=cards[q["card"] - 1] if q["card"] else "")
                                  for q in questions],
                    "drafts": {},
                }
                if commit(updated):
                    st.rerun()

    question_set = personal.get("set")
    if not question_set:
        return
    st.subheader("내 맞춤 질문")
    st.caption(f'질문 언어 · {question_set["language"]} · 새로 생성하면 현재 문항과 초안이 교체됩니다.')
    questions = question_set["questions"]
    index = st.selectbox("문항 선택", range(len(questions)), key=f'personal_set_{question_set["id"]}',
                         format_func=lambda i: f'{i + 1}. {questions[i]["kind"]} · {questions[i]["question"]}')
    question = questions[index]
    slot = str(index)
    st.caption("경험 기반" if question["experience"] else "가상 상황")
    st.text(question["question"])
    labels = STAR if question["kind"] == "행동" else ("답변",)
    saved = question_set["drafts"].get(slot, [])
    answer = [st.text_area(label, value=saved[i] if i < len(saved) else "",
                           key=f'personal_{question_set["id"]}_{slot}_{i}', max_chars=1500)
              for i, label in enumerate(labels)]
    has_answer = any(part.strip() for part in answer)
    if answer != saved and (saved or has_answer):
        updated = copy.deepcopy(profile)
        if has_answer:
            updated["personal"]["set"]["drafts"][slot] = answer
        else:
            updated["personal"]["set"]["drafts"].pop(slot, None)
        if commit(updated):
            profile = updated
            st.caption("초안 저장 완료")

    with st.expander("피드백 요청 시 OpenAI에 전송할 내용"):
        st.text(question["question"])
        st.text(question["experience"] or "연결된 경험 없음")
        for label, text in zip(labels, answer):
            st.text(f"{label} · {text}")
        st.caption("문항 유형과 기술 또는 STAR 검토 기준도 함께 전송합니다.")

    if st.button("답변을 OpenAI에 보내 피드백 받기", type="primary",
                 disabled=not (key.strip() and has_answer)):
        try:
            with st.spinner("답변을 검토하는 중입니다."):
                feedback = generate_feedback(key.strip(), model, question, question["experience"],
                                             dict(zip(labels, answer)))
        except CoachingError as exc:
            st.error(str(exc))
        else:
            updated = copy.deepcopy(profile)
            updated.setdefault("personal_attempts", {})[uuid.uuid4().hex] = {
                "question": question, "answer": answer, "feedback": feedback,
                "submitted": time.time(), "set_id": question_set["id"], "index": index,
            }
            if commit(updated):
                st.rerun()

    attempts = [entry for entry in profile.get("personal_attempts", {}).values()
                if entry["set_id"] == question_set["id"] and entry["index"] == index]
    if attempts:
        st.subheader("최근 피드백")
        render_feedback(max(attempts, key=lambda entry: entry["submitted"]))
