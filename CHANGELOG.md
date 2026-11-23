# Changelog

Toutes les versions notables d’Usvegliu. Le numéro tient dans `custom_components/usvegliu/manifest.json` et dans le tag Git `vX.Y.Z`. HACS lit les **releases GitHub**, pas seulement les tags.

Le schéma est [SemVer](https://semver.org/lang/fr/) : MAJEUR.MINEUR.CORRECTIF.

## [0.6.90] — 2026-11-23

### Corrigé
- iPhone : dock `fixed` + correction du gap mesuré (100lvh / `--frame-height`) — plus de bande vide sous la nav.

[0.6.90]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.90

## [0.6.89] — 2026-11-23

### Corrigé
- iPhone : dock en flux sticky (plus de `position:fixed` / visualViewport) — plus de bande vide sous la nav à l’ouverture.

[0.6.89]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.89

## [0.6.88] — 2026-11-23

### Modifié
- Accueil alarme : libellé court « Home Alarm » (plus le nom HA complet).

[0.6.88]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.88

## [0.6.87] — 2026-11-23

### Modifié
- Accueil : statut alarme uniquement (plus de bouton) ; icône rouge quand armée. Armer/désarmer + confirm restent dans Accès.

[0.6.87]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.87

## [0.6.86] — 2026-11-23

### Ajouté
- Alarme : confirmation avant armer / désarmer, et statut visible sur la page d’accueil.

[0.6.86]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.86

## [0.6.85] — 2026-11-23

### Corrigé
- iPhone PWA : dock collé au bas du *visual viewport* (plus de bande vide sous la nav à l’ouverture).

[0.6.85]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.85

## [0.6.84] — 2026-11-23

### Corrigé
- Bandeau Ledbury : artwork d’origine (police/espacement), fond transparent, marge haute pour ne plus couper le 49.

[0.6.84]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.84

## [0.6.83] — 2026-11-23

### Corrigé
- iPhone : bandeau bas collé au bord au premier ouverture PWA (plus de `transform` sur le dock fixed).

[0.6.83]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.83

## [0.6.82] — 2026-11-23

### Corrigé
- Bandeau Ledbury **transparent** (le vert de l’app apparaît derrière), location mieux espacée.

[0.6.82]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.82

## [0.6.81] — 2026-11-23

### Corrigé
- Bandeau Ledbury : fond crème (plus noir), « Notting Hill · London » plus grand et mieux espacé.

[0.6.81]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.81

## [0.6.80] — 2026-11-23

### Amélioré
- Icônes PWA Ledbury : monogramme vert/or sur fond crème (180 / 192 / 256 / 512).

[0.6.80]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.80

## [0.6.79] — 2026-11-23

### Amélioré
- Bandeau Maison Ledbury : nouveau header noir / or / vert (essai).

[0.6.79]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.79

## [0.6.78] — 2026-11-23

### Amélioré
- Icônes PWA **49 Ledbury** : nouveau monogramme or sur vert forêt (180 / 192 / 256 / 512).

[0.6.78]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.78

## [0.6.77] — 2026-11-23

### Ajouté
- **Tablettes maison** : URL fixe `/usvegliu/house/<jeton>` (service `lien_tablettes`). Toujours active ; le nom affiché suit le séjour. Accès **LAN uniquement** (refus sur Host public / IP WAN).

[0.6.77]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.77

## [0.6.76] — 2026-11-23

### Corrigé
- macOS : plus de bande crème en bas au scroll — le thème Ledbury s’applique aussi sur `html` (overscroll).

[0.6.76]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.76

## [0.6.75] — 2026-11-23

### Corrigé
- iOS (Safari **et** Chrome / tous WebKit) : le logo n’est plus détruit au changement de page — plus de flash de texte à la place du bandeau.

[0.6.75]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.75

## [0.6.74] — 2026-11-23

### Corrigé
- iOS : plus de flash de texte (style « Good afternoon ») à la place du logo en changeant d’onglet — le bandeau reste en place, alt vide.

[0.6.74]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.74

## [0.6.73] — 2026-11-23

### Corrigé
- macOS / Safari : l’icône dock ne retombe plus sur **Usvegliu** — le thème Ledbury est injecté dans le HTML avant `app.js` (plus d’écrasement au premier render).

[0.6.73]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.73

## [0.6.72] — 2026-11-23

### Amélioré
- Ledbury : vert plus doux (`#F2F6F3`), bandeau bas vert légèrement distinct (`--dock`), icônes assorties.
- iPhone : plus de bande blanche sous le dock (fond opaque + extension sous l’indicateur).

[0.6.72]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.72

## [0.6.71] — 2026-11-23

### Corrigé
- Icône Ledbury : marge safe pour macOS/iOS + `logo-ledbury-180` (apple-touch).
- iPhone PWA : dock bas plus collé (plus de double safe-area) ; fond du dock = `--paper` du thème.

[0.6.71]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.71

## [0.6.70] — 2026-11-23

### Amélioré
- Icône PWA **49 Ledbury** : fond vert pâle `#E8F4EE` (identique à l’écran Maison), plus le fond noir.

[0.6.70]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.70

## [0.6.69] — 2026-11-23

### Corrigé
- PWA / signet : `start_url` garde le chemin avec **token** (plus de 403) ; titre **49 Ledbury** / short_name **49Ledbury** selon le thème.
- Le HTML servi injecte déjà le bon manifeste (plus le manifeste statique « Maison »).

[0.6.69]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.69

## [0.6.68] — 2026-11-23

### Corrigé
- Console : plus d’**Entity not found** sur le brouillon Wi‑Fi (entité `text` réelle uniquement, mode manuel).
- Maison Infos : bandeau install avec consigne **menu ⋮ / Installer** (manifest HTTPS, plus `blob:`) — plus seulement « Not now ».

[0.6.68]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.68

## [0.6.67] — 2026-11-23

### Amélioré
- Base **0.6.56** : bandeau Installer dans **Infos**, sélecteur d’entités filtrable (pas de liste à cases).
- Voucher manuel : **code Wi‑Fi par séjour** (brouillon Console + Appliquer / `definir_voucher`).
- Options : **Ajouter tout (domaines)** après le filtre ; case « j’autorise caméras/serrures/alarmes » **mémorisée**.
- Console / webapp : pas de régression UI volontaire (pas de nouveau service worker / dock).

[0.6.67]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.67


## [0.6.66] — 2026-11-23

### Tatonnage
- Contenu identique à **0.6.56**.

[0.6.66]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.66

## [0.6.65] — 2026-11-23

### Tatonnage
- Essai 0.6.57 (ignoré — multi-sélection refusée).

[0.6.65]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.65

## [0.6.64] — 2026-11-23

### Tatonnage
- Contenu identique à **0.6.55**.

[0.6.64]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.64

## [0.6.63] — 2026-11-23

### Tatonnage
- Contenu identique à **0.6.50**.

[0.6.63]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.63

## [0.6.56] — 2026-11-23

### Amélioré
- Message d’installation de la web app déplacé dans l’onglet **Infos**.

[0.6.56]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.56

## [0.6.55] — 2026-11-23

### Amélioré
- Fond Ledbury **très léger** (`#e8f4ee`), même douceur que le rose Usvegliu.

[0.6.55]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.55

## [0.6.54] — 2026-11-23

### Amélioré
- Fond Ledbury **bien visible** (`#c8e2d7`, plus le rose pâle quasi identique).
- Maison : CSS/JS versionnés (`?v=…`) pour forcer le refresh après update.

[0.6.54]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.54

## [0.6.53] — 2026-11-23

### Amélioré
- Thème **49 Ledbury** : fond d’écran vert doux style Notting Hill (`#e6f3ec` / accent `#258d60`). Logos restaurés (inchangés).

[0.6.53]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.53

## [0.6.52] — 2026-11-23

### Amélioré
- Thème **49 Ledbury** : accent Notting Hill `#258d60` (UI + logos).

[0.6.52]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.52

## [0.6.51] — 2026-11-23

### Amélioré
- Console propriétaire en **Français / English** selon l’option Langue.
- Message d’accueil / copie console : **marque de la villa** (Usvegliu ou 49 Ledbury), plus de texte Usvegliu en dur.

[0.6.51]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.51

## [0.6.50] — 2026-11-23

### Ajouté
- App Maison installable (PWA) : manifeste, service worker, icônes, bandeau « Installer l’app » (iOS / Android).

[0.6.50]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.50

## [0.6.49] — 2026-11-23

### Ajouté
- Option **Langue (Maison / console)** : Français ou English, à l’installation et dans les réglages (indépendant du thème).

[0.6.49]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.49

## [0.6.48] — 2026-11-22

### Amélioré
- Ledbury : sous-titre **Notting Hill · London** plus lisible.

[0.6.48]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.48

## [0.6.47] — 2026-11-22

### Amélioré
- Ledbury : porte un peu **plus grande**, écriture légèrement **plus petite**.

[0.6.47]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.47

## [0.6.46] — 2026-11-22

### Amélioré
- Ledbury : bandeau **horizontal** (porte à gauche, écriture à droite), moins haut.

[0.6.46]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.46

## [0.6.45] — 2026-11-22

### Amélioré
- Ledbury : **vraie porte** illustrée (tes fichiers) + typo conservée, bandeau empilé plus présent.

[0.6.45]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.45

## [0.6.44] — 2026-11-22

### Amélioré
- Ledbury : bandeau **plus graphique** (porte stylisée + typo type Usvegliu) et **plus grand** à l’écran.

[0.6.44]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.44

## [0.6.43] — 2026-11-22

### Amélioré
- Ledbury : nouveaux **logo** et **bandeau** (porte 49 + LEDBURY / Notting Hill · London), fond transparent.

[0.6.43]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.43

## [0.6.42] — 2026-11-22

### Amélioré
- Lumière : regroupement par **pièce** (area HA).

[0.6.42]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.42

## [0.6.41] — 2026-11-22

### Amélioré
- Lumière : ampoule **jaune** quand allumée (plus le vert du thème Ledbury).

[0.6.41]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.41

## [0.6.40] — 2026-11-22

### Corrigé
- Config flow : plus d’erreur **400 Bad Request** après 0.6.39 (TargetSelector sans filtres vides `entity={}` / `area={}`).

[0.6.40]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.40

## [0.6.39] — 2026-11-22

### Amélioré
- Options : un seul sélecteur **Équipements locataire** (target HA) pour cocher plusieurs entités, appareils ou zones d’un coup.

[0.6.39]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.39

## [0.6.38] — 2026-11-22

### Corrigé
- Heatmiser (Ledbury) : le bouton On/Off Maison marche sans mode HVAC « off » — Off → preset **Standby**, On → **Home** (l’UI reste simple On/Off).

[0.6.38]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.38

## [0.6.37] — 2026-11-22

### Amélioré
- Ledbury : même style propre qu’Usvegliu ; logo porte **transparent** et plus large.
- Interface Ledbury en **anglais** ; météo **London** (plus Lumio).
- Polices équipements inchangées (stack Usvegliu).

[0.6.37]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.37

## [0.6.36] — 2026-11-22

### Amélioré
- Thème **49 Ledbury** : logo porte Portobello en bannière, palette crème / vert forêt / blush.
- Ledbury = chauffage sol + radiateurs : plus de soufflante / vitesses d’air dans Maison ; onglet toujours « Chauffage ».

[0.6.36]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.36

## [0.6.35] — 2026-11-22

### Ajouté
- Setup : 3ᵉ choix **Voucher manuel** (EasyPass sans cnMaestro X / sans API). Code collé dans Options, affiché dans Maison et le mail.

[0.6.35]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.35

## [0.6.34] — 2026-11-21

### Corrigé
- Setup : liste claire **UniFi / Cambium** à la place du menu à flèches sans libellés ; titre « Wi-Fi de la maison ».

[0.6.34]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.34

## [0.6.33] — 2026-11-21

### Ajouté
- Installation **Cambium seule** : plus besoin d’UDM. Au setup, choisir UniFi ou Cambium EasyPass ; la voie Cambium préremplit le thème 49 Ledbury.

[0.6.33]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.33

## [0.6.32] — 2026-11-21

### Ajouté
- Thème Maison **49 Ledbury** (Notting Hill) : logos Portobello, charte vert / blush, mails et titres. Option `guest_theme` (`usvegliu` par défaut, `ledbury` sur l’instance dédiée).

[0.6.32]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.32

## [0.6.31] — 2026-11-21

### Ajouté
- Vouchers Wi-Fi via **Cambium EasyPass Cloud** (cnMaestro), en plus d’UniFi. Options : fournisseur `unifi` (défaut) ou `cambium`, avec client ID/secret, portail et plan voucher. U Svegliu reste sur UniFi ; un second site peut basculer sur Cambium sans fork.

[0.6.31]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.31

## [0.6.30] — 2026-11-08

### Ajouté
- Accès : pictogrammes **porte**, **garage**, **portail**, **volet**, **alarme** et **sonnette**, dans le même trait que la lampe et la voiture.

[0.6.30]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.30

## [0.6.29] — 2026-11-08

### Changé
- Lumières (et lumière piscine) : icône de **lampe** à la place du texte Allumée / Éteinte.

[0.6.29]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.29

## [0.6.28] — 2026-11-08

### Ajouté
- Pictogramme **voiture de profil** (câble vers la borne) sur la carte véhicule de l'accueil et dans Accès, comme sur un écran de wallbox.

[0.6.28]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.28

## [0.6.27] — 2026-11-08

### Corrigé
- Accueil Maison : **Mode démo** ne recouvre plus les dates du séjour (iPad).

[0.6.27]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.27

## [0.6.26] — 2026-11-08

### Ajouté
- Switch **Mode démo** sur l'appareil Usvegliu : la web app Maison affiche une villa complète (10 thermostats, véhicule en charge, lumières, accès, piscine, son) sans attendre les entités Home Assistant. À éteindre avant un vrai séjour.

[0.6.26]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.26

## [0.6.25] — 2026-11-08

### Changé
- Accueil Maison : la borne **véhicule** n'apparaît que si un câble est branché. Affiche **En charge**, **Charge terminée** ou **Branché**, plus le niveau (%) quand Home Assistant le fournit.

[0.6.25]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.25

## [0.6.24] — 2026-11-07

### Changé
- Option **Code PIN Nuki (Keypad)** dans les réglages, distincte du déverrouillage Nuki dans Maison. Décochée (défaut) : le mail d'accueil part sans code porte.

[0.6.24]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.24

## [0.6.23] — 2026-11-07

### Ajouté
- **Code porte Nuki Keypad** par séjour, comme le Wi-Fi : créé dans la fenêtre d'avance (J−3), dans le mail d'accueil et Infos / Console, retiré à la fin du jour de départ (pas le jour Wi-Fi extra). Jeton Web API dans les options. Une panne Nuki n'empêche pas UniFi ni le compte HA.

[0.6.23]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.23

## [0.6.22] — 2026-11-07

### Changé
- Console propriétaire : **accueil** (séjour en cours + prochain), liste ordonnée cliquable, fiche par séjour (identifiants, Wi-Fi, message, actions), onglet **Historique** (séjours clos et journal d'accès). Plus tout sur une seule page.

[0.6.22]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.22

## [0.6.21] — 2026-11-07

### Ajouté
- Message d'accueil **envoyé par mail J−2** si l'adresse du locataire est dans la description (ou le lieu) de l'événement calendrier. Service SMTP dédié (`guest_mail_service`), distinct de la notification propriétaire. **Renvoyer la notification** force aussi ce mail.

[0.6.21]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.21

## [0.6.20] — 2026-11-07

### Ajouté
- Onglet **Son** : volume, pause, muet et *Tout couper* sur les `media_player` cochés (Amp Sonos dès qu'ils sont dans HA). Les TV restent hors app.

[0.6.20]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.20

## [0.6.19] — 2026-11-07

### Modifié
- Interphone : **popup sur l'accueil** (photo Linea + *Ouvrir le portail* à côté) quand ça sonne. Plus de bloc visio dans Accès.

[0.6.19]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.19

## [0.6.18] — 2026-11-07

### Ajouté
- Alarme **Tydom 2** : armer / désarmer via `deltadore_tydom.set_mode_using_stored_pin` si l'intégration est là.
- Accès : **photo de la platine** (caméra Linea / 300EOS cochée), actualisée quand ça sonne.

[0.6.18]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.18

## [0.6.17] — 2026-11-06

### Ajouté
- Web app Maison : **lumière bassin** (onglet Pool), **borne** (en charge / branché / libre), **sonnette** (quelqu'un sonne). Lumières, scènes et alarme (armer / désarmer) restent dans Lumière et Accès.

[0.6.17]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.17

## [0.6.16] — 2026-11-05

### Changé
- Lien Maison (et compte HA) : fin à minuit de la **journée de départ**. Wi-Fi : encore **un jour** après, puis le voucher UniFi est retiré.

[0.6.16]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.16

## [0.6.15] — 2026-11-05

### Changé
- Le **code Wi-Fi** est créé dès les 3 jours avant l'arrivée, pour le message à envoyer. Compte HA et lien Maison restent inactifs jusqu'au jour J.

[0.6.15]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.15

## [0.6.14] — 2026-11-05

### Changé
- Web app Maison : bandeau et icône **U Svegliu** remplacés par le logo villa (citadelle, soleil, olivier).

[0.6.14]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.14

## [0.6.13] — 2026-11-05

### Changé
- Voucher Wi-Fi, compte HA et lien Maison : émis dès la fenêtre d'avance, **actifs seulement le jour d'arrivée** (minuit local). Un essai 24 h reste immédiat.

[0.6.13]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.13

## [0.6.12] — 2026-11-05

### Ajouté
- Web app Maison : onglet **Infos**, QR code pour ouvrir le lien personnel sur un autre téléphone (plus un bouton Copier).

[0.6.12]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.12

## [0.6.11] — 2026-11-05

### Changé
- Web app Maison : la météo de l'accueil indique **Lumio**.
- SSID par défaut : **Usvegliu-Guest** (message Console, Infos, options).

[0.6.11]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.11

## [0.6.10] — 2026-11-05

### Corrigé
- Console : le message à envoyer contient toujours la ligne **Réseau Wi-Fi**, lue sur le séjour ou les réglages (plus seulement si le SSID était déjà collé sur la ligne du séjour).

[0.6.10]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.10

## [0.6.9] — 2026-11-05

### Changé
- Web app Maison : plus de températures sur l'accueil. À la place, la météo du jour à **Calvi** (icônes). La température extérieure de la villa est en coin sur **Clim**. Piscine et pH dans l'onglet **Pool**.

[0.6.9]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.9

## [0.6.8] — 2026-11-05

### Ajouté
- Web app Maison : bandeau **U Svegliu — Villa Lumio Corsica** en tête de l'application (logo villa, pas le mot Usvegliu en capitales).

[0.6.8]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.8

## [0.6.7] — 2026-11-05

### Ajouté
- Console : message à envoyer au locataire (forme de politesse villa, lien personnel Maison, réseau et code Wi-Fi). À copier-coller. Sans identifiants Home Assistant.

[0.6.7]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.7

## [0.6.6] — 2026-11-05

### Changé
- Web app Maison : le bandeau affiche **Chauffage** ou **Clim** selon le mode. Plus de rappel du mode en bas de l'accueil.

[0.6.6]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.6

## [0.6.5] — 2026-11-05

### Changé
- Web app Maison : bouton **Copier** à côté du réseau et du code Wi-Fi (le navigateur ne peut pas rejoindre le hotspot ni saisir le voucher tout seul).
- Clim : un dessin de vent à côté de la force de ventilation, sur la liste et sur le cadran.

[0.6.5]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.5

## [0.6.4] — 2026-11-05

### Changé
- Web app Maison : navigation par sections (Maison, Clim, Lumière, Accès, Infos) au lieu d'un empilement de cartes. Le code Wi-Fi n'apparaît plus sur l'accueil, seulement dans **Infos**. Les thermostats n'affichent plus le nom de pièce en plus de leur libellé. Mise en page tablette (iPad mini) en deux colonnes, barre du bas sur téléphone.

[0.6.4]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.4

## [0.6.3] — 2026-11-04

### Ajouté
- Web app Maison : section **Informations** (nom du réseau Wi-Fi et code voucher du séjour). Le SSID se renseigne dans les options Usvegliu. La section pourra accueillir d'autres consignes plus tard.

[0.6.3]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.3

## [0.6.2] — 2026-11-04

### Corrigé
- Web app Maison : la consigne ne rebondit plus d'un ou deux crans après des appuis rapides. L'affichage garde la valeur choisie jusqu'à ce que Home Assistant la confirme.

### Ajouté
- Console : bouton **Relire le calendrier** (`usvegliu.relire_calendrier`) pour lancer un cycle tout de suite, sans attendre 15 min.

[0.6.2]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.2

## [0.6.1] — 2026-11-04

### Corrigé
- Web app Maison : page blanche. Un backtick cassait `app.js` (le script ne démarrait pas).

[0.6.1]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.1

## [0.6.0] — 2026-11-04

### Changé
- Web app Maison : passe design résidence d'exception (accueil nominatif et dates du séjour, cartes papier, typographie éditoriale, commandes d'accès plus hôtel, libellés en français).

[0.6.0]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.0

## [0.5.9] — 2026-11-04

### Corrigé
- La Console affiche le **mot de passe du compte Home Assistant temporaire**. Home Assistant masque l'attribut nommé `password` dans Lovelace : le capteur l'expose aussi sous `code_compte` / `mot_de_passe`, et chaque séjour a une carte « Mot de passe Home Assistant ». Si rien n'apparaît (séjour créé avant l'archivage), toucher **Nouveau mot de passe**.

### Changé
- Console en deux vues : **Séjours** (identifiants, Wi-Fi, actions) et **Réglages** (options Usvegliu en vigueur, sans clé API ni code alarme).

[0.5.9]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.9

## [0.5.8] — 2026-11-04

### Changé
- La console propriétaire n'est plus réservée aux administrateurs. Les comptes **Utilisateur** (droits de contrôle) la voient et peuvent renouveler ou révoquer. Les comptes locataires Usvegliu ne la voient pas.

[0.5.8]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.8

## [0.5.7] — 2026-11-04

### Corrigé
- La console propriétaire (`usvegliu-proprietaire`) est recréée même si **Séjour** existe déjà. Un tableau créé à la main sous un autre nom (par ex. **Location**, URL `dashboard-location`) n'est plus pris pour la console.
- `usvegliu.appliquer_tableau` retrouve un tableau Lovelace par son URL, pas seulement par la clé interne, et réessaie la console tant qu'elle n'est pas écrite.

[0.5.7]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.7

## [0.5.6] — 2026-11-04

### Ajouté
- Web app Maison : page unique avec lumières et scénarios, Nuki, garage, portail, alarme, températures extérieur / piscine et pH. Les commandes passent par `/api/usvegliu/guest/command` après contrôle de la liste du séjour.

[0.5.6]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.6

## [0.5.5] — 2026-11-04

### Ajouté
- Web app Maison : titre **Chauffage** ou **Climatisation** selon le switch saisonnier du propriétaire. Rouge si la consigne est au-dessus de la mesure en chauffage, bleu si elle est en dessous en climatisation, neutre sinon.

[0.5.5]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.5

## [0.5.4] — 2026-11-04

### Ajouté
- Tableau Lovelace **Console** (`usvegliu-proprietaire`, administrateurs seulement) : séjours actifs, identifiants en direct, boutons pour renouveler ou révoquer le mot de passe et le voucher Wi-Fi.
- Services `usvegliu.revoquer_acces` et `usvegliu.revoquer_voucher` : l'accès n'est recréé qu'avec Régénérer.

[0.5.4]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.4

## [0.5.3] — 2026-11-04

### Ajouté
- Le capteur **Séjours actifs** (et les attributs du code voucher) affiche le mot de passe HA du locataire, destiné au propriétaire. Il est gardé dans le magasin privé de l'intégration. Pas dans le CSV, ni les logs, ni les diagnostics, ni la web app Maison.

[0.5.3]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.3

## [0.5.2] — 2026-11-04

### Ajouté
- Capteur admin **Séjours actifs** : tant que le séjour n'est pas clos, l'administrateur garde le locataire, l'identifiant HA, le code Wi-Fi et le **lien Maison**, même après fermeture de la notification. Le mot de passe HA n'y figure pas (il n'est toujours pas archivé).

[0.5.2]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.2

## [0.5.1] — 2026-11-04

### Corrigé
- Après login, le locataire ouvre le tableau **Séjour** (`usvegliu-sejour`) au lieu de l'accueil Home Assistant, qui restait sur « Chargement des données… ».
- Précision lab : une IP Tailscale `100.x` n'est pas « locale » pour Home Assistant. Un compte `local_only` peut valider le mot de passe puis bloquer le websocket.

[0.5.1]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.1

## [0.5.0] — 2026-11-04

### Ajouté
- Web app Maison en **temps réel** : `GET /api/usvegliu/guest/stream` (SSE) pousse clim et Nuki à chaque `state_changed`. Repli sur un polling 8 s si le flux coupe.

[0.5.0]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.5.0

## [0.4.1] — 2026-11-04

### Corrigé
- `usvegliu.appliquer_tableau` écrit enfin les cartes sur Home Assistant 2026 (Lovelace sous HassKey). Le service renvoie `ok`, `cards` et `reason`.
- Le tableau locataire utilise une vue **sections**, celle créée par HA 2026.

[0.4.1]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.4.1

## [0.4.0] — 2026-11-04

Première version publiée.

### Ajouté
- Intégration Home Assistant `usvegliu` (vouchers UniFi, comptes locataires, journal CSV).
- Web app Maison (jeton de séjour, thermostats, Nuki).
- Service `usvegliu.lien_maison` (lien d’essai 24 h).
- Versioning SemVer : changelog, tags `vX.Y.Z`, release GitHub automatique.

[0.4.0]: https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.4.0
