# Dialogue Assets

`Dialogue Scene UI`에서 사용하는 portrait/background asset 폴더이다.

## 구조

```text
assets/dialogue/
├─ common/
│  └─ player/
├─ fairy/
│  ├─ companion/
│  └─ npc/
├─ mystery/
│  ├─ companion/
│  └─ npc/
├─ martial/
│  ├─ companion/
│  └─ npc/
├─ sf/
│  ├─ companion/
│  └─ npc/
├─ fantasy/
│  ├─ companion/
│  └─ npc/
└─ backgrounds/
   ├─ fairy/
   ├─ mystery/
   ├─ martial/
   ├─ sf/
   └─ fantasy/
```

## Portrait 파일명

`character_id`를 파일명 stem으로 사용한다.

예시:

```text
assets/dialogue/fairy/companion/lulu.png
assets/dialogue/mystery/npc/archive_keeper.webp
assets/dialogue/common/player/player.png
```

지원 확장자:

- `.png`
- `.webp`
- `.jpg`
- `.jpeg`

해당 캐릭터 파일이 없으면 같은 폴더의 `default.*`를 찾고,
그것도 없으면 `Dialogue Scene UI`의 placeholder fallback을 사용한다.

미스터리 동료는 플레이 액션에 맞는 선택적 pose를 제공한다.

- `investigate.png`: 사건 기록 및 단서 확인
- `explain.png`: 핵심 개념 설명 및 정답 피드백
- `thinking.png`: 판단 도움 및 오답 피드백
- `notebook.png`: 단서 정리 및 학습 노트 삽화

다른 테마에는 이 pose 계약을 강제하지 않으며 기존 `default.*`를 사용한다.

## Background 파일명

`scene_id`를 파일명 stem으로 사용한다.

예시:

```text
assets/dialogue/backgrounds/sf/control_room.png
assets/dialogue/backgrounds/mystery/archive_room.webp
```

해당 scene 파일이 없으면 같은 테마 폴더의 `default.*`를 찾고,
그것도 없으면 기존 테마 CSS 배경을 사용한다.

## 역할 규칙

- `companion`: 테마별 `companion/`
- `npc`: 테마별 `npc/`
- `player`: `common/player/`
- `narrator`: portrait 없음

## 테마 slug

- 동화 → `fairy`
- 미스터리 / 미스테리 → `mystery`
- 무협 → `martial`
- SF → `sf`
- 판타지 → `fantasy`
