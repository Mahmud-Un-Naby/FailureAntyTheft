# Presentation-day demo checklist

## Before leaving

- Charge the laptop and phone.
- Install/open Phyphox and select **Acceleration with g**.
- Bring a charger and, ideally, a second hotspot-capable phone.
- Copy the `.pptx` to both local storage and a USB/cloud backup.
- Replace the cover-page presenter placeholder.

## Ten minutes before presenting

1. Connect the laptop and sensor phone to the same private Wi-Fi or hotspot.
2. Start Mosquitto with `docker compose up -d mosquitto`.
3. Start FailureAntyTheft with `.venv/bin/failureantytheft`.
4. Open `http://localhost:8000` in Chrome.
5. In Phyphox, enable remote access and press Play.
6. Update the registered URL if the phone's IP address changed.
7. Confirm the dashboard state is **Disarmed**, not **Offline**.
8. Click **Sound off** and confirm the test siren is audible.
9. Arm, wait seven seconds, move the phone and acknowledge the alarm.
10. Return the device to Disarmed before the actual presentation.

## Fallback

- If institutional Wi-Fi isolates devices, use a private hotspot.
- If the live network still fails, show the dashboard screenshot on slide 7 and
  explain the recorded live-phone validation on slide 9.
