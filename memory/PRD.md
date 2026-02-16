# JABADRIVER - Module de Sous-traitance VTC

## Original Problem Statement
Application VTC (Jabadriver) avec un module de sous-traitance permettant aux chauffeurs de recevoir des courses et de gérer leur facturation.

## Core Requirements - IMPLEMENTED

### 1. FACTURATION - Courses Attribuées ✅
- **Émetteur = Chauffeur**: Le BDC et la Facture sont émis au nom du chauffeur (pas Jabadriver)
- **Informations chauffeur affichées**:
  - Raison sociale / Nom commercial
  - Adresse professionnelle
  - SIRET
  - Mention TVA (ex: "TVA non applicable – art. 293 B du CGI")
- **Pied de page Jabadriver**: Texte légal indiquant que Jabadriver est intermédiaire technique

### 2. Numérotation Factures ✅
- **Format**: `{DRIVER_CODE}-{ANNÉE}-{SEQUENCE}` (ex: DR01-2026-001)
- **Compteur indépendant par chauffeur**: Chaque chauffeur a sa propre séquence
- **Séquence continue et chronologique**
- **Code chauffeur auto-généré**: Format DR01, DR02, etc.

### 3. Workflow Facture (DRAFT → ISSUED) ✅
- **DRAFT**: Facture modifiable (suppléments possibles)
- **ISSUED**: Facture figée, plus aucune modification possible
- **Seul le chauffeur peut émettre la facture**

### 4. Suppléments Chauffeur ✅
- Péage (montant libre)
- Parking (montant libre)
- Attente (calcul automatique: 0,50€/minute)
- **Bloqués après émission facture**

### 5. Modification Client (Page Token) ✅
- **Autorisée si**: invoiceStatus ≠ ISSUED
- **Champs modifiables**: Adresse départ/arrivée, Date, Heure, Passagers
- **Recalcul automatique**: 1,50€/km + 0,50€/min
- **Notifications**: Email admin + Email chauffeur
- **BDC auto-mis à jour**
- **Bloquée après émission facture**

### 6. Email Attribution Client ✅
- Email envoyé au client avec infos chauffeur lors de l'attribution
- Mention que toute modification entraîne un recalcul automatique

### 7. Filtre Courses de Test (isTest) ✅ [2026-02-15]
- **Champ is_test**: Boolean sur le modèle Course (défaut: false)
- **Endpoint toggle**: `POST /api/admin/subcontracting/courses/{id}/toggle-test`
- **Exclusion des stats**: Les courses test sont exclues du total_commission
- **UI Admin**:
  - Badge TEST orange visible sur les courses test
  - Bouton "Mode Test" / "Test" pour basculer le flag
  - Contour orange sur les cartes de courses test
  - Indicateur "(test)" à côté du prix
- **Page Commissions**:
  - Badge "COURSE TEST" visible
  - Montant barré pour les paiements liés à des courses test
- **Aucune suppression de données**: Les courses test restent dans la base

### 8. Correction Autocomplétion Google Places - Page Token ✅ [2026-02-15]
- **Problème**: L'autocomplétion d'adresses ne fonctionnait pas sur la page de modification client (`/my-booking/:token`)
- **Cause**: Variable d'environnement incorrecte (`REACT_APP_PUBLIC_GOOGLE_MAPS_API_KEY` au lieu de `REACT_APP_GOOGLE_MAPS_API_KEY`)
- **Correction**: Alignement avec `BookingPage.jsx` pour utiliser la bonne variable d'env
- **Comportement actuel**:
  - Suggestions Google Places apparaissent après 3+ caractères
  - Sélection d'une suggestion remplit le champ d'adresse
  - Recalcul automatique du prix déclenché après sélection
  - Compatible mobile (testé sur viewport iPhone)

### 9. Driver Ride Workflow avec Liens Directs ✅ [2026-02-16]
- **Token d'accès direct**: `driver_access_token` généré lors de l'attribution de la course
- **Lifecycle des statuts**: `ASSIGNED → IN_PROGRESS → DRIVER_COMPLETED → DONE`
  - `ASSIGNED`: Course attribuée au chauffeur
  - `IN_PROGRESS`: Course démarrée par le chauffeur
  - `DRIVER_COMPLETED`: Course terminée par le chauffeur, en attente de confirmation
  - `DONE`: Course clôturée (admin confirme)
