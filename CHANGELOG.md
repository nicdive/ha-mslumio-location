# Changelog

Toutes les versions notables d’Usvegliu. Le numéro tient dans `custom_components/usvegliu/manifest.json` et dans le tag Git `vX.Y.Z`. HACS lit les **releases GitHub**, pas seulement les tags.

Le schéma est [SemVer](https://semver.org/lang/fr/) : MAJEUR.MINEUR.CORRECTIF.

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
