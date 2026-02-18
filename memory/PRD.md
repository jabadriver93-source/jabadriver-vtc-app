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

### 14. START Idempotent + Safari Reliability ✅ [2026-02-16]
- **Problème PROD**: Le chauffeur clique "Démarrer", API renvoie 409, course reste "Attribuée"
- **Cause probable**: Double-fetch Safari, race condition, ou course déjà IN_PROGRESS
- **Corrections Backend (`/api/driver/ride/{id}/start`)**:
  - **START idempotent**: Si course déjà `IN_PROGRESS`, retourne **200 OK** avec `{ idempotent: true, status: "IN_PROGRESS" }` au lieu de 409
  - **Logs enrichis**: `[RIDE-START]` avec ride_id, current_status, auth_driver, auth_method, started_at
  - **Race condition résolue**: Si atomic update échoue mais course est IN_PROGRESS → retourne 200 OK
  - **Réponse 409 enrichie**: `{ error, current_status, expected_status, ride_id }`
- **Corrections Frontend (DriverCoursesPage.jsx)**:
  - **Debounce 2s**: `lastActionRef` empêche double-clic rapide
  - **Cache-buster**: `?_t=${Date.now()}` sur tous les appels
  - **Gestion idempotent**: Toast `info` si `idempotent: true`, sinon `success`

### 15. Diagnostic Email + Logs Améliorés ✅ [2026-02-16]
- **Nouveaux endpoints admin**:
  - `GET /api/admin/subcontracting/email-diagnostic` - Vérifie config SENDER_EMAIL, RESEND_API_KEY, FRONTEND_URL
  - `POST /api/admin/subcontracting/test-email-driver/{course_id}` - Envoie email test au chauffeur assigné
- **Logs [EMAIL-FLOW] enrichis** dans `finalize_attribution()`:
  - Log driver_found, course_found, driver_email, driver_access_token
  - Log SENDER_EMAIL, FRONTEND_URL, RESEND_API_KEY_present
  - Log `[1/3]`, `[2/3]`, `[3/3]` pour chaque email envoyé
- **Logs [EMAIL][ASSIGNED]** pour tracer le flux complet:
  - Attempting → RESEND_API_KEY present → ride_url → Sending → SUCCESS/FAILED avec resend_id

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
- **Bug Fix "unknown status": 100% (iteration_6.json)** [2026-02-16]
  - ✅ START button: ASSIGNED → IN_PROGRESS, toast "Course démarrée !"
  - ✅ END button: IN_PROGRESS → DRIVER_COMPLETED, toast "Course terminée !"
  - ✅ 409 handling: current_status lu correctement, plus de "unknown"
  - ✅ Status badge updates dynamiquement après action

---

## Prioritized Backlog

### P0 - Bugs Production (CRITIQUES)
- ⏳ **Email assignation chauffeur**: Investiguer les logs production `[EMAIL][ASSIGNED]`. Module fonctionnel en preview.

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

---

## Recent Updates [2026-02-17]

### 16. END Idempotent + Rate Limit Handling ✅ [2026-02-17]
- **Problème PROD**: Le bouton "Terminer la course" échouait avec erreur 409 similaire au START
- **Corrections Backend (`/api/driver/ride/{id}/end`)**:
  - **END idempotent**: Si course déjà `DRIVER_COMPLETED`, retourne **200 OK** avec `{ idempotent: true, status: "DRIVER_COMPLETED" }`
  - Même logique que START pour gérer les race conditions

### 17. Email Assignment - Rate Limit Handling ✅ [2026-02-17]
- **Problème PROD**: L'email d'attribution chauffeur n'était pas envoyé (429 Too Many Requests de Resend)
- **Corrections**:
  - **Variable d'environnement**: Utilisation de `SENDER_EMAIL_NEW` au lieu de `SENDER_EMAIL`
  - **Helper `send_email_with_retry()`**: Gestion automatique des erreurs 429 avec exponential backoff (3 tentatives max)
  - **Flag `assignment_email_sent`**: Évite les doublons d'email si la course est déjà marquée `ASSIGNED`
  - **Bouton admin "Tester email chauffeur"**: Pour debug en production, affiche le `resend_id` dans le toast

