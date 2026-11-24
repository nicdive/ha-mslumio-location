# 49 Ledbury — guide de l’app locataire

Interface **Maison** pour les hôtes de **49 Ledbury Road** (thème Ledbury, langue **anglaise**). Lien personnel reçu par mail / message d’accueil ; actif **le jour d’arrivée**, jusqu’à la fin du jour de départ.

Ouvrir le lien sur le téléphone (idéalement sur le Wi‑Fi de la maison). Sur iPhone : Partager → **Add to Home Screen**. Sur Android : menu ⋮ → Installer / Add to Home screen.

---

## Accès avant l’arrivée

Si le lien est ouvert trop tôt : **Available from \<date\>.** (ou *Available on your arrival day*).

Les codes Wi‑Fi / porte peuvent déjà figurer dans le mail ; l’app elle-même ne s’ouvre qu’à l’arrivée.

---

## Navigation (barre du bas)

Les onglets n’apparaissent que s’il y a quelque chose à afficher pour ce séjour.

| Onglet | Rôle |
| --- | --- |
| **Home** | Accueil : salutation, météo Londres, statut alarme / chargeur si présent |
| **Heating** | Chauffage par pièce (Ledbury = chauffage seul, pas de clim ni ventilateur) |
| **Lights** | Lumières et scènes |
| **Access** | Serrures, volets / portes, alarme, sonnette / visiophone, chargeur |
| **Sound** | Zones audio (si configurées) |
| **Info** | Wi‑Fi, code porte, QR / lien pour partager l’app |
| **Pool** | Uniquement si des données piscine sont branchées (rare à Ledbury) |

---

## Home

- Logo **49 Ledbury**, message du type *Good morning / afternoon / evening*.
- Météo locale (**Weather in London**).
- **Home Alarm** : état seulement (Armed / Disarmed) — pas de bouton ici.
- Chargeur véhicule : affiché s’il est branché (état de charge).

---

## Heating

Deux vues : **Adjust** (consigne ±, marche/arrêt) et **Overview** (cartes pièces).

- Toucher une pièce pour le **cadran** de consigne (− / on-off / +).
- Pas de commande « Cool » ni de vitesses d’air (spécifique Ledbury).
- Température extérieure affichée en pastille si un capteur est configuré.

---

## Lights

- Groupées par pièce ; **Scenes** en haut si des scènes sont autorisées.
- Toucher l’icône lampe : on / off.
- Lumières à variation : **glisser horizontalement** sur la ligne (par pas de ~10 %) pour régler la luminosité ; relâcher pour valider.

---

## Access

Selon ce qui est exposé au séjour :

- **Locks** — Open / Close (déverrouiller / verrouiller).
- **Shutters / covers / gates** — Open / Close / Stop.
- **Home Alarm** — **Arm** / **Disarm** avec confirmation (*Arm the alarm?* / *Disarm the alarm?*).
- **Door entry** — si quelqu’un sonne : popup *Someone is at the door*, éventuelle caméra, bouton **Open the gate**.
- **Vehicle / charger** — statut (Available, Charging, Charged…).

---

## Info

- **Wi‑Fi network** + **Wi‑Fi code** (copie possible).
- **Door code** (PIN Keypad), s’il est activé pour le séjour.
- **Share the app** / QR : ouvrir le même séjour sur un autre téléphone.

Le mot de passe Home Assistant **n’apparaît pas** dans cette app (réservé à la Console propriétaire).

---

## Sound (si présent)

Play / pause, volume ±, mute par zone, **Mute all**.

---

## Limites utiles à savoir

- L’app ne commande que les équipements autorisés pour les locataires.
- Pas de réglages d’intégration, pas de calendrier, pas de comptes.
- Tablette murale : URL maison (`/house/…`) réservée au **LAN** de la villa.
- Après le départ : le lien se ferme ; le Wi‑Fi peut rester un jour de plus selon la config.

---

*Document d’usage locataire — thème 49 Ledbury uniquement. La Console propriétaire et U Svegliu sont hors sujet.*
