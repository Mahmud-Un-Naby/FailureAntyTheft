# FailureAntyTheft — presentation content

Target duration: **8–10 minutes**  
Slide count: **12**  
Institution: **Mawlana Bhashani Science and Technology University**  
Department: **Computer Science and Engineering**

> Before presenting, replace `[Presenter Name]` and `[Student ID]` on the cover.

## 1. Cover

**FailureAntyTheft**  
A phone-based IoT movement detection and anti-theft alert system

## 2. Why build this system?

- Portable assets such as bags, drawers and laboratory equipment can be moved
  while unattended.
- Raw sensor noise must not create false alarms.
- Smartphones already contain accelerometers, Wi-Fi and batteries.
- A local classroom prototype should not depend on paid cloud services.

## 3. Solution overview

1. **Sense:** Phyphox exposes phone acceleration and device time.
2. **Decide:** the server calibrates, filters noise and verifies sustained
   movement.
3. **Respond:** the dashboard updates, saves the event and sounds a siren.

## 4. Architecture

Phone/Phyphox → HTTP collector → MQTT/Mosquitto → per-device runtime and pure
detector → SQLite + FastAPI/WebSocket → dashboard and siren.

## 5. Sensor-to-alert flow

Sample → collect/deduplicate → normalize → calculate motion score → require
three crossings inside 0.5 seconds → persist and publish the alarm.

## 6. Detection logic

Offline → Disarmed → Calibrating → Armed → Suspicious → Alarm. The default
calibration uses a 5-second placement delay and 2-second sample window. Motion
score is the absolute difference between the smoothed acceleration magnitude
and the median baseline.

## 7. Dashboard

Show health metrics, device cards, live motion chart, alarm/sound workflow and
event history.

## 8. Technology stack

Phyphox, Python, FastAPI, asyncio, MQTT, Mosquitto, SQLite, WebSocket,
HTML/CSS/JavaScript, Web Audio, Pytest, Ruff, mypy and Docker Compose.

## 9. Evidence

- 105 passing automated tests; one environment-gated live MQTT test.
- 84% coverage at final software handoff; detector coverage 94%.
- Real phone `/config` returned HTTP 200 and `measuring: true`.
- Verified live buffers: `acc_time`, `accX`, `accY`, `accZ`.
- Dashboard reported the live phone as online/disarmed after the compatibility
  correction.

## 10. Live demo

Start Phyphox → connect phone → verify online → enable/test sound → arm and wait
seven seconds → move phone → observe alarm → acknowledge and show history.

## 11. Limitations and roadmap

Current scope: trusted private LAN, browser alarm endpoint, built-in Phyphox
profile, prototype rather than certified security. Next: automatic buffer
discovery, authentication/TLS, mobile/PWA push, multi-sensor correlation and
packaged deployment.

## 12. Conclusion

FailureAntyTheft demonstrates a complete local IoT loop using hardware people
already own: sense, communicate, decide, store, visualize and act.