### 18. Unification Visuelle Documents Chauffeur ✅ [2026-02-17]
- **Objectif**: Cohérence visuelle parfaite entre portail chauffeur, page token, et PDF téléchargés
- **Logo JABADRIVER**:
  - Affiché en haut de la page token (`/driver/ride/{id}?token=xxx`)
  - Affiché en haut du portail chauffeur (`/driver/courses`)
  - Intégré dans les PDF générés (bon de commande et facture)
  - Largeur: ~240px, centré horizontalement, fond transparent
- **Module PDF unifié (`/app/backend/pdf_template.py`)**:
  - Utilise reportlab pour générer des PDF identiques au design frontend
  - Couleurs et espacements alignés avec le composant `DriverDocumentTemplate.jsx`
  - Sections: Logo → Header (titre/numéro) → Prestataire/Client → Détails course → Récapitulatif financier → Footer
  - Commission affichée uniquement sur le bon de commande (pas sur la facture)
- **Endpoints PDF**:
  - Token-based: `GET /api/driver/ride/{id}/bon-commande-pdf?token=xxx`
  - Token-based: `GET /api/driver/ride/{id}/invoice-pdf?token=xxx`
  - Session-based: `GET /api/driver/courses/{id}/bon-commande-pdf` (Auth Bearer)
  - Session-based: `GET /api/driver/courses/{id}/invoice-pdf` (Auth Bearer)
- **Helper `verify_driver_token_for_ride()`**: Fonction centralisée pour vérifier le token d'accès chauffeur
- **Test Results**: 100% (13/13 tests backend, tous tests frontend passés) - iteration_7.json

## Key Files Reference

### Backend
- `/app/backend/server.py` - Main FastAPI server
- `/app/backend/subcontracting.py` - Business logic, endpoints, email sending
- `/app/backend/pdf_template.py` - Unified PDF generation module (driver docs + platform commission invoice)
- `/app/backend/assets/jabadriver_logo.png` - Logo for driver documents (bon de commande, facture)
- `/app/backend/assets/logo_jabadriver_chauffeur.png` - Logo for platform commission invoice

### Frontend
- `/app/frontend/src/pages/driver/DriverRidePage.jsx` - Token-based ride page with logo
- `/app/frontend/src/pages/driver/DriverCoursesPage.jsx` - Driver portal with logo
- `/app/frontend/src/pages/admin/AdminSubcontractingPage.jsx` - Admin subcontracting with "Facture commission" button
- `/app/frontend/src/components/driver/DriverDocumentTemplate.jsx` - Unified document components
- `/app/frontend/public/jabadriver_logo.png` - Logo for frontend display

---

## Recent Updates [2026-02-17]

### 19. Facture Commission Plateforme (Jabadriver → Chauffeur) ✅ [2026-02-17]
- **Objectif**: Pouvoir générer une facture officielle Jabadriver → Chauffeur pour chaque commission payée
- **Endpoint**: `GET /api/admin/subcontracting/courses/{id}/platform-invoice-pdf` (admin only)
- **Bouton UI**: "Facture commission" (vert emerald) ajouté dans la carte course admin (visible quand chauffeur assigné)
- **PDF généré**:
  - **Logo**: JABADRIVER CHAUFFEUR (logo_jabadriver_chauffeur.png)
  - **Émetteur**: JABADRIVER - 49 boulevard Marc Chagall, 93600 Aulnay-sous-Bois - SIRET: 941 473 217 00011
  - **Client**: Nom chauffeur + Société + SIRET + Email
  - **Objet**: Commission de mise en relation — Course #{course_id}
  - **Montant**: Commission 10% du total course TTC
  - **TVA**: TVA non applicable — art. 293B du CGI
  - **Numéro facture**: JABA-{ANNÉE}-{COURSE_ID}
