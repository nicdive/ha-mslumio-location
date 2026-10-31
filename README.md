# MS Lumio

Intégration Home Assistant (custom component, installable via HACS) pour une maison en location courte durée. Elle relie un **calendrier de réservations** déjà présent dans Home Assistant à :

1. des **vouchers hotspot UniFi** créés sur l'UDM, puis supprimés au départ, en cas d'annulation ou de séjour raccourci ;
2. un **compte Home Assistant non administrateur** par séjour (ou un compte unique dont le mot de passe tourne), limité aux entités de chauffage, volets et éclairage ;
3. un **journal** (événement Home Assistant + CSV) qui dit qui a reçu quoi, et quand.

L'intégration ne remplace pas le portail captif : le locataire saisit le code sur la page hotspot UniFi, comme aujourd'hui. Elle ne crée aucune redirection de port et n'ouvre rien vers Internet.

## Ce qui a été vérifié, et ce qui ne l'a pas été

Vérifié dans la documentation et dans les tests de ce dépôt (31 octobre 2026), **sans UDM ni Home Assistant réel** :

| Sujet | Source | Retenu dans le code |
| --- | --- | --- |
| Création de vouchers | [Generate Vouchers](https://developer.ui.com/network/v11.0.97/createvouchers), API Network v11.0.97 | `POST /v1/sites/{siteId}/hotspot/vouchers`, corps `name`, `count: 1`, `timeLimitMinutes`, `authorizedGuestLimit`, `rxRateLimitKbps`, `txRateLimitKbps` |
| Lecture / suppression | [List](https://developer.ui.com/network/v11.0.97/getvouchers), [détail](https://developer.ui.com/network/v11.0.97/getvoucher), index [llms.txt](https://developer.ui.com/llms.txt) | `GET` paginé (`offset`, `limit`, enveloppe `data` ou `vouchers`), `DELETE` unitaire ; un 404 est traité comme « déjà supprimé » |
| Authentification | [Getting started](https://developer.ui.com/network/v11.0.97/gettingstarted) et [aide Ubiquiti](https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API) | En-tête `X-API-KEY`. Les redirections sont refusées pour que la clé ne quitte pas l'hôte |
| Horloge du voucher | Même page « Generate Vouchers » | `timeLimitMinutes` démarre **à la première autorisation** sur le portail, pas à la date d'arrivée. Pas de date de fin absolue dans ce schéma |
| Arrivée de l'API hotspot | [External Hotspot API](https://help.ui.com/hc/en-us/articles/31228198640023-External-Hotspot-API-for-Authorization-Clients) (Network 9.1, mars 2025) | L'intégration parle à l'API Integration locale, pas à l'ancienne API cookie |
| Préfixe local | Documentation officielle (l'API tourne sur la console) + montages décrits par les clients UniFi OS (`/proxy/network/integration` puis `/integration`) | Les deux préfixes sont essayés. Le premier qui répond à `GET /v1/info` est retenu |
| Comptes HA | Code `homeassistant/auth` (branche `dev`) : `async_create_user`, `async_remove_user`, `HassAuthProvider.async_add_auth` / `async_change_password` | Groupe `system-users` **non utilisé** : sa politique est « toutes les entités ». Groupe `system-admin` refusé. Utilisateur `local_only` |
| Politique d'entités | [Permissions](https://developers.home-assistant.io/docs/auth_permissions/) | Politique `entities.entity_ids` avec `read` + `control`, sans `edit`. Il n'existe pas d'API publique pour créer un groupe : le groupe `ms-lumio-locataires` est écrit dans le magasin d'auth |
| Calendrier | `CalendarEvent` (`uid`, fin exclusive des événements journée entière) | N'importe quelle entité `calendar` |

Une référence tierce de l'API v10.3 montrait d'autres champs (`durationMinutes`, `expiresAt`). Elle **contredit** le portail développeur v11. Le code envoie le schéma v11. Si le contrôleur répond HTTP 400, aucun voucher n'est créé : comparer avec l'OpenAPI affichée sur la console (voir plus bas). Ne pas supposer que le schéma v11 est celui d'un Network 9.0 plus ancien.

**À tester sur le matériel**, dans cet ordre :

1. `GET https://<udm>/proxy/network/integration/v1/info` avec la clé, certificat auto-signé.
2. Création réelle d'un voucher et lecture du `code` (enveloppe `vouchers` ou `data`).
3. Saisie du code sur le portail hotspot, et contrôle que la durée part au premier usage.
4. Suppression au départ et après annulation (le code ne doit plus être accepté).
5. Connexion du compte locataire depuis le VLAN hotspot vers `https://<ip-ha>:8123`, et échec via Nabu Casa.
6. Le locataire ne voit ni ne commande caméras, serrures, alarmes (l'interface et un appel de service). L'historique et le journal HA ne sont pas un contrôle d'accès complet : le vérifier.
7. Règle de pare-feu : depuis le hotspot, seul le port 8123 de HA répond ; le reste du LAN ne répond pas.
8. Redémarrage de HA : pas de second voucher ni de second compte pour le même séjour.

Les tests de ce dépôt (`pytest`) simulent le contrôleur. Ils ne remplacent pas cette liste.

## Installation

Home Assistant 2025.1 ou plus récent.

### HACS

1. HACS → ⋮ → *Dépôts personnalisés*.
2. URL `https://github.com/nicdive/ha-mslumio-location`, catégorie **Intégration**.
3. Télécharger **MS Lumio**, redémarrer Home Assistant.
4. Paramètres → Appareils et services → Ajouter une intégration → **MS Lumio**.

### Copie manuelle

Copier `custom_components/ms_lumio` dans `/config/custom_components/ms_lumio`, redémarrer, puis ajouter l'intégration.

## Clé API sur l'UDM Pro Max

La clé n'est saisie que dans le formulaire d'intégration. Elle est stockée dans l'entrée de configuration (`core.config_entries`), comme les autres intégrations. Elle n'est pas dans le code, le dépôt, les logs, ni le fichier de diagnostics (les champs secrets y sont remplacés par `**REDACTED**`).

1. Ouvrir UniFi Network sur l'UDM (application locale, pas seulement unifi.ui.com).
2. **Settings → Control Plane → Integrations** (l'intitulé a aussi été « Integrations » dans le menu de l'application ; sur Site Manager : **Settings → API Keys** sur [unifi.ui.com](https://unifi.ui.com)).
3. Créer une clé. Elle ne s'affiche qu'une fois : la coller dans MS Lumio, pas dans un fichier du dépôt.
4. Network 9.1 ou plus récent est nécessaire pour l'API hotspot. Le schéma de corps utilisé ici est celui publié pour Network 11.0.97. La page Integrations de la console montre l'OpenAPI **de votre version** : c'est la référence en cas de HTTP 400.

L'intégration parle à l'UDM **sur le LAN** (`https://<ip-udm>/proxy/network/integration/v1/...`). Elle n'utilise pas le connecteur cloud `api.ui.com`.

Adresse : IP du UDM, port 443. Si l'interface a changé de menu, l'essentiel est une clé acceptée par `X-API-KEY` sur ces URL.

### Certificat TLS

L'UDM présente un certificat auto-signé. La case **Vérifier le certificat TLS** est décochée par défaut, sinon la première connexion échoue. Dans cet état, la clé est envoyée sans vérification du serveur : uniquement sur le réseau local, vers l'IP que vous avez saisie. Les redirections HTTP sont refusées.

Si vous installez un certificat auquel Home Assistant fait confiance, cochez la vérification.

### Repli si l'API ne répond pas

L'intégration essaie `https://<udm>/proxy/network/integration/v1/info`, puis `https://<udm>/integration/v1/info`.

| Réponse | Lecture |
| --- | --- |
| HTTP 401 / 403 | Clé refusée. En recréer une. |
| TLS | Cocher ou décocher la vérification selon le certificat. |
| HTTP 404 sur les deux préfixes | API Integration absente (firmware / Network trop ancien, ou chemin modifié). |
| HTTP 400 à la création | Le corps v11 n'est pas celui de cette version. Comparer avec l'OpenAPI de la console. Aucun second essai n'est envoyé, pour ne pas créer un voucher avec un autre sens. |

Il n'y a **pas** de repli vers l'ancienne API privée (`/proxy/network/api/...`, cookie d'admin). Elle n'est pas l'API à clé demandée, et elle demanderait un mot de passe administrateur UniFi.

Repli opérationnel : décocher *Créer les vouchers UniFi*. Les séjours peuvent continuer d'alimenter le journal et les comptes HA ; les vouchers se créent à la main dans UniFi. Les identifiants déjà créés ici ne sont pas oubliés : la suppression reprend quand la case est recochée.

Exemple à lancer **sur le LAN**, une fois, pour voir la réponse réelle (remplacer les valeurs, ne pas commiter la clé) :

```bash
curl --fail-with-body -k \
  -H "X-API-KEY: ${UNIFI_API_KEY}" \
  -H "Accept: application/json" \
  "https://192.168.1.1/proxy/network/integration/v1/sites"
```

## Configuration

Le formulaire demande ensuite :

| Réglage | Défaut | Rôle |
| --- | --- | --- |
| Calendrier | — | N'importe quelle entité `calendar`. Le **titre** est le nom du locataire, les dates sont le séjour. |
| Jours avant l'arrivée | 3 | Création du voucher et du compte à partir de cette avance. |
| Appareils | 10 | `authorizedGuestLimit` : un seul code, plusieurs appareils. |
| Débits | 100 / 100 Mbit/s | Convertis en kbit/s SI : 100 Mbit/s = 100000 kbit/s. |
| Jours supplémentaires | 1 | Durée envoyée = longueur du séjour + 1 jour. |
| Comptes | Un par séjour | Ou un compte `locataire` dont le mot de passe change quand plus aucun séjour n'est actif, puis au suivant. |
| Chauffage, volets, éclairage | listes vides | Seules entités autorisées au locataire. |
| Journal | `ms_lumio/journal.csv` | Sous le dossier de configuration, ou un dossier média. |
| Titres ignorés | `not available`, `indisponible`, `fermé`, … | Les blocages Airbnb / Booking ne deviennent pas des vouchers. |
| Impression | désactivée | Voir plus bas. |

Un second passage avec les mêmes dates ne crée pas un deuxième voucher ni un deuxième compte. Au redémarrage, un voucher qui porte déjà le nom `<locataire> <arrivée>/<départ>` est réutilisé ; un doublon de ce nom est supprimé.

Nom du voucher : `Jean Dupont 2026-07-10/2026-07-17`. Les apostrophes sont retirées (le filtre UniFi `name.eq('…')` ne les supporte pas).

Séjour « journée entière » : la date de fin ICS est exclusive. Un événement du 10 au 17 est un départ le 17 au matin, soit 7 nuits, plus 1 jour, soit 8 jours de voucher.

Le capteur **Code voucher** affiche le code du séjour en cours (sinon le prochain déjà créé, sinon `aucun`). Il n'est pas dans la politique du locataire. Le mot de passe HA n'est pas un capteur.

## Pare-feu (zone Hotspot → HA:8123 seulement)

Network 9 classe le réseau invité en zone **Hotspot**. La politique par défaut Hotspot → Internal est en principe **Block**. La laisser ainsi.

Ajouter **une** règle d'autorisation, rien d'autre :

- Nom : `Hotspot vers Home Assistant`
- Action : Allow
- Zone source : **Hotspot** (Any, ou seulement le réseau invité)
- Zone destination : **Internal**
- Destination : objet IP de la machine Home Assistant, pas le réseau entier
- Port : **TCP 8123** uniquement

Ne pas :

- passer la politique Hotspot → Internal à Allow ;
- créer une redirection WAN (port forward) vers 8123 ;
- publier Home Assistant sur Internet pour les locataires ;
- compter sur Nabu Casa pour eux : les comptes créés ici sont `local_only`. Une IP privée (le VLAN hotspot, y compris un autre sous-réseau RFC1918) peut se connecter ; une IP publique ou le relais cloud, non.

Le portail captif et les conditions d'utilisation restent ceux d'UniFi. Le voucher n'ouvre pas HA : c'est la règle ci-dessus qui ouvre uniquement le port 8123.

mDNS (`homeassistant.local`) ne traverse en général pas le VLAN invité. Donner aux locataires l'URL en **adresse IP** (`http://192.168.x.x:8123/ms-lumio`), ou un nom DNS servi sur le hotspot.

## Accès Home Assistant des locataires

Pour chaque séjour (mode par défaut) :

- utilisateur **non propriétaire**, **non administrateur**, **local uniquement** ;
- groupe `ms-lumio-locataires`, politique limitée aux entités choisies (`climate`, `cover`, `light`, et quelques domaines du même ordre : `fan`, `switch`, `humidifier`, `water_heater`) ;
- `camera`, `lock`, `alarm_control_panel`, `image`, `siren` sont rejetés s'ils sont proposés ;
- au départ, à l'annulation ou au raccourcissement qui sort de la fenêtre : le compte est **supprimé** (mode par séjour) ou **désactivé** (compte unique, jusqu'au séjour suivant).

Le mot de passe est généré dans Home Assistant (`token_urlsafe`, sous la limite bcrypt de 72 octets). Il n'est pas écrit dans les logs. Il part dans la notification persistante (visible des administrateurs) et dans le CSV.

Limite connue, à traiter comme telle : Home Assistant n'a pas d'ACL complète. La politique de groupe est le mécanisme prévu (`entity_ids` est consulté avant le reste), mais toutes les API historiques ne filtrent pas de la même façon. Après installation, ouvrir une session locataire réelle et tenter d'atteindre une caméra, une serrure, les réglages et `/api/states`. Tant que ce contrôle n'est pas fait, ne pas considérer les caméras comme isolées. Le pare-feu ne remplace pas cet essai, et l'essai ne remplace pas le pare-feu.

Tableau de bord : URL `ms-lumio`, titre **Séjour**, visible des non-administrateurs, cartes thermostat / volets / éclairage. L'intégration le crée si la collection Lovelace en mémoire est joignable (commande websocket `lovelace/dashboards/create`). Sinon une réparation l'indique. Créer alors un tableau de stockage d'URL `ms-lumio` (le tiret est obligatoire) et appeler `ms_lumio.appliquer_tableau`.

Mettre les autres tableaux (vue d'ensemble, caméras, serrures) en **réservé aux administrateurs**. L'intégration ne le fait pas toute seule, pour ne pas masquer l'interface de l'owner.

## Journal et Synology

Fichier CSV, une ligne par action (`voucher_cree`, `voucher_adopte`, `voucher_regenere`, `voucher_supprime`, `acces_cree`, `acces_regenere`, `acces_supprime`, `acces_desactive`). Colonnes : horodatage, action, réservation, locataire, début, fin, id voucher, **code**, utilisateur, **mot de passe**, détail.

Ce fichier est l'archive. Il contient des secrets. Le poser sur un partage Synology monté dans Home Assistant, par exemple :

- monter le partage dans `/media/synology` (ou sous `/config/...`) ;
- régler le chemin sur `/media/synology/ms-lumio/journal.csv`.

Un chemin qui sort de la configuration et des dossiers média est refusé (`../etc/passwd` inclus). Aucun identifiant Synology n'est demandé : le montage est celui déjà fait par l'hôte.

L'événement `ms_lumio_journal` reprend la même trace **sans** le code complet (deux derniers caractères seulement) et **sans** le mot de passe, pour ne pas le verser dans le journal et les traces.

Le magasin interne (`.storage/ms_lumio.<entrée>`) est privé. Il sert à ne pas recréer les accès au redémarrage. Le CSV reste la copie à archiver.

## Notification et impression

À chaque nouveau code ou mot de passe : notification persistante `MS Lumio — <locataire>`. Un service `notify.…` optionnel reçoit le même texte (beaucoup de notifiers recopient le message dans le log : ne l'activer que si ce log reste privé).

L'impression n'est pas faite par l'intégration. Service `ms_lumio.imprimer_voucher` (ou la case « événement d'impression », désactivée par défaut) : événement `ms_lumio_print_voucher` avec le code en clair, pour une automatisation qui imprime. Cet événement peut apparaître dans les traces d'automatisation. Le laisser désactivé si personne n'imprime.

## Services

Tous exigent un administrateur lorsque l'appel porte un utilisateur. Une automatisation lancée sans utilisateur (contexte vide) passe : ne pas exposer ces services à un tableau locataire.

| Service | Effet |
| --- | --- |
| `ms_lumio.regenerer_voucher` | Nouveau code pour le séjour (l'ancien est supprimé). |
| `ms_lumio.regenerer_acces` | Nouveau mot de passe. |
| `ms_lumio.renvoyer_notification` | Renvoie code et mot de passe à l'administrateur. |
| `ms_lumio.imprimer_voucher` | Événement d'impression, réponse avec le code. |
| `ms_lumio.exporter_journal` | Chemin du CSV. |
| `ms_lumio.appliquer_tableau` | Réécrit les cartes du tableau `ms-lumio`. |

`reservation_key` vide = le séjour affiché par le capteur.

## Idempotence et annulations

- Même séjour, mêmes dates, voucher encore présent : aucun `POST`.
- Séjour raccourci ou allongé (même UID) : l'ancien voucher est supprimé, un nouveau code est créé, le journal l'indique. L'API officielle consultée n'a pas de modification unitaire.
- Événement disparu du calendrier dans la fenêtre lue, ou date de fin passée : voucher supprimé, compte retiré.
- Un séjour hors de la fenêtre lue n'est pas traité comme une annulation.
- Panne de l'UDM : le cycle s'arrête **avant** toute suppression. Une coupure réseau ne retire pas les accès.
- Titre dans la liste d'exclusion, séjour annulé (`cancelled`), ou durée au-delà de 60 jours : ignoré.

Sans UID calendrier, la clé est un condensat du nom et des dates : renommer le locataire ressemble à une annulation suivie d'une nouvelle arrivée (nouveau code).

## Sécurité, résumé

- Clé API : entrée de configuration uniquement, filtre de logs en plus, diagnostics redactés, pas de redirection HTTP.
- TLS vérifiable, décoché par défaut à cause du certificat d'usine, documenté ci-dessus.
- Locataires : pas admin, pas owner, pas `system-users`, `local_only`, entités listées seulement.
- Aucune exposition Internet ajoutée. La règle de pare-feu est à créer sur l'UDM ; l'intégration ne pousse pas de règle firewall (elle ne touche pas à cette partie de l'API).
- Mots de passe et codes absents des logs et des événements ordinaires. Présents dans le CSV, la notification admin, et l'événement d'impression si vous l'activez.
- Le capteur de code est lisible par qui a le droit de le lire. Il n'est pas donné au groupe locataire.

## Développement

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent le client UniFi (contrôleur HTTP local, clé dans `X-API-KEY` et pas dans l'URL, repli de préfixe, pagination, 404, refus de redirection), le calcul des séjours, l'idempotence, l'adoption d'un voucher déjà nommé, l'annulation, le remplacement quand le séjour raccourcit, l'absence de révocation si le contrôleur ne répond pas, le CSV, le chemin de journal, la rédaction des diagnostics et le refus des domaines caméra / serrure.

## Limites connues

- Horloge UniFi au premier usage du code, pas à l'arrivée. Un essai du code le jour de la création (J−3) consume trois jours. L'avance de création est réglable ; le jour supplémentaire ne compense pas un essai très anticipé.
- Schéma v11 non confirmé sur un UDM Pro Max de cette maison. HTTP 400 = s'arrêter et lire l'OpenAPI locale.
- Groupe locataire via une API interne de Home Assistant. À recontrôler après chaque montée de version majeure.
- Pas d'ACL parfaite. Le test manuel locataire fait partie de la mise en service.
- Le tableau Lovelace n'est créé que si la collection déjà chargée par HA est retrouvée. Sinon, création manuelle d'URL `ms-lumio`.
- Un seul capteur de code : le séjour en cours, ou à défaut le prochain.
- Compte partagé : un seul mot de passe pour les séjours qui se chevauchent.
- Pas de pilotage du portail captif, des conditions d'utilisation, ni du pare-feu UniFi.
