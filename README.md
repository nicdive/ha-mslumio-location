# Usvegliu

Intégration Home Assistant (custom component, installable via HACS) pour une maison en location courte durée. Elle relie un **calendrier de réservations** déjà présent dans Home Assistant à :

1. des **vouchers hotspot UniFi** créés sur l'UDM, puis supprimés au départ, en cas d'annulation ou de séjour raccourci ;
2. un **compte Home Assistant non administrateur** par séjour (ou un compte unique dont le mot de passe tourne), limité aux entités et appareils choisis, en local par défaut ;
3. un **code porte Nuki Keypad** par séjour (optionnel), créé à l'avance, envoyé dans le mail d'accueil, retiré à la fin du jour de départ ;
4. un **journal** (événement Home Assistant + CSV) qui dit qui a reçu quoi, et quand.

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
| Comptes HA | Code `homeassistant/auth` (branche `dev`) et `helpers/service.py`, `api`, `websocket_api`, `history` | Groupe `system-users` **non utilisé**. `local_only` par défaut, levé seulement si l'option internet du séjour est active. Les services qui visent une entité et `get_states` respectent la politique ; le journal, non (voir plus bas). |
| Politique d'entités | [Permissions](https://developers.home-assistant.io/docs/auth_permissions/) | Politique `entities.entity_ids` avec `read` + `control`, sans `edit`. Il n'existe pas d'API publique pour créer un groupe : le groupe `usvegliu-locataires` est écrit dans le magasin d'auth |
| Calendrier | `CalendarEvent` (`uid`, fin exclusive des événements journée entière) | N'importe quelle entité `calendar` |

Une référence tierce de l'API v10.3 montrait d'autres champs (`durationMinutes`, `expiresAt`). Elle **contredit** le portail développeur v11. Le code envoie le schéma v11. Si le contrôleur répond HTTP 400, aucun voucher n'est créé : comparer avec l'OpenAPI affichée sur la console (voir plus bas). Ne pas supposer que le schéma v11 est celui d'un Network 9.0 plus ancien.

**À tester sur le matériel**, dans cet ordre :

1. `GET https://<udm>/proxy/network/integration/v1/info` avec la clé, certificat auto-signé.
2. Création réelle d'un voucher et lecture du `code` (enveloppe `vouchers` ou `data`).
3. Saisie du code sur le portail hotspot, et contrôle que la durée part au premier usage.
4. Suppression au départ et après annulation (le code ne doit plus être accepté).
5. Connexion du compte locataire depuis le VLAN hotspot vers `https://<ip-ha>:8123`. Sans l'option internet : échec via Nabu Casa. Avec l'option, et seulement si HA est déjà exposé : succès pendant le séjour, plus après le départ.
6. Le locataire ne voit ni ne commande que les entités choisies (interface, `/api/states`, service sur une entité absente de la liste). Vérifier aussi le journal : le code lu ne le filtre pas.
7. Règle de pare-feu : depuis le hotspot, seul le port 8123 de HA répond ; le reste du LAN ne répond pas.
8. Redémarrage de HA : pas de second voucher ni de second compte pour le même séjour.

Les tests de ce dépôt (`pytest`) simulent le contrôleur. Ils ne remplacent pas cette liste.

## Installation

Home Assistant 2025.1 ou plus récent.

### HACS

Le dépôt doit être **public**. HACS n'installe pas un dépôt privé.

1. HACS → ⋮ → *Dépôts personnalisés*.
2. URL `https://github.com/nicdive/ha-mslumio-location`, catégorie **Intégration**.
3. Télécharger **Usvegliu** en choisissant une **release GitHub** (dernière : [0.6.30](https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.30)), pas le commit d'une branche.
4. Redémarrer Home Assistant.
5. Paramètres → Appareils et services → Ajouter une intégration → **Usvegliu**.

Pour **mettre à jour** (ex. 0.6.29 → 0.6.30) : HACS → Usvegliu → ⋮ → **Redownload** → **0.6.30**, puis redémarrer. Le numéro dans Paramètres → Intégrations ne change qu'après ce redémarrage.