- **Route**: `/driver/ride/:rideId?token=xxx`
- **Endpoints**:
  - `GET /api/driver/ride/{ride_id}?token` - Détails course (sans login)
  - `POST /api/driver/ride/{ride_id}/start?token` - Démarrer course
  - `POST /api/driver/ride/{ride_id}/end?token` - Terminer course
- **Page DriverRidePage (mobile-first)**:
  - Badge statut dynamique
  - **Timeline** avec timestamps (Attribuée, Démarrée, Terminée, Confirmée)
  - Infos: date/heure, client (nom + tél clickable), adresses
  - Récapitulatif financier (gain net)
  - **Boutons Communication**: Appeler (tel:), WhatsApp (wa.me/)
  - **Boutons Navigation GPS**: Google Maps, Waze (destination dynamique selon statut)
    - ASSIGNED: Navigation vers point de prise en charge (pickup)
    - IN_PROGRESS: Navigation vers destination (dropoff)
  - Bouton principal: "Démarrer" (ASSIGNED) ou "Terminer" (IN_PROGRESS)
  - Boutons PDF: Bon de commande, Facture
- **Dashboard Chauffeur (DriverCoursesPage)** - Source de vérité unique:
  - Actions START/END directes depuis le dashboard (sans navigation vers DriverRidePage)
  - Boutons d'action selon statut:
    - ASSIGNED → "Démarrer la course" (appel API direct)
    - IN_PROGRESS → "Terminer la course" (appel API direct)
    - DRIVER_COMPLETED → "Attente confirmation" (désactivé)
    - DONE → Pas de bouton d'action
  - **Safari iOS fix**: `safeReadJson()` pour lire le body une seule fois
  - **Cache-busting**: `?_t=${Date.now()}` + headers `Cache-Control: no-store`
  - **Fetch options**: `cache: 'no-store'` pour Safari
  - Logs console: `[COURSES]`, `[ACTION]`, avec statut et current_status en 409
- **Logs Email [EMAIL-FLOW]**:
  - Log détaillé à chaque étape de l'envoi d'email assignation
  - `driver_email`, `FRONTEND_URL`, `RESEND_API_KEY_present`, `resend_id` ou erreur
- **Emails**:
  - Attribution: Email au chauffeur avec bouton "VOIR LA COURSE" (lien avec token)
  - Start: Email au client + admin (course démarrée)
  - End: Email au client avec bouton "CONFIRMER MA COURSE"
- **Configuration requise**:
  - `FRONTEND_URL` dans backend/.env pour les liens d'email
- **Sécurité**:
  - Token valide jusqu'à status = DONE
  - Seul le chauffeur assigné peut agir
  - Protection double-action

### 10. Confirmation Client après Fin de Course ✅ [2026-02-16]
- **Workflow**: Chauffeur termine → Client reçoit email → Client confirme → Course validée
- **Token**: `client_confirmation_token` généré à la fin de course
- **Route Frontend**: `/confirm-ride/:rideId?token=xxx`
- **Endpoints**:
  - `GET /api/driver/confirm-ride/{ride_id}?token` - Détails pour confirmation
  - `POST /api/driver/confirm-ride/{ride_id}?token` - Confirmer la course
- **Page ConfirmRidePage (mobile-first)**:
  - Récapitulatif course avec timeline
  - Infos chauffeur, adresses, prix
  - Bouton vert "Confirmer ma course"
  - Écran de succès après confirmation
- **Après confirmation**:
  - Status → DONE
  - Tokens invalidés (driver + confirmation = null)
  - Email admin "Course confirmée"

### 11. Boutons Navigation et Communication - DriverRidePage ✅ [2026-02-16]
- **Navigation GPS** (mobile-first, détection auto du contexte):
  - Google Maps: `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`
  - Waze: `https://waze.com/ul?ll={lat},{lng}&navigate=yes`
  - Fallback vers adresse textuelle si coordonnées absentes
  - **Destination dynamique**: Pickup (ASSIGNED) → Dropoff (IN_PROGRESS)