- **Séparation des flux**:
  - ✅ Facture chauffeur → client (existante, non modifiée)
  - ✅ Facture Jabadriver → chauffeur (NOUVEAU)
  - Commission JAMAIS affichée sur documents client
- **Non-régression confirmée**: START/END idempotent, Emails Resend, Factures chauffeur existantes, Token driver pages
- **Test Results**: 100% (13/13 backend, 100% frontend) - iteration_8.json

### 20. Corrections ciblées ✅ [2026-02-17]
- **Correction 1 - Infos société facture commission**:
  - JABADRIVER, 49 boulevard Marc Chagall, 93600 Aulnay-sous-Bois
  - SIRET: 941 473 217 00011
  - Visible dans `PLATFORM_INFO` de `/app/backend/pdf_template.py`

- **Correction 2 - Commission supprimée du bon de commande client**:
  - Le bon de commande (doc_type='bon') n'affiche JAMAIS la commission
  - Affiche uniquement: Prix course, Suppléments (péage, parking, attente), **Total TTC**
  - Logique: `show_commission_in_pdf = show_commission and doc_type not in ['bon', 'facture', 'facture_finale']`
  - La commission reste visible dans: Dashboard admin, Facture commission plateforme, Vue chauffeur (frontend)

- **Correction 3 - Email admin quand chauffeur termine course**:
  - Fonction: `send_ride_ended_to_admin()` utilisant `send_email_with_retry()` (retry 429 automatique)
  - **IDEMPOTENT**: Flag `end_admin_notification_sent` empêche les doublons
  - Sujet: "✅ Course terminée — #{course_id}"
  - Contenu: Client, Trajet, Date/Heure, Montant, Chauffeur, Commission, Lien admin
  - Logs: `[EMAIL-FLOW][ADMIN][RIDE-ENDED]`

- **Test Results**: 100% (20/20 tests) - iteration_9.json


### 21. Corrections UI/UX Mobile ✅ [2026-02-17]
- **Bouton Visible (Page Token Mobile)**:
  - Le bouton d'action fixe "Démarrer/Terminer la course" était masqué par la bannière "Made with Emergent"
  - **Fix**: `bottom-20` au lieu de `bottom-4` pour que le bouton reste au-dessus de la bannière
  - Testé sur viewport mobile (viewport iPhone)

- **Badge "Brouillon" masqué**:
  - Le badge de statut "Brouillon" apparaissait inutilement dans le portail chauffeur
  - **Fix**: Condition ajoutée pour exclure les factures en statut "DRAFT" de l'affichage du badge
  - Fichier: `/app/frontend/src/pages/driver/DriverCoursesPage.jsx`

- **"FACTURE PROVISOIRE" → "FACTURE"**:
  - Remplacement du texte sur tous les documents (frontend + PDF)
  - Fichiers: `DriverDocumentTemplate.jsx`, `pdf_template.py`

- **Bannière Statut Non-Bloquante**:
  - La bannière "Course terminée" recouvrait les boutons de téléchargement PDF
  - **Fix**: Déplacée dans le flux normal du document au lieu d'être en position absolue

### 22. Flux de Redirection Post-Login ✅ [2026-12-17]
- **Problème**: Un chauffeur non connecté cliquant sur `/claim/:token` était redirigé vers `/driver/courses` après login au lieu de revenir à la page `/claim/:token`
- **Solution robuste implémentée**:
  - **Module utilitaire**: `/app/frontend/src/lib/authRedirect.js`
    - `buildLoginRedirectUrl(targetPath)`: Construit l'URL de login avec paramètre redirect encodé
    - `storeRedirectTarget(path)`: Stocke la destination dans sessionStorage
    - `getPostLoginRedirect(searchParams)`: Récupère la destination (URL param > sessionStorage > default)
    - `getRedirectFromParams(searchParams)`: Décode le paramètre redirect
  - **ClaimPage.jsx**: Utilise `buildLoginRedirectUrl()` pour rediriger vers `/driver/login?redirect=%2Fclaim%2F{token}`
  - **DriverLoginPage.jsx**: Utilise `getPostLoginRedirect(searchParams)` après login réussi
