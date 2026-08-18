# BLACK YOMI ONI — каркас заказа рамы

**SKU:** **NX-YOMI-A** · **BLACK YOMI ONI**  
**Статус:** **не PO.** Открывать после посадки GATE (тепло/q/SATCOM).  
**Линия:** [BLACK YOMI](../../../00_docs/architecture/BLACK_YOMI.md)  
**Не:** GATE · TENGU · RAIJIN · X8 · 50×50 · боевой отсек · расходник

`expendable: false`. `weapon_bus: false`. Pixhawk 6C **не** в полётном контуре.

---

## 1. Лётные цифры

| Параметр | Значение |
|----------|----------|
| Мах (эшелон) | **2.0–2.2** на **16–18 км** |
| Потолок | ≥ 18 км рабочий |
| MTOW | **тонны** (завод в оферте; не 400 кг GATE) |
| Полезка заказчика | **150–300 кг** |
| Топливо | ТС-1 / Jet-A-1 |
| Тяга | ТРДД класса **АЛ-41** / производная, цех Су-35 |
| Посадка | полоса. Парашют — запас, не основной |
| Расходник | не принимаем |

---

## 2. Завод / мы

| Завод | NULLXES |
|-------|---------|
| Планер титан/композит, воздухозаборники, ТРДД, топливная, шасси, пожарка | Orin NX 16GB + dual-ready полка |
| Приводы, ICD CAN/PWM | IMX568 в обогреваемом обтекателе |
| Генератор 28 В, кВт-класс | tactical INS + multi-band GNSS |
| Антенные вырезы SATCOM | SATCOM-терминал; ELRS только пад |

---

## 3. Отсеки

- **A COMPUTE:** ≥ 40 л, 28 В, **≥ 400 Вт** cont / 800 Вт peak, жидкостный контур, виброопоры ТРДД.  
- **B NOSE:** M12 70–90° H, обогрев, ПВД Rosemount-класса / ADC под Мах 2.3.  
- **C NAV:** INS у ЦМ, 2× GNSS ≥ 800 мм разнос.  
- **D RF:** SATCOM верх, LOS backup. ELRS в люк шасси.  
- **E ENGINE:** перегородка, пожарка. Не в A.

ЦМ с 150–300 кг полезки — в оферте, не на лётных.

---

## 4. L0 и связь

- Полёт: **наш C++ L0**. 6C не подключён к поверхностям в воздухе.  
- Пад: ELRS. Воздух: SATCOM + направленный LOS.  
- Обрыв C2: снижение Маха → коридор → RTB. Не continue dash.  
- Обрыв Orin: L0 сам RTB/loiter.

---

## 5. Приёмка (когда станет PO)

1. GATE уже дал тепло/SATCOM на Мах 1.2.  
2. STEP отсеков + 28 В 400 Вт / 1 ч.  
3. Первый полёт до Mag 1.6. Мах 2.2 — отдельный пункт.

```yaml
order: NX-YOMI-A-AIRFRAME-1
sku: NX-YOMI-A
name: BLACK YOMI ONI
po_status: not_po_until_gate_landed
weapon_bus: false
munition: false
expendable: false
performance:
  dash_mach: [2.0, 2.2]
  dash_alt_m: [16000, 18000]
  payload_customer_kg: [150, 300]
  fuel: TS-1
  propulsion: turbofan_al41_class
  recovery: runway
l0:
  flight: customer_cpp
  pad_bench: pixhawk6c
  python_pwm: false
links:
  flight_c2: satcom_primary
  pad_rc: elrs_2g4
```
