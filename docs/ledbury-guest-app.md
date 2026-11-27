# 49 Ledbury — guide Maison (locataire)

App **Maison** pour **49 Ledbury Road** (thème Ledbury, **anglais**). Lien personnel (mail / message) : actif **le jour d’arrivée** → fin du jour de départ.

Ouvrir sur le téléphone, de préférence sur le **Wi‑Fi guest** de la maison. iPhone : Share → **Add to Home Screen**.

Si trop tôt : **Available from \<date\>.**

---

## Onglets

N’apparaissent que s’il y a quelque chose à afficher.

| Onglet | Rôle |
| --- | --- |
| **Home** | Salutation, météo Londres, alarme / chargeur (statut) |
| **Heating** | Chauffage par pièce (pas de clim ni ventilateur) |
| **Lights** | Lumières + scènes |
| **Access** | Serrures, volets / portes, alarme, sonnette, chargeur |
| **Sound** | Zones audio (si configurées) |
| **TV** | Télécommandes Apple TV (si configurées) |
| **Info** | Wi‑Fi, code porte, QR / partage de l’app |

---

## Home

- Logo **49 Ledbury**, *Good morning / afternoon / evening*.
- **Weather in London**.
- **Home Alarm** : Armed / Disarmed seulement (pas de bouton ici).
- Chargeur véhicule : seulement s’il est branché.

---

## Heating

**Adjust** (consigne ±, on/off) et **Overview** (cartes). Toucher une pièce → cadran. Pas de Cool / fan.

---

## Lights

Par pièce ; scènes en haut si autorisées. Icône = on/off. Variation : glisser horizontalement (~10 %).

---

## Access

Selon le séjour : locks, volets / portail, **Arm / Disarm** (avec confirmation), sonnette (popup + éventuelle photo / open gate), chargeur.

---

## Sound (si présent)

Play / pause, volume, mute, **Mute all**.

---

## TV (si présent)

Liste des TV (ex. Living, Kitchen…). Ouvrir une TV :

- **Turn on / off** (CEC via Apple TV)
- Pad ▲▼◀▶ + OK, Menu, Home
- Volume ± / mute

Pas de choix de source (box / sat / CCTV) : une Apple TV est **fixée** par écran. Control4 peut encore free-router hors Maison.

**AirPlay** depuis l’iPhone (musique / vidéo / mirroring) vers une Apple TV : Control Center, sur le Wi‑Fi guest — indépendant de l’onglet TV (réglage réseau villa).

---

## Info

Wi‑Fi + code, code porte (Keypad) si activé, QR pour partager l’app. Pas de mot de passe Home Assistant ici.

---

## Limites

- Uniquement les équipements autorisés pour le séjour.
- Tablette murale (`/house/…`) : **LAN** villa seulement.
- Après départ : lien fermé ; Wi‑Fi parfois +1 jour.

Plaquette PDF : [ledbury-manual/49-Ledbury-Guest-User-Manual.pdf](ledbury-manual/49-Ledbury-Guest-User-Manual.pdf).

### Setup propriétaire (résumé)

1. **Pulse-Eight** + **Apple TV** (appairage PIN) dans HA.  
2. Usvegliu → **Options** : jusqu’à 4 TV = nom + `media_player` ATV + sortie Neo + entrée Neo ATV.  
3. ATV dans les **entités locataire**.  
4. AirPlay guest Wi‑Fi : [ledbury-airplay-vlan15.md](ledbury-airplay-vlan15.md) (mDNS + firewall Hotspot → IP ATV).

### À venir

- **Push sonnette** (Web Push si l’app est en arrière-plan) — pas encore.

*Usage locataire — thème 49 Ledbury. Console / U Svegliu hors sujet.*