- **Communication Client**:
  - Appeler: `tel:{phone}` - Ouvre téléphone natif
  - WhatsApp: `https://wa.me/{phone}` - Ouvre WhatsApp
- **UX Mobile**: Boutons larges (h-12/h-14), feedback tactile (active:scale-95)
- **Aucune régression** sur le workflow existant (Start/End/Confirm)

### 12. Sécurité et Anti-Double-Action - Driver Ride Workflow ✅ [2026-02-16]
- **Double authentification (Token OU Session)**:
  - Token URL (`?token=xxx`): Pour accès direct depuis email
  - Session JWT (`Authorization: Bearer xxx`): Pour chauffeur connecté
  - Le chauffeur assigné peut utiliser les deux méthodes
- **Protection Backend**:
  - Vérification chauffeur assigné (assigned_driver_id)
  - Anti-double-action via `started_at`/`ended_at` check
  - Requêtes atomiques MongoDB (prevent race conditions)
  - HTTP 409 Conflict pour actions dupliquées
- **Champs d'audit ajoutés**:
  - `started_by_driver_id`: ID du chauffeur ayant démarré
  - `ended_by_driver_id`: ID du chauffeur ayant terminé
- **Logging sécurité**:
  - `[RIDE-AUTH]` pour mode d'authentification utilisé
  - `[RIDE-SECURITY]` pour tentatives invalides
- **Protection Frontend**:
  - `isActionDisabled` state pour bloquer double-clics
  - Boutons désactivés pendant chargement
  - Messages d'erreur détaillés (HTTP 409 → "Course déjà démarrée/terminée")
  - Support dual auth (token URL ou session localStorage)

## Technical Implementation

### Backend (FastAPI)
- **Modèle Driver**: Champs obligatoires (company_name, address, siret, vat_mention, driver_code)
- **Modèle Course**: Nouveaux champs (invoice_status, invoice_number, supplements, is_test, driver_access_token, started_at, ended_at, started_by_driver_id, ended_by_driver_id, client_confirmation_token, confirmed_at)
- **Statuts Course**: OPEN, RESERVED, ASSIGNED, IN_PROGRESS, DRIVER_COMPLETED, DONE, CANCELLED, CANCELLED_LATE_*
- **Routes**:
  - `PATCH /api/driver/courses/{id}/supplements` - Ajout suppléments
  - `POST /api/driver/courses/{id}/issue-invoice` - Émission facture
  - `GET /api/driver/courses/{id}/invoice-status` - Statut facture
  - `POST /api/client-portal/{token}/modify-direct` - Modification directe client
  - `GET /api/calculate-route` - Calcul itinéraire Google Maps
  - `POST /api/admin/subcontracting/courses/{id}/toggle-test` - Bascule mode test
  - `GET /api/driver/ride/{ride_id}?token` - Détails course (accès direct token)
  - `POST /api/driver/ride/{ride_id}/start?token` - Démarrer course
  - `POST /api/driver/ride/{ride_id}/end?token` - Terminer course
  - `GET /api/driver/confirm-ride/{ride_id}?token` - Détails pour confirmation client
  - `POST /api/driver/confirm-ride/{ride_id}?token` - Confirmer la course

### Frontend (React)
- **DriverLoginPage**: Formulaire inscription avec champ "Mention TVA *"
- **DriverCoursesPage**: Gestion suppléments, émission facture, badges statut
- **DriverRidePage**: Page mobile-first accès direct par token, timeline, boutons Start/End
- **ConfirmRidePage**: Page confirmation client mobile-first avec timeline et bouton confirmer
- **ClientPortalPage**: Modification directe, affichage blocage si facture émise
- **AdminSubcontractingPage**: Bouton toggle test, badge TEST, statuts IN_PROGRESS/DRIVER_COMPLETED
- **AdminCommissionsPage**: Badge COURSE TEST, montant barré pour courses test

