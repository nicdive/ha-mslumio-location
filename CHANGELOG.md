# Changelog

Toutes les versions notables d’Usvegliu. Le numéro tient dans `custom_components/usvegliu/manifest.json` et dans le tag Git `vX.Y.Z`. HACS lit les **releases GitHub**, pas seulement les tags.

Le schéma est [SemVer](https://semver.org/lang/fr/) : MAJEUR.MINEUR.CORRECTIF.

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
