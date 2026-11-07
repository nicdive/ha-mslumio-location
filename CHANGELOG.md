# Changelog

Toutes les versions notables d’Usvegliu. Le numéro tient dans `custom_components/usvegliu/manifest.json` et dans le tag Git `vX.Y.Z`. HACS lit les **releases GitHub**, pas seulement les tags.

Le schéma est [SemVer](https://semver.org/lang/fr/) : MAJEUR.MINEUR.CORRECTIF.

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