- **Test Results**: 100% (4/4 tests frontend) - iteration_11.json
  - ✅ Unauthenticated user redirected to login with correct redirect param
  - ✅ Login with redirect param → redirected to claim page
  - ✅ Normal login without redirect → goes to /driver/courses
  - ✅ Full flow test passed

---

## Updated Backlog [2026-12-17]

### 27. Amélioration Dashboard Admin - Filtres & Stats ✅ [2026-12-18]

**Objectif** : Améliorer le dashboard admin avec des filtres par type de course et des statistiques financières agrégées.

**Fonctionnalités implémentées :**

1. **Filtre "Type de course"** :
   - Options : "Type de course" (toutes) / "🏠 Mes courses" (directes) / "🚚 Sous-traitées"
   - `data-testid="course-type-filter"`
   - Filtrage côté API avec paramètre `course_type`

2. **Statistiques CA en haut de page** :
   - Total CA avec répartition : 🏠 Direct + 🚚 Sous-traitées
   - Exemple : "🏠 1878€ + 🚚 265€ = 2143€"

3. **Badge prix avec indicateur type** :
   - Courses sous-traitées : Badge orange (bg-amber-400) avec emoji 🚚 et "+sup."
   - Courses directes : Badge bleu (bg-[#7dd3fc])

4. **API enrichie `/api/reservations`** :
   - Nouveau champ `is_subcontracted` (boolean)
   - Nouveau objet `financial_data` : 
     - `final_price_eur`, `base_price_eur`, `supplements_eur`
     - `commission_eur`, `driver_revenue_eur`

**Tests : 100% (iteration_16.json)**

**Fichiers modifiés :**
- `/app/frontend/src/pages/AdminDashboard.jsx`
- `/app/backend/server.py`

---

### 29. Unification Mode TEST Dashboard ↔ Sous-traitance ✅ [2026-12-18]

**Problème** : Le mode TEST n'était pas synchronisé entre le Dashboard (reservations) et la Sous-traitance (courses). Toggle d'un côté ne se reflétait pas de l'autre.

**Solution implémentée** :

1. **Filtre unifié** : Même logique `showTest ? item.is_test : !item.is_test` dans les deux pages
   - "Masquer tests" (défaut) = affiche SEULEMENT les normaux
   - "Afficher tests" = affiche SEULEMENT les tests

2. **Synchronisation bidirectionnelle** :
   - Toggle Dashboard → met à jour `is_test` sur la réservation ET la course liée
   - Toggle Sous-traitance → met à jour `is_test` sur la course ET les réservations liées

3. **Compteurs cohérents** :
   - Dashboard : compte les réservations test (actuellement 1)
   - Sous-traitance : compte les courses test (actuellement 7)

**Fichiers modifiés** :
- `/app/frontend/src/pages/AdminDashboard.jsx` : filtre corrigé (lignes 47, 148-159)
- `/app/backend/server.py` : toggle_test_reservation avec sync (ligne 1217)
- `/app/backend/subcontracting.py` : admin_toggle_test_course avec sync (ligne 5661)

**Tests : 100% (iteration_18.json)**
- 11/11 tests backend passés
- Sync vérifié : reservation 003c1efb ↔ course 511f5e99
- Aucune régression sur commission/pricing

---

### 30. Danger Zone - Reset Total Données Test ✅ [2026-12-18]

**Objectif** : Permettre à l'admin de supprimer toutes les données de test en une action sécurisée.

**Fonctionnalités** :
- Page `/admin/danger` avec preview des données à supprimer
- Bouton "Danger" rouge dans le header Dashboard
- Confirmation obligatoire `RESET-ALL-TEST`
- Variable d'environnement `ALLOW_DANGER_RESET=true` requise

**Suppression en cascade** :
1. commission_payments
2. activity_logs
3. claim_tokens
4. courses
5. reservations

**Préservé** : drivers, configuration, templates

**Endpoints** :
- `GET /api/admin/danger/reset-preview`
- `POST /api/admin/danger/reset-all`

**Tests : 100% (iteration_19.json)** - 15/15 backend

---

### P0 - Prochaine Priorité
- ⏳ **Système de Bonus / Parrainage Chauffeurs**: À implémenter

### Correction Flux Client Portal ✅ [2026-12-17]
- ✅ Lien email "Suivre mon chauffeur" corrigé (utilise client_portal_token)
- ✅ Statut client correct (current_status de la course)
- ✅ Bouton "Suivre mon chauffeur" avec GPS Google Maps
- ✅ Cache-Control Safari
- ✅ Tests 100% (iteration_13.json)

### Finalisation Workflow Course ✅ [2026-12-17]
- ✅ Bouton client "Je suis présent" fonctionne avec toast de succès
- ✅ Bouton chauffeur "Localiser client" visible après confirmation présence
- ✅ Injection automatique des frais d'attente dans la facture au START
- ✅ Message "Client confirmé" au lieu de "En attente de confirmation"
- ✅ Tests 100% (iteration_14.json)

### Correction Prix/Commission - Single Source of Truth ✅ [2026-12-18]
**Problèmes corrigés:**
- ❌ AVANT: Commission = 10% du total final (INCORRECT)
- ✅ APRÈS: Commission = 10% du prix de BASE uniquement

**Règles métier implémentées:**
1. `final_total = base_price + waiting_fee + extras`
2. `commission = 10% × base_price` (jamais sur total)
3. `waiting_minutes = ceil(seconds/60)` (toute minute entamée compte)

**Exemple validé:**
- Base: 54€, Attente 1min: 1€, Final: 55€
- Commission: 5.40€ (10% de 54€, PAS 5.50€)
- Net chauffeur: 49.60€

**Single Source of Truth:**
- Fonction `calculate_course_totals()` dans subcontracting.py
- Tous les écrans et PDFs utilisent ces valeurs

### Correction Admin Dashboard Classique ✅ [2026-12-18]
**Problèmes corrigés:**
1. ❌ AVANT: Prix carte = prix de base (54€ même avec suppléments)
   ✅ APRÈS: Prix carte = prix final (55€) avec indicateur "+sup."
   
2. ❌ AVANT: BDC/Facture toujours au nom Jabadriver
   ✅ APRÈS: BDC/Facture au nom du chauffeur si cours sous-traitée

**Fonctionnalités ajoutées:**
- Détail prix sur carte: "Base: 54€ + Attente (1min): 1€ = Total: 55€"
- Boutons conditionnels: "BDC (chauffeur)" / "Facture (chauffeur)"
- Nouveaux endpoints admin:
  - `GET /api/admin/subcontracting/courses/{id}/driver-bon-commande-pdf`
  - `GET /api/admin/subcontracting/courses/{id}/driver-invoice-pdf`

**Tests: 100% (iteration_15.json)**

**Fichiers modifiés:**
- `/app/backend/subcontracting.py`: calculate_course_totals(), calculate_waiting_price() avec ceil()
- `/app/backend/pdf_template.py`: calculate_totals() commission = base × 10%
- `/app/frontend/src/components/driver/DriverDocumentTemplate.jsx`: utilise totals API
- `/app/frontend/src/pages/admin/AdminSubcontractingPage.jsx`: affiche totals

**Nouveaux Endpoints:**
- `POST /api/client-portal/{token}/client-present` : Client signale sa présence

**Nouveaux Champs Retournés par `/api/driver/ride/{id}`:**
- `totals`: Objet complet avec base_price_eur, final_total_eur, commission_base_eur, net_driver_eur
- `confirmed_at`: Timestamp de confirmation client
- `client_present`, `client_present_time`, `client_lat`, `client_lng`

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



---

## Recent Updates [2026-02-17]

### 23. Système Chauffeur Arrivé + Compteur Attente ✅ [2026-02-17]

**Objectif** : Permettre au chauffeur de signaler son arrivée et facturer automatiquement le temps d'attente client.

**Nouveau Statut Course :**
- `DRIVER_ARRIVED` : Chauffeur arrivé au point de prise en charge, en attente du client
- `NO_SHOW` : Client absent après 20+ minutes d'attente

**Nouveaux Champs DB (collection `courses`) :**
- `arrival_time` : Horodatage serveur de l'arrivée chauffeur
- `arrival_lat`, `arrival_lng` : Coordonnées GPS du chauffeur à l'arrivée
- `client_present_time` : Horodatage quand le client signale sa présence
- `waiting_minutes` : Durée totale d'attente (calculée au démarrage)
- `waiting_billable_minutes` : Minutes facturables (après 5 min gratuites, max 20)
- `waiting_price` : Montant attente (1€/min, max 20€)
- `arrival_email_sent` : Flag idempotent pour l'email client

**Tarification Attente :**
- 0-5 min : GRATUIT
- 5-25 min : 1€/minute
- Maximum facturable : 20 minutes = 20€
- NO_SHOW (≥20 min) : Prix total de la course dû

**Nouveaux Endpoints Backend :**
- `POST /api/driver/ride/{id}/arrive` : Signaler arrivée (GPS requis)
- `GET /api/driver/ride/{id}/waiting-info` : Info attente temps réel
- `POST /api/driver/ride/{id}/client-present` : Client signale présence
- `POST /api/driver/ride/{id}/no-show` : Déclarer client absent (après 20 min)

**Flux des Statuts :**
```
ASSIGNED → (Je suis arrivé) → DRIVER_ARRIVED → (Démarrer) → IN_PROGRESS → ...
                                    ↓
                              (20 min attente)
                                    ↓
                              NO_SHOW (prix total dû)
```

**UI Chauffeur (DriverRidePage.jsx) :**
- Statut ASSIGNED : Bouton "🚗 Je suis arrivé" (bleu)
- Statut DRIVER_ARRIVED : 
  - Card compteur attente (temps, € facturables)
  - Bouton "Démarrer la course" (orange)
  - Bouton "Client absent" après 20 min (rouge)
- GPS demandé via HTML5 Geolocation API

**UI Client (ClientPortalPage.jsx) :**
- Alerte orange "Votre chauffeur est arrivé !"
- Compteur temps d'attente en temps réel
- Indicateur "Gratuit encore X min" / "Frais: X€"
- Bouton "✅ Je suis présent"
- Confirmation après clic

**Emails Automatiques :**
- `[EMAIL][ARRIVED][CLIENT]` : Email au client quand chauffeur arrive
- `[EMAIL][CLIENT_PRESENT][DRIVER]` : Email au chauffeur quand client arrive
- `[EMAIL][CLIENT_PRESENT][ADMIN]` : Email admin (info)
- Tous avec retry automatique (429 rate limit handling)

**Sécurité Anti-Fraude :**
- GPS obligatoire pour signaler arrivée (validation ≤200m désactivée si pas de coords stockées)
- Horodatage serveur obligatoire (pas l'heure téléphone)
- Endpoints idempotents (pas de double action)
- Plafond automatique 20€
- Logs visibles admin

**Test Results** : 100% backend (7 tests), 100% frontend - iteration_12.json

**Non-régression confirmée :**
- ✅ START/END existants fonctionnent
- ✅ START accepte ASSIGNED et DRIVER_ARRIVED
- ✅ Emails existants non impactés
- ✅ PDF et factures non impactés
- ✅ Commissions non impactées


### 24. Géocodification GPS et Validation Arrivée ✅ [2026-02-17]

**Objectif** : Stocker les coordonnées GPS des adresses et activer la validation de distance (200m max) pour le bouton "Je suis arrivé".

**Modifications Backend :**
- **`/api/calculate-route`** : Retourne maintenant `pickup_lat`, `pickup_lng`, `dropoff_lat`, `dropoff_lng` depuis Google Directions API
- **Modèle `CourseCreate`** : Nouveaux champs optionnels pour les coordonnées GPS
- **Modèle `Course`** : Nouveaux champs `pickup_lat`, `pickup_lng`, `dropoff_lat`, `dropoff_lng`
- **`POST /courses`** : Stocke les coordonnées GPS si fournies

**Modifications Frontend (AdminSubcontractingPage.jsx) :**
- Nouveau bouton "Calculer la distance" dans le formulaire de création de course
- Appelle `/api/calculate-route` avec les adresses départ/arrivée
- Remplit automatiquement le champ distance ET stocke les coordonnées GPS
- Indicateur "GPS validé" affiché quand les coordonnées sont disponibles

**Validation GPS Activée :**
- Si `pickup_lat` et `pickup_lng` sont présents dans la course :
  - Calcul de distance Haversine entre position chauffeur et adresse pickup
  - Si distance > 200m → Erreur "too_far" avec message explicatif
  - Si distance ≤ 200m → Arrivée acceptée
- Si pas de coordonnées → Validation ignorée (compatibilité anciennes courses)

**Tests Effectués :**
- ✅ Position trop loin (Lyon → Paris) : 393km → Rejeté
- ✅ Position exacte (0m) : Accepté
- ✅ Anciennes courses sans GPS : Validation ignorée

**Formule Haversine :**
```python
def haversine_distance(lat1, lng1, lat2, lng2) -> float:
    R = 6371000  # Earth radius in meters
    # ... calcul sphérique
    return distance_meters
```

**Constante de Configuration :**
```python
ARRIVAL_GPS_MAX_DISTANCE_METERS = 200
```


### 25. Autocomplétion Google Places Admin ✅ [2026-02-17]

**Objectif** : Ajouter l'autocomplétion d'adresses Google Places dans le formulaire admin pour garantir des coordonnées GPS précises.

**Modifications (AdminSubcontractingPage.jsx) :**
- Import du script Google Maps Places API (singleton pattern pour éviter les chargements multiples)
- Refs pour les champs d'adresse : `pickupInputRef`, `dropoffInputRef`
- Refs pour les instances Autocomplete : `pickupAutocompleteRef`, `dropoffAutocompleteRef`
- État `mapsReady` pour suivre le chargement de l'API

**Fonctionnement :**
1. Le script Google Maps est chargé au montage du composant
2. Quand le modal de création s'ouvre, les Autocomplete sont initialisés sur les champs d'adresse
3. Quand l'utilisateur sélectionne une suggestion :
   - L'adresse complète est mise à jour
   - Les coordonnées GPS sont extraites de `place.geometry.location`
   - Les champs `pickup_lat/lng` ou `dropoff_lat/lng` sont mis à jour automatiquement
4. Les coordonnées GPS sont affichées sous chaque champ d'adresse (ex: "GPS: 48.86946, 2.33142")

**Configuration Autocomplete :**
```javascript
new window.google.maps.places.Autocomplete(inputRef.current, {
  types: ["address"],
  componentRestrictions: { country: "fr" },
  fields: ["formatted_address", "geometry", "name"]
});
```

**UX Améliorée :**
- Placeholder "Commencez à taper une adresse..." pour guider l'utilisateur
- Indicateur GPS vert sous chaque champ quand les coordonnées sont disponibles
- Le bouton "Calculer la distance" reste disponible en fallback

**Variable d'environnement requise :**
```
REACT_APP_GOOGLE_MAPS_API_KEY=AIzaSy...
```



---

## Recent Updates [2026-12-17]

### 26. Correction Complète du Flux Client Portal ✅ [2026-12-17]

**Objectif** : Corriger les bugs majeurs du portail client (`/my-booking/{token}`) pour assurer un affichage cohérent du statut de course et un suivi chauffeur fonctionnel.

**Problèmes Corrigés :**

1. **Bug Lien Email "Suivre mon chauffeur"** :
   - **Problème** : L'email d'arrivée chauffeur utilisait `course.id` (UUID) au lieu du `client_portal_token`, causant une erreur 404.
   - **Fix** : La fonction `send_driver_arrived_to_client()` récupère maintenant le `client_portal_token` de la réservation liée.
   - **Fichier** : `/app/backend/subcontracting.py`

2. **Bug Statut Client Incorrect** :
   - **Problème** : Le client voyait "En cours" alors que la course était terminée (statut `reservation.status` au lieu du vrai statut course).
   - **Fix** : L'endpoint `/api/client-portal/{token}` retourne maintenant `current_status` (statut réel de la ride) et `display_status` (texte traduit).
   - **Fichier** : `/app/backend/server.py`

3. **Mapping Statuts pour Display** :
   ```
   ASSIGNED → "En attente chauffeur"
   DRIVER_ARRIVED → "Chauffeur arrivé"
   IN_PROGRESS → "En cours"
   DRIVER_COMPLETED / DONE → "Terminée"
   NO_SHOW → "Client absent"
   CANCELLED_* → "Annulée"
   ```

4. **Cache Safari** :
   - **Fix** : Header `Cache-Control: no-store, no-cache, must-revalidate` ajouté sur l'endpoint client-portal.
   - **Frontend** : Cache-busting avec `?_t=${Date.now()}` et `cache: 'no-store'` sur les fetch.

5. **Section "Suivre mon chauffeur"** :
   - **Nouveau** : Bouton bleu "🗺️ Suivre mon chauffeur" visible quand `status = DRIVER_ARRIVED` et coordonnées GPS disponibles.
   - **Action** : Ouvre Google Maps avec les coordonnées d'arrivée du chauffeur (`arrival_lat`, `arrival_lng`).

6. **Informations Chauffeur Enrichies** :
   - **Nouveau** : `assigned_driver_phone` retourné par l'API.
   - **UI** : Numéro de téléphone cliquable sous le nom du chauffeur.

**Nouveaux Champs Retournés par `/api/client-portal/{token}`** :
```json
{
  "current_status": "DRIVER_ARRIVED",    // Statut réel de la course
  "display_status": "Chauffeur arrivé",  // Texte traduit
  "assigned_driver_phone": "0698765432", // Téléphone chauffeur
  "arrival_time": "2026-02-17T21:56:57", // Heure d'arrivée
  "arrival_lat": 48.8795,                // GPS chauffeur
  "arrival_lng": 2.3553,
  "client_present_time": null,           // Présence client
  "waiting_minutes": 0,
  "waiting_price": 0.0
}
```

**Fichiers Modifiés** :
- `/app/backend/server.py` : Endpoint `/api/client-portal/{token}` enrichi
- `/app/backend/subcontracting.py` : Email d'arrivée avec bon token
- `/app/frontend/src/pages/ClientPortalPage.jsx` : UI avec `realStatus`, bouton suivi, badge dynamique

**Non-Régression Confirmée** :
- ✅ Portail modification client fonctionne
- ✅ Bouton "Je suis présent" fonctionne
- ✅ Emails existants non impactés
- ✅ Workflow chauffeur non impacté

