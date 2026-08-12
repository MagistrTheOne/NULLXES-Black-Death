# VOICE_PERSONA — NULLXES GSC announcer

**Status:** Canon · 2026-08-13  
**Host:** GSC only (`companion_load: false`)  
**Not:** L0 · GuidanceIntent · fire-control · CERBER · cloud TTS · Qwen

CIVIL орёт как инспектор. DEFENSE врубает sting и орёт матом RU+EN. Это операторский рот, не контур управления.

```text
SceneAlert / WorldObject / TerritorialTrack / Envelope
                         │
                         ▼
                   VoiceDirector   (pack.yaml, variants)
                         │
                         ▼
              /bd/gsc/voice_cue
                         │
         TtsEngine: NULLXES ONNX (STABLE) → else SAPI
                         │
              VoicePlayer + defense_sting     NULLXES_VOICE=1
```

## TTS: что берём

| Вариант | Вердикт |
|---------|---------|
| Cloud API (ElevenLabs / Azure / OpenAI) | **Нет.** Утечка миссии, лаг, чужой рот, не NULLXES |
| Qwen / Llama / GPT TTS | **Нет.** Product lock. Не наш корпус, не наш sha |
| **NULLXES ONNX TTS** (`nullxes_tts_v1`, VITS/Piper corpse) | **Да.** GSC local. Train+export+sha. Пока CANDIDATE → SAPI fallback |

SAPI — костыль, чтобы рот жил сегодня. Цель — свой голос в `models/gsc/voice/nullxes_tts_v1/`.

## CIVIL (маты инспектора)

| kind | линия |
|------|--------|
| boot | `CIVIL. Ало, я на смене. Кожаные мешки, не беситесь.` |
| human | `О, кожаные мешки.` / `Ало, люди, я вас вижу, блядь.` |
| power_line | `Ало блядь, я тут дефект нашла.` |
| uav | `Неизвестный объект. Борт в кадре.` |

Варианты: `crc32(envelope:kind:object_id) % n`. Cooldown 12 с.

## DEFENSE (маты RU+EN)

На **switch**: sting + `Ну вот, теперь вам пизда. You're fucked.`

Дальше TTS по классам / territorial `unknown`. `friend` молчит. Кинетики нет.

## Вкл

```text
NULLXES_VOICE=1 python 06_autonomy/ros2/nodes/voice_soft.py
```

Без флага — только cue (CI/bench).

## Код

`06_autonomy/gsc/voice/` · `tts_runtime.py` · `models/gsc/voice/nullxes_tts_v1/` · `ros2/nodes/voice_soft.py`
