# FailureAntyTheft speaker notes

## Slide 1 — Cover (30 seconds)

Introduce the project as a local IoT anti-theft system that converts ordinary
smartphones into motion sensors. State that no dedicated sensor hardware or paid
cloud service is required.

## Slide 2 — Problem (45 seconds)

Portable assets are difficult to monitor cheaply. Phones already contain the
right sensors, but simply reading acceleration is not enough because noise and
minor vibrations can create false alerts. The project therefore focuses on a
reliable detection and response workflow.

## Slide 3 — Solution (45 seconds)

Explain the complete IoT cycle: Phyphox senses, the server decides, and the
dashboard responds. Everything remains on the local network.

## Slide 4 — Architecture (70 seconds)

Walk from left to right. The collector polls Phyphox, validates private URLs,
deduplicates samples and publishes typed telemetry. MQTT decouples the logical
components. Each device has an ordered runtime and pure detector. SQLite stores
configuration, state and events. FastAPI and WebSocket serve the dashboard and
accept commands.

## Slide 5 — Data flow (50 seconds)

Emphasize that one noisy sample does not trigger an alarm. Device sample time is
used for the sustained-movement window, so buffered HTTP delivery does not alter
the detector's decision.

## Slide 6 — Detection logic (75 seconds)

After arming, the system allows five seconds for placement and then collects a
stable baseline for two seconds. Acceleration magnitude is smoothed with an EMA.
The motion score is the difference from the baseline. Three threshold crossings
inside 0.5 seconds trigger the alarm. Acknowledgement disarms the device.

## Slide 7 — Dashboard (45 seconds)

Point out the at-a-glance metrics, device cards, independent controls, live
motion chart, audible alarm control and persistent history. The screenshot is
from the implemented application.

## Slide 8 — Technology stack (45 seconds)

Briefly connect each technology to its responsibility. Stress that the stack is
reproducible, local-first and deliberately avoids unnecessary infrastructure.

## Slide 9 — Evidence (60 seconds)

Separate automated evidence from physical evidence. The suite passes 105 tests.
Recorded stationary and movement samples protect the detector logic. A real
phone returned the expected Phyphox buffers and became online in the dashboard.

## Slide 10 — Demonstration (30 seconds before demo)

Describe the steps, then perform them. Wait the complete seven seconds after
arming. If venue Wi-Fi isolates devices, switch to a private hotspot. Keep the
dashboard screenshot available as a fallback.

## Slide 11 — Limitations and roadmap (45 seconds)

Be transparent that this is a trusted-LAN classroom prototype, not a certified
security system. The next priorities are automatic Phyphox discovery,
authentication/TLS, background mobile notifications and multi-sensor
correlation.

## Slide 12 — Conclusion (30 seconds)

Summarize the complete IoT loop and the value of reusing existing hardware.
Thank the audience and invite questions.

Estimated total without live demo: **8–9 minutes**.
