# 49 Ledbury — Maison (guest)

App for **49 Ledbury Road** (Notting Hill). Personal link from the welcome message: **arrival day** → end of departure day.

Open on your phone. iPhone: Share → **Add to Home Screen**.

Too early: **Available from \<date\>.**

---

## Tabs

| Tab | Role |
| --- | --- |
| **Home** | Welcome, London weather, alarm status |
| **Heating** | Heating by room (no cooling) |
| **Lights** | Lights & scenes |
| **Access** | Locks, shutters / gate, alarm, doorbell |
| **Sound** | Audio zones (if available) |
| **TV** | Apple TV remote (if available) |
| **Info** | Wi‑Fi voucher, QR / share link |

---

## Wi‑Fi

Join the guest network → enter the **voucher** on the **captive portal**. Codes also under **Info**.

---

## Home / Heating / Lights

- **Home** — greeting, weather, alarm status only.
- **Heating** — Adjust (±, on/off) or Overview; tap a room for the dial.
- **Lights** — by room; lamp = on/off; swipe to dim; scenes if present.

---

## Access

Locks Open/Close; gate / shutters Open/Close/Stop; alarm Arm/Disarm (confirm). Doorbell popup may show camera + **Open the gate**.

---

## TV

Pick a TV → power, pad, Menu/Home, volume. One Apple TV per screen (no source picker). AirPlay from the phone to an Apple TV works on guest Wi‑Fi when the network allows it.

---

## Info

Wi‑Fi network + voucher, QR to share the app with your party.

---

## Notes

- Link closes after departure; Wi‑Fi may last one more day.
- Wall tablet URL (`/house/…`) is for the house LAN only.

PDF: [ledbury-manual/49-Ledbury-Guest-User-Manual.pdf](ledbury-manual/49-Ledbury-Guest-User-Manual.pdf).

### Host setup (short)

1. Pulse-Eight + Apple TVs in HA; Usvegliu **Options** → up to 4 TVs (name, ATV, Neo out/in).  
2. ATV `media_player` in tenant entities.  
3. AirPlay guest: [ledbury-airplay-vlan15.md](ledbury-airplay-vlan15.md).

### Later

- Doorbell Web Push (background) — not yet.
