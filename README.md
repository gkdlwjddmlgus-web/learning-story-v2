# 원인과 수정

새 계정에서도 정답일 때만 `<div>`가 노출되어 DB/Mock 데이터 문제가 아님을 확인했다.

현재 `_render_learning_note()`는 raw HTML 안에 중첩 `<div>`를 사용한다.
정답일 때는 `correct_answer=None`이라 answer block이 비어 있고, 오답일 때는 answer `<div>`가 하나 추가된다.
Streamlit Markdown parser가 이 두 HTML 구조를 다르게 해석하면서 정답 분기에서 explanation wrapper가 문자로 노출되는 것으로 판단했다.

수정은 nested `<div>`를 없애고 내부 콘텐츠를 `display:block` span으로 통일한다.
