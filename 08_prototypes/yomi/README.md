# 08_prototypes/yomi — BLACK YOMI

**Canon:** [BLACK_YOMI.md](../../00_docs/architecture/BLACK_YOMI.md) · [YOMI_STACK_DELTA.md](../../00_docs/architecture/YOMI_STACK_DELTA.md)  
**Отец:** BLACK DEATH (infra). Это **не** Beta 50×50 и **не** X8 practice.

| Папка | SKU | Статус заказа |
|-------|-----|----------------|
| [gate/](gate/README.md) | NX-YOMI-0 GATE | **PO lock** — [AIRFRAME_ORDER.md](gate/AIRFRAME_ORDER.md) |
| [oni/](oni/README.md) | NX-YOMI-A ONI | не PO, пока GATE не сел |
| [tengu/](tengu/README.md) | NX-YOMI-B TENGU | не PO, пока ONI не сел |
| [raijin/](raijin/README.md) | NX-YOMI-C RAIJIN | не в том же PO |

Порядок: GATE → тепло/q/SATCOM → ONI → TENGU. RAIJIN — отдельный НИР.

`expendable: false`. `weapon_bus: false`. Нет `/bd/weapon`. Practice X8 живёт в `practice_airframes/`.
