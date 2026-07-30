# TEST PLAN — SonicModell AR Wing Pro (~2026-09)

**Platform:** SonicModell AR Wing Pro (practice flying wing)  
**Prerequisite:** edu bench gates from `TEST_PLAN_EDU_AUG.md` passed  
**Note:** Not Alpha 5×5. Geometry/propulsion differ; autonomy contracts must match.

## Airframe / propulsion

- [ ] CG and control surface direction verified
- [ ] Motor/ESC direction and failsafe documented
- [ ] Range check / link loss behaviour on RC known before autonomy loop

## Autonomy on wing

- [ ] Real IMU → L0 hold on ground (props restrained or removed per safety SOP)
- [ ] GNSS fix when available → nav EKF update (no fake fix in software)
- [ ] DMI: host coordinator assigns explore/loiter intent; agent ACCEPT → goal → guidance
- [ ] FM modes: force LIMITED peer / low SOC path on ground if telemetry real

## Optional two-kit DMI

- [ ] Second agent (edu or second wing kit): exclusive TaskOffer — only one ACCEPT
- [ ] WorldFact from agent A visible in Shared World Cache on host within TTL

## Flight (civil range only)

- [ ] CTOL practice under pilot override authority
- [ ] Autonomy loop engaged only inside agreed envelope
- [ ] Abort: pilot / RC priority over DMI intent at all times on practice frames

## Exit criteria for stage 2

Bus + L0 + DMI intent bridge proven on AR Wing Pro ground/taxi or short hop per local rules; lessons recorded as facts only.
