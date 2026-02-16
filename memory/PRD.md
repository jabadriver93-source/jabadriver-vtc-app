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
- **Emails**:
  - Attribution: Email au chauffeur avec bouton "VOIR LA COURSE"
  - Start: Email au client + admin (course démarrée)
  - End: Email au client avec bouton "CONFIRMER MA COURSE"
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

## Technical Implementation

### Backend (FastAPI)
- **Modèle Driver**: Champs obligatoires (company_name, address, siret, vat_mention, driver_code)
- **Modèle Course**: Nouveaux champs (invoice_status, invoice_number, supplements, is_test, driver_access_token, started_at, ended_at, client_confirmation_token, confirmed_at)
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

## Non-Regression Confirmed
- ✅ Paiement Stripe inchangé
- ✅ Système de claim chauffeur inchangé
- ✅ Commission 10% inchangée
- ✅ Layout mobile préservé
- ✅ Environnements preview/production identiques
- ✅ Numérotation factures préservée

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
