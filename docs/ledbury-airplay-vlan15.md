# Ledbury — AirPlay from guest VLAN 15 to device on VLAN 1

Goal: a phone on the **guest Wi‑Fi (VLAN 15)** can discover and stream AirPlay to a device on **VLAN 1** (Apple TV / AirPlay endpoint).

Stack assumed: **UniFi UDM** = router / firewall / mDNS; **Cambium** = guest SSID (EasyPass) tagged VLAN 15.

---

## 0. Prep

1. Note the AirPlay device on VLAN 1:
   - Name (e.g. `Living Room`)
   - **MAC** and **IP** (DHCP reservation on UDM recommended)
2. Confirm:
   - Guest SSID → VLAN **15**
   - AirPlay device → VLAN **1** (corporate / LAN)
3. From a laptop on VLAN 1, confirm AirPlay already works locally (Control Center sees the device).

---

## 1. UniFi UDM — DHCP reservation (VLAN 1)

1. UniFi Network → **Client Devices** → select the Apple TV / AirPlay box.
2. Settings → enable **Fixed IP** on the LAN (VLAN 1) network.
3. Keep that IP for firewall rules (example below: `192.168.1.50` — replace with yours).

---

## 2. UniFi UDM — mDNS / Bonjour between VLANs

AirPlay discovery uses multicast DNS. It must be forwarded **15 ↔ 1**.

### UniFi Network 8 / UniFi OS (typical path)

1. **Settings** → **Routing** → **mDNS**  
   (or **Settings** → **Networks** → global / advanced multicast, depending on controller version)
2. Enable **mDNS** / **mDNS Reflector** / **Bonjour forwarding**.
3. Ensure both networks are included:
   - Guest / VLAN 15
   - LAN / VLAN 1
4. Apply / provision.

If your UI only has a global toggle: turn it **on** (UDM reflects between corporate networks; verify guest is not excluded).

### Check

After rules below: phone on guest should list the AirPlay target.  
If firewall is open but the name never appears → mDNS still blocked.

---

## 3. UniFi UDM — firewall (the important part)

mDNS alone is not enough. The phone must send **unicast** audio/control to the AirPlay device.

### 3.1 Create an allow rule (guest → AirPlay host)

**Settings** → **Security** → **Traffic Rules** / **Firewall** (name varies by UniFi OS):

Create a rule, high priority, **before** any “drop guest to LAN”:

| Field | Value |
| --- | --- |
| Action | **Accept** |
| Source | Guest network / VLAN 15 (or guest RFC1918 zone) |
| Destination | AirPlay device IP (or a firewall group with that IP) |
| Port / protocol | Prefer **Any** TCP+UDP to that host for a first test |
| Direction | LAN in / inter-VLAN (guest → LAN) |

Name example: `Allow Guest AirPlay to Living ATV`.

### 3.2 Keep the rest of VLAN 1 closed

Leave (or add) the usual:

- Guest **cannot** reach the rest of VLAN 1 (HA, NAS, PCs, cameras…).
- Guest **can** reach WAN (internet) as today for the captive portal / browsing.
- Only the AirPlay IP(s) are exceptions.

### 3.3 Optional harden (after it works)

Instead of “Any” to the host, you can try tightening later. AirPlay uses several ports (commonly including **TCP 7000**, plus others that change by OS). Many sites keep **host allow Any** for reliability.

### 3.4 Client isolation on UniFi

If the guest SSID were on UniFi APs: disable **Client Device Isolation** for that SSID, or AirPlay/peer traffic can still break.  
At Ledbury the guest SSID is on **Cambium** → see §4.

---

## 4. Cambium — guest SSID (VLAN 15)

Gateway/firewall stays on the **UDM**. Cambium mainly tags Wi‑Fi onto VLAN 15.

In **cnMaestro** (or AP local UI):

1. Open the **guest WLAN** / EasyPass SSID.
2. **VLAN** = **15** (untagged on AP BSS, tagged on uplink trunk to the LAN/UDM).
3. **Client isolation** / **Station isolation** / **P2P blocking**:
   - Must **not** block the phone from reaching the gateway / other subnets in a way that breaks inter-VLAN (isolation is L2 between stations on the same SSID; inter-VLAN is usually OK if the UDM allows it).
   - Leave isolation **on** if you want (guests still cannot talk to each other); that does **not** replace UDM firewall.
4. Uplink / switch port to UDM (or core switch): **trunk** with VLAN 15 + management VLAN as designed.
5. No need to “enable AirPlay” on Cambium — there is no such toggle; discovery + ACL are on the UDM.

EasyPass / captive portal: after the voucher is accepted, the client gets normal forwarding; AirPlay then depends on UDM mDNS + firewall only.

---

## 5. Switch / trunk (if not direct AP → UDM)

On any switch between Cambium and UDM:

- Trunk carries **VLAN 1** and **VLAN 15**
- Native VLAN consistent with your design
- No ACL on the switch that drops multicast or guest→LAN before the UDM

---

## 6. Test plan

1. Phone on **guest SSID**, voucher OK, internet OK.
2. Control Center → Screen Mirroring / AirPlay → target on VLAN 1 appears.
3. Play audio 1–2 minutes (no drop).
4. From another device on VLAN 1, confirm HA / NAS still **unreachable** from the guest phone (browser to their IPs should fail).
5. Repeat after AP roam / phone sleep.

### If discovery fails but internet works

- mDNS reflector off or guest network excluded  
- AirPlay device on wrong VLAN  
- Phone still in portal walled garden (finish EasyPass)

### If device appears but stream fails / stalls

- Firewall allows mDNS-ish traffic only, not unicast to the host → widen rule to **Accept any to AirPlay IP**  
- Wrong IP (DHCP changed) → fix reservation  
- ISP/AP client isolation anomaly → check Cambium + switch

---

## 7. Security summary

| Allowed | Blocked |
| --- | --- |
| Guest → AirPlay device IP(s) on VLAN 1 | Guest → rest of VLAN 1 |
| Guest → Internet | Guest → admin / HA / cameras (unless you add other rules) |
| mDNS between 15 and 1 (for AirPlay services) | Open guest ↔ full LAN |

Add each new AirPlay endpoint as another IP (or group) in the same allow rule.

---

## 8. Relation to Maison app

This is **network-only**. Maison does not proxy AirPlay.  
Once this works: guest can AirPlay from the iPhone; Maison can later do **zone volume** on C4 if those entities exist in HA.

---

*Replace example IP `192.168.1.50` with the real reserved address. UniFi menu labels move between releases; look for mDNS / Bonjour and Traffic/Firewall rules if the path differs.*