### PDF Generation (ReportLab)
- **Bon de Commande**: Émetteur = Chauffeur, pied de page Jabadriver
- **Facture**: Émetteur = Chauffeur, suppléments détaillés, pied de page Jabadriver

### 13. Bug Fix: "Course déjà en statut: unknown" ✅ [2026-02-16]
- **Problème**: Sur iPhone/Safari, le message "Course déjà en statut: unknown" s'affichait même après un succès (200 OK)
- **Cause**: Le frontend lisait `data?.current_status || 'unknown'` sans vérifier d'abord si la requête avait réussi
- **Correction Frontend (DriverCoursesPage.jsx)**:
  - Ordre de vérification: 401 (logout) → 409 (conflit) → !ok (autre erreur) → success
  - Pour succès 200: Lire `data?.status` (ex: "IN_PROGRESS", "DRIVER_COMPLETED")
  - Pour conflit 409: Lire `data?.current_status || data?.status`
  - Log détaillé avec `[ACTION] ✅ Start SUCCESS` ou `[ACTION] 409 Conflict`
- **Backend confirmé OK**: Retourne `{ success: true, status: "IN_PROGRESS", ... }` en 200

### 14. Bug Investigation: Email d'assignation chauffeur ⏳ [2026-02-16]
- **Problème signalé**: Le chauffeur ne reçoit pas l'email "VOIR LA COURSE" après attribution
- **Investigation**:
  - Configuration SENDER_EMAIL correctement passée au module subcontracting ✅
  - Fonction `send_course_assigned_to_driver` fonctionnelle en test ✅
  - Autres emails (ride_started, ride_ended) envoyés avec succès ✅
  - Logs `[EMAIL-FLOW]` et `[EMAIL][ASSIGNED]` implémentés ✅
- **Statut**: Module email fonctionnel en preview. Si bug persiste en prod, vérifier:
  1. Logs production pour `[EMAIL][ASSIGNED]`
  2. SENDER_EMAIL et RESEND_API_KEY en production
  3. Rate limit Resend (2 req/sec)
- **Note**: Le flux d'assignation (après paiement commission) n'a pas pu être testé de bout en bout car il nécessite un vrai paiement Stripe

## Non-Regression Confirmed
- ✅ Paiement Stripe inchangé
- ✅ Système de claim chauffeur inchangé
- ✅ Commission 10% inchangée
- ✅ Layout mobile préservé
- ✅ Environnements preview/production identiques
- ✅ Numérotation factures préservée
- ✅ Workflow START/END fonctionne sur Safari iOS (après fix cache-busting et safeReadJson)

## Test Credentials
- **Chauffeur**: nouveau.chauffeur@test.com / test123
- **Admin**: admin / admin123

## Test Results
- Backend: 17/17 tests passés (100%)
- Frontend: Tous les flux vérifiés
- Feature isTest: 89% backend (8/9), 100% frontend
- Autocomplétion Google Places: 100% (desktop + mobile) [2026-02-15]
- Driver Ride Workflow: 100% backend (13/13), 100% frontend [2026-02-16]
- Client Confirmation: 100% backend (11/11), 100% frontend [2026-02-16]
- Navigation/Communication Buttons: 100% frontend (vérifié ASSIGNED + IN_PROGRESS) [2026-02-16]
- Security/Anti-Double-Action: 100% backend + frontend [2026-02-16]
  - ✅ Double-start rejected (HTTP 409)
  - ✅ Double-end rejected (HTTP 409)
  - ✅ Invalid token rejected (HTTP 403)
  - ✅ Audit fields stored (started_by_driver_id, ended_by_driver_id)
  - ✅ Security logs generated

---

## Prioritized Backlog

### P1 - Dashboard Statistiques Admin
- Tableau de bord avec statistiques (courses, revenus, chauffeurs)
- Graphiques d'évolution

### P2 - Améliorations
- Notifications push chauffeurs
- Chat en temps réel
- Historique des commissions

### P3 - Backlog
- Application mobile native
- Intégration GPS temps réel

### P4 - Connu mais non prioritaire
- Correction icône PWA chauffeur (problème mineur)
