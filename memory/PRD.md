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

### 7. Filtre Courses de Test (isTest) ✅ [NEW - 2026-02-15]
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

## Technical Implementation

### Backend (FastAPI)
- **Modèle Driver**: Champs obligatoires (company_name, address, siret, vat_mention, driver_code)
- **Modèle Course**: Nouveaux champs (invoice_status, invoice_number, supplements, is_test)
- **Routes**:
  - `PATCH /api/driver/courses/{id}/supplements` - Ajout suppléments
  - `POST /api/driver/courses/{id}/issue-invoice` - Émission facture
  - `GET /api/driver/courses/{id}/invoice-status` - Statut facture
  - `POST /api/client-portal/{token}/modify-direct` - Modification directe client
  - `GET /api/calculate-route` - Calcul itinéraire Google Maps
  - `POST /api/admin/subcontracting/courses/{id}/toggle-test` - Bascule mode test

### Frontend (React)
- **DriverLoginPage**: Formulaire inscription avec champ "Mention TVA *"
- **DriverCoursesPage**: Gestion suppléments, émission facture, badges statut
- **ClientPortalPage**: Modification directe, affichage blocage si facture émise
- **AdminSubcontractingPage**: Bouton toggle test, badge TEST, indicateur prix test
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
