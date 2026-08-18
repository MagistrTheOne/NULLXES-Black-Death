# YOMI — дельта стека (что остаётся / что меняется)

**Canon:** [BLACK_YOMI.md](BLACK_YOMI.md) · дерево: `08_prototypes/yomi/`  
**Отец:** BLACK DEATH / Judgment / X8 Flight-1 — параллельный путь, не этот документ.

Мозг не переписываем. Меняется тело, энергия, L0-путь в воздухе, радио.

```
cam → CERBER → POSEIDON → DMI → Guidance → L0
```

На X8 L0 в воздухе = Pixhawk 6C + `ArduPlaneAdapter`.  
На YOMI L0 в воздухе = **наш C++**. 6C = пад (GATE) или отсутствует в контуре (ONI+).

---

## Остаётся (все SKU)

| Слой | Статус |
|------|--------|
| CERBER ONNX, нет LLM в `perception/` | без изменений |
| POSEIDON facts only | без изменений |
| DMI exclusive TaskOffer; GOTO / LOITER / RTB / EXPLORE_SECTOR | без изменений |
| ATLAS GSC only, `companion_load: false` | без изменений |
| ADR-008 CIVIL boot / DEFENSE `operator_ack` | без изменений; DEFENSE официален |
| Python не PWM | без изменений |
| L0 swarm-blind; нет `/bd/weapon` | без изменений |
| NEVER_ACTIONS (WEAPON / JAM / SPOOF / FIRE_CONTROL / GUIDANCE_INTENT) | YAML не включает |
| `expendable: false` | сажаем |
| X8 Flight-1 BOM | не трогать |

---

## Меняется (тело, не мозг)

| | GATE NX-YOMI-0 | ONI NX-YOMI-A | TENGU NX-YOMI-B | RAIJIN NX-YOMI-C |
|--|----------------|---------------|-----------------|------------------|
| Тело | ТРД, ≤400 кг | цех Су, тонны, АЛ-41-класс | Мах 3, 22–26 км | скрам/ТЗП, 30–35 км |
| L0 в полёте | native C++ + 6C только пад | native C++, 6C не в контуре | то же | то же + blackout радио |
| Энергия | 28 В ген, банки буфер | то же, масштаб кВт | то же + тепло отсека | тёплый отсек Orin обязателен |
| C2 | SATCOM + ELRS земля | SATCOM | SATCOM высотный | разгон: запас канала |
| Зрение | IMX568, метры | тот же контракт | нагрев обтекателя | ТЗП носа ≠ дальность камеры |
| PO | lock | не пока GATE не сел | не пока ONI не сел | отдельный НИР |

Камера на любом Махе — метры / десятки метров. 30–50 км = GSC COP, не EO.

`02_aerodynamics/` / `03_structure/` отца (BWB AR=1.25) под YOMI не клонируем. Геометрию считает завод.

---

## Заказы

| SKU | Файл |
|-----|------|
| GATE | [08_prototypes/yomi/gate/AIRFRAME_ORDER.md](../../08_prototypes/yomi/gate/AIRFRAME_ORDER.md) |
| ONI | [08_prototypes/yomi/oni/AIRFRAME_ORDER.md](../../08_prototypes/yomi/oni/AIRFRAME_ORDER.md) |
| TENGU | [08_prototypes/yomi/tengu/AIRFRAME_ORDER.md](../../08_prototypes/yomi/tengu/AIRFRAME_ORDER.md) |
| RAIJIN | [08_prototypes/yomi/raijin/AIRFRAME_ORDER.md](../../08_prototypes/yomi/raijin/AIRFRAME_ORDER.md) |