HACS ne liste une version **que** si la [release GitHub](https://github.com/nicdive/ha-mslumio-location/releases) existe. Un numéro dans le `manifest.json` ou une pull request ne suffit pas : sans tag `v0.6.30` poussé, 0.6.30 n'apparaît pas.

## Versions

SemVer dans `custom_components/usvegliu/manifest.json`, historisé dans [CHANGELOG.md](CHANGELOG.md). HACS affiche uniquement les [releases GitHub](https://github.com/nicdive/ha-mslumio-location/releases), pas les tags seuls ni les branches.

Pour publier :

1. Monter le `version` du `manifest.json`.
2. Ajouter une section en tête du changelog.
3. Commit (la branche qui porte ce numéro).
4. Tag annoté `vX.Y.Z` (même numéro que le manifest) et `git push origin vX.Y.Z`.
5. L'action **Release** crée alors la release GitHub. **Sans ce push de tag, HACS reste sur la version précédente.** Si l'action manque : GitHub → Releases → *Create a new release* à partir du tag.

### Copie manuelle

Copier `custom_components/usvegliu` dans `/config/custom_components/usvegliu`, redémarrer, puis ajouter l'intégration.

Si une ancienne copie `custom_components/ms_lumio` est déjà installée : la supprimer, retirer l'entrée **MS Lumio** dans Appareils et services, redémarrer, puis ajouter **Usvegliu**. Le domaine Home Assistant a changé (`usvegliu`) : les services s'appellent maintenant `usvegliu.…`.

## Clé API sur l'UDM Pro Max

La clé n'est saisie que dans le formulaire d'intégration. Elle est stockée dans l'entrée de configuration (`core.config_entries`), comme les autres intégrations. Elle n'est pas dans le code, le dépôt, les logs, ni le fichier de diagnostics (les champs secrets y sont remplacés par `**REDACTED**`).

1. Ouvrir UniFi Network sur l'UDM (application locale, pas seulement unifi.ui.com).
2. **Settings → Control Plane → Integrations** (l'intitulé a aussi été « Integrations » dans le menu de l'application ; sur Site Manager : **Settings → API Keys** sur [unifi.ui.com](https://unifi.ui.com)).
3. Créer une clé. Elle ne s'affiche qu'une fois : la coller dans Usvegliu, pas dans un fichier du dépôt.
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
| Calendrier | — | N'importe quelle entité `calendar`. Le **titre** est le nom du locataire, les dates sont le séjour. L'**adresse mail** du locataire va dans la **description** (pas le titre) pour l'envoi automatique J−2. |
| Jours avant l'arrivée | 3 | Création du voucher Wi-Fi, du code porte, du compte HA et du lien Maison. Login HA et lien Maison ne **s'activent que le jour d'arrivée**. |
| Appareils | 10 | `authorizedGuestLimit` : un seul code, plusieurs appareils. |
| Débits | 100 / 100 Mbit/s | Convertis en kbit/s SI : 100 Mbit/s = 100000 kbit/s. |
| Jours supplémentaires | 1 | Le voucher Wi-Fi reste **un jour après le départ**, puis il est supprimé. Le lien Maison s'arrête à la fin de la journée de départ. |
| Comptes | Un par séjour | Ou un compte `locataire` dont le mot de passe change quand plus aucun séjour n'est actif, puis au suivant. |
| Entités et appareils | listes vides | Tout domaine. Seules ces entités (et toutes les entités des appareils choisis) sont lisibles et commandables. Caméra, serrure et alarme exigent une case de confirmation. |
| Accès internet | désactivé | Pendant le séjour seulement, le compte n'est plus « local uniquement ». Rien n'est ouvert sur le réseau : Home Assistant doit déjà être joignable de l'extérieur. |
| Mail locataire | vide | Service `notify` SMTP (ex. `notify.smtp`). Vide = pas d'envoi auto, le message reste à copier sur la Console. Distinct de la notification propriétaire. |
| Jours avant le mail | 2 | Envoi du message d'accueil (lien Maison, Wi-Fi, code porte) ce nombre de jours avant l'arrivée, une fois les codes créés (J−3 par défaut). |
| Journal | `usvegliu/journal.csv` | Sous le dossier de configuration, ou un dossier média. |
| Titres ignorés | `not available`, `indisponible`, `fermé`, … | Les blocages Airbnb / Booking ne deviennent pas des vouchers. |
| Impression | désactivée | Voir plus bas. |
| URL publique web app | vide | Origine du lien locataire (`https://www.usvegliu.fr`). Vide = URL interne de HA (`/usvegliu/s/…`). |
| Nom du réseau Wi-Fi | vide | SSID affiché au locataire dans **Informations**. |
| Switch chauffage / climatisation | vide | Interrupteur du propriétaire. **Allumé = climatisation**, **éteint = chauffage**. Le locataire le lit, il ne le commande pas. |
| Température extérieure / piscine / pH | vide | Capteurs affichés en tête de la web app, lecture seule. |
| Code alarme | vide | Si le panneau HA exige un code. Reste sur le serveur. |
| Code PIN Nuki (Keypad) | désactivé | PIN porte par séjour. **Indépendant** du déverrouillage Nuki dans Maison (`lock`). Décochez : le mail d'accueil part sans code porte. |
| Jeton Nuki Web API | vide | Créé sur [web.nuki.io](https://web.nuki.io) (API). Comme le code alarme : un champ mot de passe, vide = ne pas changer. |
| Identifiant smartlock | vide | Laissez vide s'il n'y a qu'une serrure. Sinon l'id numérique Nuki de la porte d'entrée. |

## Keypad Nuki

Ouvrir ou fermer la porte depuis Maison (`lock.unlock` / `lock.lock`) utilise l'entité Nuki déjà dans Home Assistant. Ça n'a pas besoin de Keypad ni de PIN.

Le **code PIN** est une option à part : un code par locataire, à taper sur le Keypad. Décochez **Code PIN Nuki (Keypad)** si vous n'avez pas (encore) de clavier : le mail d'accueil part quand même, sans code porte.

Pour les PIN :

1. Jumeler le Keypad dans l'app Nuki.
2. Sur [web.nuki.io](https://web.nuki.io) : créer un jeton API, le coller dans les options Usvegliu, cocher **Code PIN Nuki (Keypad)**.
3. Usvegliu crée un PIN 6 chiffres (1–9, jamais 0, ne commence pas par 12) dans la fenêtre d'avance, le met dans le mail J−2, Infos et la Console, et le retire à la **fin du jour de départ** (le Wi-Fi peut rester un jour de plus).

Le PIN n'est pas dans le CSV ni les logs. Airbnb peut déjà envoyer des codes Nuki de son côté : Usvegliu sert les réservations calendrier / directes.

Si Nuki ne répond pas, UniFi et le compte HA continuent. Le PIN est réessayé au cycle suivant ; le mail d'accueil n'attend le code que si l'option PIN est cochée et le jeton présent.

Un second passage avec les mêmes dates ne crée pas un deuxième voucher ni un deuxième compte. Au redémarrage, un voucher qui porte déjà le nom `<locataire> <arrivée>/<départ>` est réutilisé ; un doublon de ce nom est supprimé.

Nom du voucher : `Jean Dupont 2026-07-10/2026-07-17`. Les apostrophes sont retirées (le filtre UniFi `name.eq('…')` ne les supporte pas).

Séjour « journée entière » : la date de fin ICS est exclusive. Un événement du 10 au 17 est un départ le 17. Le lien Maison tient jusqu'à la fin de cette journée. Le voucher Wi-Fi est retiré le lendemain.

Le capteur **Code voucher** affiche le code du séjour en cours (sinon le prochain déjà créé, sinon `aucun`). Le capteur **Séjours actifs** liste tous les séjours encore ouverts (y compris avant l'arrivée, et un lien d'essai 24 h) : locataire, dates, identifiant HA, **mot de passe**, code Wi-Fi, code porte, lien Maison, tableau `/usvegliu-sejour`. Le code Wi-Fi et le code porte sont créés dès la fenêtre d'avance (3 jours) pour le message à envoyer. Avant le jour d'arrivée le compte HA est désactivé, et le lien Maison répond « s'ouvre le jour d'arrivée ». C'est la console propriétaire : fermer la notification persistante ne l'efface pas ; le départ ou l'annulation si. Un compte créé avant 0.5.3 n'a pas encore de mot de passe stocké : `usvegliu.regenerer_acces` en émet un et le pose sur le capteur. Ces deux capteurs ne sont pas dans la politique du locataire.

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

mDNS (`homeassistant.local`) ne traverse en général pas le VLAN invité. Donner aux locataires l'URL en **adresse IP** (`http://192.168.x.x:8123/usvegliu-sejour`), ou un nom DNS servi sur le hotspot.

## Accès Home Assistant des locataires

Pour chaque séjour (mode par défaut) :

- utilisateur **non propriétaire**, **non administrateur** ;
- un groupe `usvegliu-<identifiant>` propre à ce compte, pour que deux séjours ne partagent pas la même liste ;
- politique limitée aux entités et aux appareils choisis dans les options (ou à la surcharge du séjour). `read` et `control` seulement, pas `edit`, pas tout un domaine, pas `all` ;
- **local uniquement**, sauf si l'option d'accès internet est activée pour ce séjour ;
- au départ, à l'annulation ou au raccourcissement qui sort de la fenêtre : le compte est **supprimé** (mode par séjour) ou **retiré** (compte unique). L'accès internet s'arrête en même temps. Un changement d'options est réappliqué au cycle suivant, y compris aux séjours déjà ouverts.

Le sélecteur d'entités n'a pas de filtre de domaine. Le sélecteur d'appareils autorise toutes les entités de l'appareil, y compris celles ajoutées plus tard. Caméra, serrure et alarme (`camera`, `lock`, `alarm_control_panel`) ne sont pas proposées par défaut. Si vous les cochez, ou si un appareil en contient, l'enregistrement est refusé tant que la case de confirmation n'est pas cochée.

Surcharge par réservation : service `usvegliu.reglages_sejour`, avec l'attribut `reservation_id` du capteur (ou l'UID du calendrier). Les listes envoyées **remplacent** le réglage global pour ce séjour. `allow_remote` vaut `inherit`, `local` ou `remote`. `reset` revient au global. En mode compte unique, une seule session ne peut pas avoir deux politiques : c'est l'**union** des séjours actifs, et l'internet est ouvert si le global ou l'un de ces séjours l'autorise.

### Ce que le groupe restreint garantit

Vérifié dans le code de Home Assistant Core (branche `dev`, lu pour cette modification), pas exécuté sur la maison :

- `GET /api/states`, `GET /api/states/<entité>`, le websocket `get_states` et `subscribe_entities` ne renvoient que les entités pour lesquelles `check_entity(..., "read")` réussit. Un admin ou une politique `all` reçoit tout. Le compte locataire n'est ni l'un ni l'autre.
- Un appel de service **qui vise une entité** passe par `homeassistant/helpers/service.py` : sans droit `control` sur cette entité, Home Assistant lève `Unauthorized`.
- `POST /api/states/<entité>` (écrire un état à la main) est réservé aux administrateurs.
- L'historique (`history/history_during_period` et `/api/history/period`) filtre les entités demandées avec le même droit de lecture (correctif core #169236).

Ce que ça ne garantit pas :

- Le **journal** (`logbook/get_events`, `/api/logbook`) ne consulte pas `check_entity` dans le code examiné. Un locataire qui sait appeler cette API peut voir des événements d'autres entités. À retester sur la version installée ; ne pas y mettre de secrets.
- Les services **sans entité cible** (shell_command, rest_command, certains scripts) ne sont pas couverts par la politique, qui ne connaît que la catégorie `entities`. Ne sélectionnez pas un script ou une scène qui déverrouille une porte ou appelle un service large : une fois le script autorisé, son contenu s'exécute avec les droits de Home Assistant, pas avec ceux du locataire.
- `get_services` décrit tous les services. Les voir n'est pas les exécuter.
- Un appel **sans utilisateur** dans le contexte (automatisation) n'est pas filtré : ce n'est pas le locataire qui l'exécute.
- Cette lecture de code ne remplace pas un essai réel : ouvrir une session locataire et tenter une caméra non choisie, `/api/states`, un service `light.turn_on` sur une lumière absente de la liste, et le journal.

### Accès internet pendant le séjour

L'option est **désactivée par défaut**, globalement et pour chaque réservation (`inherit`). Si vous l'activez, `local_only` passe à faux **uniquement tant que le séjour est ouvert**, puis le compte est supprimé ou redevient local. Le module n'ajoute aucune redirection de port, aucun proxy et n'active pas Nabu Casa.

Home Assistant doit **déjà** être joignable de l'extérieur, par exemple :

- Home Assistant Cloud (Nabu Casa), ou
- un reverse proxy HTTPS que vous administrez déjà.

Mesures à avoir en place avant d'activer l'option : mot de passe fort (celui généré ici l'est), `http.ip_ban_enabled` et `login_attempts_threshold` dans la configuration HTTP, MFA du compte propriétaire, et aucun droit d'administration pour le locataire.

Le mot de passe est généré dans Home Assistant (`token_urlsafe`, sous la limite bcrypt de 72 octets). Le propriétaire le retrouve sur **Séjours actifs** et dans la notification. Il n'est pas écrit dans les logs, ni dans le CSV, ni dans les diagnostics. La web app Maison ne le voit pas. Pour en émettre un autre : `usvegliu.regenerer_acces`.

Tableau locataire : URL `usvegliu-sejour`, titre **Séjour**, visible des non-administrateurs, cartes thermostat / volets / éclairage. Accueil du compte locataire (`default_panel`).

Tableau propriétaire : URL `usvegliu-proprietaire`, titre **Console**. Visible des **administrateurs** et des comptes **Utilisateur** (droits de contrôle), pas des locataires. Quatre vues : **Accueil** (séjour **en cours** et **prochain**, raccourcis), **Séjours** (liste ordonnée, un clic ouvre la fiche), **Historique** (séjours clos et journal des accès, sans les codes), **Réglages**. La fiche d'un séjour contient le compte HA, le mot de passe, le Wi-Fi, le **code porte**, le **message à envoyer** et les actions. Le message à coller contient le lien personnel Maison, le réseau, le code Wi-Fi et le code Keypad s'il existe, dans une forme de politesse villa ; pas les identifiants Home Assistant. S'il y a une adresse et un SMTP, le même texte part par mail à J−2. Les identifiants sont lus en direct sur le capteur **Séjours actifs** (rien de secret dans le YAML Lovelace). Home Assistant masque l'attribut `password` : le mot de passe est exposé sous un autre nom pour rester visible. Si un séjour ancien n'a pas de mot de passe enregistré, **Nouveau mot de passe**.

L'intégration crée les deux tableaux si la collection Lovelace est joignable. Sinon : créer les URL `usvegliu-sejour` et `usvegliu-proprietaire` (tiret obligatoire) puis `usvegliu.appliquer_tableau`.

### Afficher la console propriétaire

Ce n'est **pas** le tableau **Séjour** (locataire) ni un tableau créé à la main sous un autre nom. Dans Home Assistant 2026, le bouton **+** des tableaux de bord ne reprend pas le titre comme URL : « Location » devient `dashboard-location`, donc l'intégration n'y écrit rien.

1. Mettre à jour Usvegliu ([0.6.30](https://github.com/nicdive/ha-mslumio-location/releases/tag/v0.6.30)+), redémarrer Home Assistant.
2. Outils de développement → Actions → `usvegliu.appliquer_tableau` → Exécuter.
3. Dans la barre latérale, ouvrir **Console**, ou l'URL `/usvegliu-proprietaire`.

Si **Console** n'apparaît toujours pas : Paramètres → Tableaux de bord → **+** → nouveau tableau vide. Titre `Usvegliu propriétaire` (Home Assistant génère alors l'URL `usvegliu-proprietaire`). **Ne pas** cocher « réservé aux administrateurs » (les comptes Utilisateur doivent la voir). Afficher dans la barre. Puis rappeler `usvegliu.appliquer_tableau`. Un tableau **Location** vide peut être supprimé.

Les locataires n'ont pas la Console dans la barre. Mettre les autres tableaux (vue d'ensemble, caméras, serrures) en **réservé aux administrateurs** si seul l'admin doit les voir. L'intégration ne le fait pas toute seule.

### Écran « Chargement des données… » après le mot de passe

Le formulaire peut accepter le mot de passe et rester ensuite sur le splash. Deux causes distinctes :

1. **Accueil Home Assistant.** HA 2026 ouvre le tableau Home (zones, toutes les entités). Un compte restreint y reste parfois bloqué. L'intégration pose maintenant **Séjour** comme tableau par défaut du locataire. Mettre à jour le composant, redémarrer, puis `usvegliu.regenerer_acces` (ou attendre le cycle de 15 min) pour l'écrire sur le compte déjà créé.
2. **Tailscale n'est pas « local ».** Home Assistant ne traite comme locales que les RFC1918 (`10/8`, `172.16/12`, `192.168/16`). Une IP Tailscale `100.64.0.0/10` est refusée pour un compte `local_only` **au websocket** (HA 2026.4+), pas forcément au formulaire. D'où un login « ok » puis un chargement infini sur `http://ha:8123`.

Pour un essai du **compte HA** depuis Tailscale : activer **Accès internet pendant le séjour**, enregistrer, puis `usvegliu.regenerer_acces`. Sur le VLAN hotspot de la villa (IP privée), laisser l'option coupée. Le **lien Maison** n'utilise pas ce compte : il fonctionne déjà sur `ha:8123` sans ce réglage.

Pas besoin d'assigner un groupe dans Paramètres → Personnes : l'intégration crée `usvegliu-<identifiant>` toute seule. La colonne Groupe de l'UI peut rester vide.

## Journal et Synology

Fichier CSV, une ligne par action (`voucher_cree`, `voucher_adopte`, `voucher_regenere`, `voucher_supprime`, `acces_cree`, `acces_regenere`, `acces_supprime`, `acces_desactive`, `code_porte_cree`, `code_porte_adopte`, `code_porte_regenere`, `code_porte_supprime`, `message_envoye`). Colonnes : horodatage, action, réservation, locataire, début, fin, id voucher, nom du voucher, **code voucher**, MAC si le contrôleur la renvoie, détail. Le schéma voucher v11.0.97 ne documente pas de MAC : la colonne reste vide tant qu'une réponse n'en contient pas (`macAddress`, `mac`, ou une liste de clients).

Pas de mot de passe, pas d'identifiant de connexion, pas de PIN Nuki. Un ancien fichier qui en contenait est réécrit sans ces colonnes à la prochaine ligne. Le code voucher reste dans le CSV : c'est le secret d'accès Wi-Fi à archiver. Le poser sur un partage Synology monté dans Home Assistant, par exemple :

- monter le partage dans `/media/synology` (ou sous `/config/...`) ;
- régler le chemin sur `/media/synology/usvegliu-sejour/journal.csv`.

Un chemin qui sort de la configuration et des dossiers média est refusé (`../etc/passwd` inclus). Aucun identifiant Synology n'est demandé : le montage est celui déjà fait par l'hôte.

L'événement `usvegliu_journal` reprend la même trace **sans** le code complet (deux derniers caractères seulement) et **sans** le mot de passe, pour ne pas le verser dans le journal et les traces.

Le magasin interne (`.storage/usvegliu.<entrée>`) est privé. Il sert à ne pas recréer les accès au redémarrage. Le CSV reste la copie à archiver.

## Notification et impression

À chaque nouveau code ou mot de passe : notification persistante `Usvegliu — <locataire>`. Un service `notify.…` optionnel reçoit le même texte (beaucoup de notifiers recopient le message dans le log : ne l'activer que si ce log reste privé). La notification peut être fermée : le capteur **Séjours actifs** (appareil Usvegliu) reste la liste de travail tant que le séjour est ouvert.

Le **mail locataire** est un autre service (`notify.smtp` typiquement). J−2 avant l'arrivée, Usvegliu y envoie le message d'accueil (lien Maison, SSID, code Wi-Fi, code porte s'il est activé) à l'adresse lue dans la description du calendrier. Les adresses des plateformes (Airbnb, Booking, Vrbo…) sont ignorées. Sans adresse ou sans SMTP, copiez le bloc **Message à envoyer** sur la Console. `usvegliu.renvoyer_notification` renvoie aussi ce mail, même avant J−2. Si le Keypad est activé, le mail attend que le PIN existe.

L'impression n'est pas faite par l'intégration. Service `usvegliu.imprimer_voucher` (ou la case « événement d'impression », désactivée par défaut) : événement `usvegliu_print_voucher` avec le code en clair, pour une automatisation qui imprime. Cet événement peut apparaître dans les traces d'automatisation. Le laisser désactivé si personne n'imprime.

## Services

Tous exigent un administrateur **ou** un compte Utilisateur (droits de contrôle) lorsque l'appel porte un utilisateur. Les locataires sont refusés. Une automatisation lancée sans utilisateur (contexte vide) passe.

| Service | Effet |
| --- | --- |
| `usvegliu.regenerer_voucher` | Nouveau code pour le séjour (l'ancien est supprimé). |
| `usvegliu.revoquer_voucher` | Supprime le code Wi-Fi jusqu'à régénération. |
| `usvegliu.regenerer_nuki` | Nouveau code porte Keypad (l'ancien est supprimé). |
| `usvegliu.revoquer_nuki` | Supprime le code porte jusqu'à régénération. |
| `usvegliu.regenerer_acces` | Nouveau mot de passe. |
| `usvegliu.revoquer_acces` | Supprime le compte HA jusqu'à régénération. |
| `usvegliu.renvoyer_notification` | Renvoie la notification propriétaire, et le mail d'accueil au locataire s'il a une adresse. |
| `usvegliu.reglages_sejour` | Surcharge les entités, les appareils et l'accès internet d'une réservation. |
| `usvegliu.imprimer_voucher` | Événement d'impression, réponse avec le code. |
| `usvegliu.exporter_journal` | Chemin du CSV. |
| `usvegliu.appliquer_tableau` | Réécrit **Séjour** et **Console**. |
| `usvegliu.relire_calendrier` | Relit le calendrier tout de suite (sinon cycle de 15 min). |

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
- Locataires : pas admin, pas owner, pas `system-users`. `local_only` sauf si l'accès internet du séjour est activé. Entités et appareils listés seulement.
- Aucune exposition Internet ajoutée. La règle de pare-feu est à créer sur l'UDM ; l'intégration ne pousse pas de règle firewall (elle ne touche pas à cette partie de l'API).
- Mots de passe absents des logs, du CSV, du stockage des séjours et des événements. Présents seulement dans la notification admin, le temps de la noter.
- Codes voucher dans le CSV et le capteur, masqués sur le bus. L'événement d'impression, s'il est activé, contient le code en clair.
- PIN Nuki : notification propriétaire, mail, Console et Infos. Absent du CSV, des logs et des diagnostics.
- Le capteur de code n'est pas dans la liste donnée au locataire, sauf si vous l'y ajoutez vous-même.

## Web app locataire

La web app **Maison** est servie par le même Home Assistant. Le locataire n'ouvre pas l'UI admin : un lien avec jeton suffit. L'interface est une application à sections (accueil, clim, pool, lumière, accès, infos), adaptée au téléphone et à l'iPad mini. Le bandeau reprend le logo **U Svegliu**.

- **Maison** : accueil nominatif, dates du séjour, météo du jour à Lumio, **véhicule** seulement s'il est branché (pictogramme de voiture, en charge, niveau, charge terminée). Si quelqu'un sonne, un popup avec la photo de la platine et *Ouvrir le portail*.
- **Clim** : thermostats autorisés (marche / arrêt, consigne, ventilation) ; titre **Chauffage** ou **Climatisation** selon le switch du propriétaire. Température extérieure en coin.
- **Pool** : température, pH, et lumière du bassin.
- **Lumière** : lumières (icône de lampe allumée / éteinte) et scénarios (à cocher dans les entités locataire).
- **Accès** : porte, garage, portail, alarme (armer / désarmer), volets, sonnette (état), borne de recharge (lecture), chacun avec un pictogramme. La photo visio est sur l'accueil, pas ici.
- **Son** : zones `media_player` (Amp Sonos) : volume, pause / lecture, muet, tout couper. L'onglet n'apparaît que si au moins une zone est cochée. Pas de Spotify / source de la villa.
- **Infos** : nom du réseau Wi-Fi, code voucher, code porte Keypad, et QR code du lien personnel Maison. Pas sur l'accueil.

Pour apparaître, chaque appareil doit d'abord exister dans Home Assistant, puis être dans **Entités autorisées** (alarme / serrure : cocher la case sensible, et renseigner le **code alarme** Delta Dore / TYDOM).

- **Borne** : OCPP, Modbus EVlink, Wallbox, etc. Cocher le capteur d'état et, s'il existe, le capteur de niveau (SOC %). Accueil : visible seulement si un véhicule est branché, avec un **pictogramme de voiture** (câble vers la borne), **En charge**, **Branché** ou **Charge terminée**, plus le % s'il est dans HA. L'onglet Accès garde aussi **Libre**. Pas de démarrage / arrêt de charge.
- **Alarme Delta Dore** : **Tydom 2** déjà en place. HACS *Delta Dore Tydom*, cocher `alarm_control_panel`, coller le code. L'app appelle `set_mode_using_stored_pin` si ce service existe.
- **Sonnette / visiophone** : sonnerie via `binary_sensor` / `event`. Popup accueil (photo + ouvrir le portail) si une `camera` (Linea 3000 / 300EOS) est cochée (case sensible). Parler reste sur le HomeTouch / 300EOS / app Home + Security.
- **Sonos Amp** : cocher les `media_player` des zones (salon, terrasse, piscine). Pas les TV. Le locataire règle le volume et coupe le son ; il lance sa musique depuis son téléphone (AirPlay / appli Sonos).

Le navigateur n'envoie que le jeton. Les commandes sont exécutées côté serveur après contrôle de la liste d'entités du séjour.

### Mode démo

Pour voir le rendu complet **avant** d'avoir branché thermostats, borne, alarme, etc. dans Home Assistant :

1. Appareil **Usvegliu** → allumer le switch **Mode démo**.
2. Ouvrir un lien Maison (`usvegliu.lien_maison` → essai 24 h, ou un séjour déjà provisionné).

L'app affiche alors 10 thermostats, le véhicule en charge, lumières, scènes, porte, garage, portail, volets, alarme, piscine, son, Infos. Les boutons réagissent (mémoire, rien n'est envoyé aux vrais appareils). Un bandeau **Mode démo** le rappelle. Éteindre le switch avant un vrai séjour.

### Configurer pour tester

1. Mettre à jour le custom component (redémarrer Home Assistant).
2. Options Usvegliu :
   - **Entités autorisées** : thermostats MH8 (`climate.…`), lumières MyHome, scènes, `cover` garage/portail, et si besoin `lock.…` Nuki plus `alarm_control_panel`.
   - **Switch chauffage / climatisation**, **température extérieure**, **piscine**, **pH** : lecture seule, à part des entités locataire.
   - Pour Nuki / alarme : cocher **J'autorise caméras, serrures ou alarmes**. Un **code alarme** éventuel reste côté serveur.
   - **URL publique de la web app** : laisser **vide** sur le HA de test. Réserver `https://www.usvegliu.fr` au reverse proxy de production.
3. Outils de développement → Services → `usvegliu.lien_maison` :
   - **Lien d'essai (24 h)** = oui, pour tester tout de suite sans événement calendrier ;
   - ou laisser vide pour le séjour en cours / le prochain déjà provisionné.
4. La réponse du service contient `url` et `path`. Une notification persistante affiche aussi le lien.
5. Ouvrir l'URL sur un téléphone **lui aussi sur Tailscale** (MagicDNS `ha` ne se résout que sur le tailnet) :
   - lab : `http://ha:8123/usvegliu/s/<token>` (`/s/<token>` marche aussi) ;
   - public, après proxy : `https://www.usvegliu.fr/s/<token>`.

Si l'URL locale de Home Assistant (Paramètres → Système → Réseau) est déjà `http://ha:8123`, `lien_maison` compose ce lien tout seul. Tailscale ne change rien au jeton ni à l'API : pas de compte HA, pas de certificat client. HTTPS seulement si ce HA de test l'a déjà activé.

Le lien d'essai expire au bout de 24 h. Un séjour calendrier a un jeton et un code Wi-Fi dès qu'il est provisionné (3 jours avant). Le lien Maison et le compte HA s'ouvrent le jour d'arrivée et s'arrêtent à la fin de la journée de départ. Le Wi-Fi reste un jour de plus.

### Reverse proxy (même machine)

La web app écoute sur Home Assistant :

| Chemin HA | Usage |
| --- | --- |
| `/usvegliu/s/<token>` | page locataire |
| `/usvegliu/static/` | CSS / JS |
| `/api/usvegliu/guest/state` | état (un coup) |
| `/api/usvegliu/guest/stream` | état en temps réel (SSE) |
| `/api/usvegliu/guest/climate` | commandes thermostat |
| `/api/usvegliu/guest/lock` | Nuki |
| `/api/usvegliu/guest/command` | lumières, scènes, bassin, garage, portail, alarme |
| `/api/usvegliu/guest/snapshot` | photo d'une caméra visio autorisée |

Exemple pour `https://www.usvegliu.fr/s/…` vers HA en local :

```nginx
location /s/ {
    proxy_pass https://127.0.0.1:8123/usvegliu/s/;
    proxy_set_header Host $host;
    proxy_ssl_verify off;
}
location /usvegliu/ {
    proxy_pass https://127.0.0.1:8123/usvegliu/;
    proxy_set_header Host $host;
    proxy_ssl_verify off;
}
location /api/usvegliu/ {
    proxy_pass https://127.0.0.1:8123/api/usvegliu/;
    proxy_set_header Host $host;
    proxy_ssl_verify off;
    proxy_buffering off;
    proxy_cache off;
}
```

Le premier essai peut se faire **sans** ce proxy, directement sur `http://ha:8123` (Tailscale).

## Développement

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent le client UniFi (contrôleur HTTP local, clé dans `X-API-KEY` et pas dans l'URL, repli de préfixe, pagination, 404, refus de redirection), le calcul des séjours, l'idempotence, l'adoption d'un voucher déjà nommé, l'annulation, le remplacement quand le séjour raccourcit, l'absence de révocation si le contrôleur ne répond pas, le PIN Keypad (création, révocation au départ Maison, panne Nuki sans bloquer UniFi), le CSV sans mot de passe ni PIN (y compris la réécriture d'un ancien fichier), le chemin de journal, la rédaction des diagnostics, la politique limitée aux entités choisies et l'avertissement caméra / serrure / alarme.

## Limites connues

- Horloge UniFi au premier usage du code, pas à l'arrivée. Un essai du code le jour de la création (J−3) consume trois jours. L'avance de création est réglable ; le jour supplémentaire ne compense pas un essai très anticipé.
- Schéma v11 non confirmé sur un UDM Pro Max de cette maison. HTTP 400 = s'arrêter et lire l'OpenAPI locale.
- Groupe locataire via une API interne de Home Assistant. À recontrôler après chaque montée de version majeure, y compris le filtrage du journal.
- Pas d'ACL sur les services sans entité ni, dans le code lu, sur le journal. Le test manuel locataire fait partie de la mise en service.
- L'accès internet n'est qu'un drapeau `local_only`. Sans Nabu Casa ou un proxy déjà en place, le locataire distant n'arrive pas. Tailscale (`100.x`, MagicDNS `ha`) n'est pas local pour ce drapeau : le formulaire peut passer, le websocket non.
- Les tableaux Lovelace ne sont créés que si la collection déjà chargée par HA est retrouvée. Sinon, création manuelle des URL `usvegliu-sejour` et `usvegliu-proprietaire`.
- Capteur de code : le séjour en cours, ou à défaut le prochain. Capteur **Séjours actifs** : tous les séjours encore ouverts, avec liens et mot de passe propriétaire. Pas dans le CSV.
- Compte partagé : un seul mot de passe pour les séjours qui se chevauchent.
- Pas de pilotage du portail captif, des conditions d'utilisation, ni du pare-feu UniFi.
- Les codes Keypad passent par l'API cloud Nuki (`api.nuki.io`). Sans internet ou sans jeton, le PIN n'est pas créé ; UniFi et HA continuent.
