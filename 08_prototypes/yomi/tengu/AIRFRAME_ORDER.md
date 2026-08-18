# BLACK YOMI TENGU — каркас заказа рамы

**SKU:** **NX-YOMI-B** · **BLACK YOMI TENGU**  
**Статус:** **не PO.** Открывать после посадки ONI.  
**Линия:** [BLACK YOMI](../../../00_docs/architecture/BLACK_YOMI.md)  
**Не:** GATE · ONI как тот же PO · RAIJIN · расходник · боевой отсек

`expendable: false`. `weapon_bus: false`. Крейсер на высоте, не гонка у земли.

---

## 1. Лётные цифры

| Параметр | Значение |
|----------|----------|
| Мах | **2.8–3.2** |
| Высота крейсера | **22–26 км** |
| Тяга | цех Су + двигатель под Мах 3 |
| Полезка | ≥ 150 кг (как ONI, плюс теплозащита носа) |
| Топливо | ТС-1 |
| Посадка | полоса после сброса Маха |
| Расходник | не принимаем |

---

## 2. Что добавляется к ONI

- Воздухозаборники и кромки под жару Мах 3.  
- Обтекатель EO: нагрев + материал, не «то же стекло GATE».  
- INS tactical+ у ЦМ.  
- ПВД / ADC под Мах 3.3.  
- Отсек A: −55 °C снаружи, контур Orin обязателен.  
- C2: SATCOM высотный; LOS как запас на снижении.

---

## 3. L0

Наш C++. 6C не в контуре. Python не PWM. Обрыв C2 → снижение → RTB. Не continue на Мах 3.

---

## 4. Приёмка (когда станет PO)

1. ONI сел, есть нагрев/q на Мах 2.2.  
2. Паспорт кромок и обтекателя на Мах 3 / 24 км.  
3. Первый полёт не сразу 3.2.

```yaml
order: NX-YOMI-B-AIRFRAME-1
sku: NX-YOMI-B
name: BLACK YOMI TENGU
po_status: not_po_until_oni_landed
weapon_bus: false
munition: false
expendable: false
performance:
  dash_mach: [2.8, 3.2]
  dash_alt_m: [22000, 26000]
  fuel: TS-1
  propulsion: mach3_plant_su
  recovery: runway
l0:
  flight: customer_cpp
  python_pwm: false
links:
  flight_c2: satcom_high_alt
  pad_rc: elrs_2g4
```
