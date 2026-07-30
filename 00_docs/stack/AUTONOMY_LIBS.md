# Минимальный набор библиотек — автономный ИИ (Python 3.11)

Только onboard / offline. Без облачных API.

## Runtime (полёт / HIL)

| Пакет | Версия-ориентир | Назначение |
|-------|-----------------|------------|
| `numpy` | ≥1.26 | численные массивы |
| `scipy` | ≥1.11 | фильтры, оптимизация, интерполяция |
| `opencv-python-headless` | 4.x | CV pipeline |
| `onnxruntime` | ≥1.17 | **основной** inference |
| `ultralytics` | YOLOv8/v10/v11 | **только offline** export; в полёте — чистый ONNX (`infer_yolo.py`) |
| `filterpy` | ≥1.4 | EKF/UKF baseline |
| `PyYAML` | ≥6.0 | конфиги |
| `msgpack` / `protobuf` | — | компактная сериализация state (выбор один) |

Опционально по железу:

| Пакет | Когда |
|-------|-------|
| `onnxruntime-gpu` | NVIDIA CUDA |
| TensorRT (через ORT-EP / native) | NVIDIA, production latency |
| OpenVINO | Intel VPU/CPU ускорение |

ROS 2 Python-клиенты (`rclpy` и msg-пакеты) — из дистрибутива ROS 2, не из PyPI как primary.

## Training / offline only (не в полётном образе)

| Пакет | Назначение |
|-------|------------|
| `torch` 2.x | обучение и экспорт ONNX |
| `ultralytics` | train/export YOLO |
| `onnx` | проверка/упрощение графов |

## Perception extras (где применимо)

| Компонент | Назначение |
|-----------|------------|
| OpenVINS | VIO |
| ORB-SLAM3 | визуальный SLAM |

Интегрируются как отдельные процессы/ноды; Python-обёртки минимальны.

## Явно исключено

`openai`, `anthropic`, `google-generativeai`, любой HTTP-клиент к LLM/cloud inference в runtime-зависимостях полёта.

Источник истины по пинам: `06_autonomy/requirements-autonomy.txt`.
