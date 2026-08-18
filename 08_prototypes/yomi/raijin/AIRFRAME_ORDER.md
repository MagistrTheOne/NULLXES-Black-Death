# BLACK YOMI RAIJIN — каркас заказа рамы

**SKU:** **NX-YOMI-C** · **BLACK YOMI RAIJIN**  
**Статус:** **не в том же PO**, что GATE/ONI/TENGU. Смежный НИР (скрам / ТЗП).  
**Линия:** [BLACK YOMI](../../../00_docs/architecture/BLACK_YOMI.md)  
**Не:** расходник · боевой отсек · «дописать YAML к GATE»

`expendable: false`. `weapon_bus: false`. Выше 35 км без носителя не заказываем.

---

## 1. Лётные цифры

| Параметр | Значение |
|----------|----------|
| Мах | **5–7** |
| Высота | **30–35 км** |
| Разгон | ТРД + прямоток/скрам **или** внешняя ступень (завод в оферте НИР) |
| Фюзеляж | цех Су |
| ТЗП носа/кромок | смежный подряд, паспорт нагрева |
| Полезка мозга | Orin **только тёплый отсек**, не под обшивкой |
| Посадка | сброс Маха → полоса или парашют. Не удар в точку |

---

## 2. Отсеки (жёстко для мозга)

- **A COMPUTE:** гермо + жидкость, 28 В, тепловой контур независимо от ТЗП носа.  
- **B NOSE:** ТЗП ≠ окно камеры на Мах 7. EO может быть боковой/закрываемой. Контракт зрения — по-прежнему метры, не 50 км.  
- **C NAV:** INS; GNSS на разгоне может пропасть — L0 не требует непрерывного фикса.  
- **D RF:** разгон — запас канала (blackout). SATCOM после снижения Маха. ELRS только земля.

---

## 3. L0

Наш C++. 6C нет в контуре. Python не PWM.  
Обрыв C2 на разгоне: заранее прописанный коридор снижения, не «продолжай Мах 6».

---

## 4. Приёмка (когда станет отдельный PO)

1. TENGU дал высоту/жару Мах 3.  
2. ТЗП и скрам — отдельные акты, не строка в заказе GATE.  
3. Первый вылет не гиперзвук.

```yaml
order: NX-YOMI-C-AIRFRAME-1
sku: NX-YOMI-C
name: BLACK YOMI RAIJIN
po_status: separate_nir_not_same_po
weapon_bus: false
munition: false
expendable: false
performance:
  dash_mach: [5, 7]
  dash_alt_m: [30000, 35000]
  propulsion: turbojet_plus_scram_or_booster
  recovery: [runway_after_slow, chute_after_slow]
l0:
  flight: customer_cpp
  python_pwm: false
  failsafe_c2_loss: prebriefed_slowdown_corridor
links:
  boost_c2: degraded_ok
  cruise_c2: satcom_after_slow
  pad_rc: elrs_2g4
```
