import streamlit as st

from components.theme_system import (
    get_theme_pack,
)
from repositories.attempt_repository import (
    get_concept_stats,
)
from repositories.chapter_repository import (
    get_chapter,
)
from services.mastery_service import (
    get_mastery_summary,
)
from services.personalization_service import (
    get_latest_chapter_personalization_profile,
)


def _render_concept_list(
    title: str,
    concepts: list[str],
    empty_text: str,
) -> None:
    st.markdown(
        f"**{title}**"
    )

    if concepts:
        st.write(
            ", ".join(
                concepts
            )
        )
    else:
        st.caption(
            empty_text
        )


def render_record_tab(
    user,
    world,
):
    pack = get_theme_pack(
        world[4]
    )

    st.subheader(
        pack["report_name"]
    )

    mastery = get_mastery_summary(
        user_id=user["user_id"],
        world_id=world[0],
    )

    with st.expander(
        "Concept Mastery",
        expanded=False,
    ):
        if not mastery["items"]:
            st.info(
                "새 Mastery Engine으로 저장된 기록이 아직 없습니다. "
                "기존 정답률 기록은 아래 상세 기록에서 확인할 수 있습니다."
            )
        else:
            if mastery[
                "average"
            ] is not None:
                st.metric(
                    "평균 Mastery",
                    f"{mastery['average'] * 100:.0f}%",
                )

            for item in (
                mastery["items"]
            ):
                score = (
                    item[
                        "mastery_score"
                    ]
                )

                st.markdown(
                    f"**{item['concept']}** · "
                    f"Mastery {score * 100:.0f}%"
                )
                st.progress(
                    float(score)
                )
                st.caption(
                    f"{item['correct_count']} / "
                    f"{item['attempts']} 정답"
                    + (
                        " · 복습 권장"
                        if item[
                            "review_needed"
                        ]
                        else ""
                    )
                )

    current_chapter_number = (
        world[7]
    )

    chapter = get_chapter(
        world_id=world[0],
        chapter_number=(
            current_chapter_number
        ),
    )

    with st.expander(
        "최근 Chapter 분석",
        expanded=False,
    ):
        if chapter:
            profile = (
                get_latest_chapter_personalization_profile(
                    user_id=user[
                        "user_id"
                    ],
                    world_id=world[0],
                    chapter_id=chapter[0],
                )
            )

            recent = profile[
                "recent"
            ]

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:
                _render_concept_list(
                    "취약",
                    recent["weak"],
                    "현재 취약 개념 없음",
                )

            with col2:
                _render_concept_list(
                    "복습 필요",
                    recent["review"],
                    "현재 복습 필요 개념 없음",
                )

            with col3:
                _render_concept_list(
                    "강점",
                    recent["strong"],
                    "현재 강점 개념 없음",
                )

            st.caption(
                "최근 결과는 다음 Story Block의 학습 난이도와 "
                "취약 Concept 재노출에 우선 반영됩니다."
            )
        else:
            st.info(
                "현재 Chapter 정보를 찾을 수 없습니다."
            )

    with st.expander(
        "전체 누적 학습 분석",
        expanded=False,
    ):
        if chapter:
            profile = (
                get_latest_chapter_personalization_profile(
                    user_id=user[
                        "user_id"
                    ],
                    world_id=world[0],
                    chapter_id=chapter[0],
                )
            )

            global_profile = (
                profile[
                    "global"
                ]
            )

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:
                _render_concept_list(
                    "누적 취약",
                    global_profile[
                        "weak"
                    ],
                    "누적 취약 개념 없음",
                )

            with col2:
                _render_concept_list(
                    "누적 복습 필요",
                    global_profile[
                        "review"
                    ],
                    "누적 복습 필요 개념 없음",
                )

            with col3:
                _render_concept_list(
                    "누적 강점",
                    global_profile[
                        "strong"
                    ],
                    "누적 강점 개념 없음",
                )

    with st.expander(
        "개념별 상세 기록",
        expanded=False,
    ):
        concept_stats = (
            get_concept_stats(
                user_id=user[
                    "user_id"
                ],
                world_id=world[0],
            )
        )

        if not concept_stats:
            st.info(
                "아직 저장된 학습 기록이 없습니다."
            )
            return

        for item in (
            concept_stats
        ):
            accuracy_percent = round(
                item["accuracy"]
                * 100,
                1,
            )

            st.markdown(
                f"**{item['concept']}**  \n"
                f"{item['correct_count']} / "
                f"{item['attempts']} 정답 · "
                f"정답률 {accuracy_percent}%"
            )
