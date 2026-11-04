# Changelog

Toutes les versions notables d’Usvegliu. Le numéro tient dans `custom_components/usvegliu/manifest.json` et dans le tag Git `vX.Y.Z`. HACS lit les **releases GitHub**, pas seulement les tags.

Le schéma est [SemVer](https://semver.org/lang/fr/) : MAJEUR.MINEUR.CORRECTIF.

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
