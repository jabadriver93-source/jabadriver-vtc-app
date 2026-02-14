# JABADRIVER - Module de Sous-traitance VTC

## Original Problem Statement
Application VTC complète avec un module de sous-traitance permettant :
- À l'admin de générer des liens de "claim" sécurisés pour les courses
- Aux chauffeurs partenaires de réclamer les courses en payant une commission de 10% via Stripe
- Génération manuelle de PDF (bon de commande, facture) au nom du chauffeur

## Core Requirements

### Module de Sous-traitance
- ✅ Réservation client → création automatique d'une course "OPEN" en sous-traitance
- ✅ Génération de lien claim sécurisé avec token unique
- ✅ Réservation temporaire de 3 minutes pour le chauffeur
- ✅ Paiement de commission 10% via Stripe (SDK natif)
- ✅ Attribution définitive après paiement confirmé (webhook Stripe)
- ✅ Génération manuelle de PDF (bon de commande, facture)

### Rôles et Authentification
- ✅ Rôle ADMIN : gestion complète des réservations et chauffeurs
- ✅ Rôle DRIVER : inscription, connexion, profil légal, claim de courses
- ✅ Validation des chauffeurs par admin avant activation

### Sécurité
- ✅ Anonymisation des données sensibles sur la page claim (avant paiement)
- ✅ Seuls nom client, prix, date/heure et villes visibles (pas adresses complètes)

### Emails
- ✅ Email confirmation client (sans PDF)
- ✅ Email admin "Nouvelle réservation" avec lien claim
- ✅ Bouton "Partager via WhatsApp" dans l'email admin
- ✅ Email admin "Nouveau chauffeur inscrit" avec bouton validation
- ✅ Email admin "Course attribuée" après paiement commission
- ✅ Email chauffeur "Compte validé" après activation par admin
- ✅ Email chauffeur "Dossier reçu" après inscription (liste des pièces à fournir)
- ✅ Bouton "Gérer ma réservation" dans email confirmation client (NEW)

### Gestion des Annulations (NEW)
- ✅ Annulation chauffeur tardive (< 1h) : flag, compteur, commission non remboursée
- ✅ Annulation client tardive (< 1h) : statut spécifique, traçabilité
- ✅ Statuts : CANCELLED_LATE_DRIVER, CANCELLED_LATE_CLIENT
- ✅ Bouton "Annuler la course" dans l'espace chauffeur (DriverCoursesPage.jsx)
  - Visible uniquement pour les courses avec statut ASSIGNED
  - Modale de confirmation avec avertissement si annulation tardive (< 1h)
  - Appel API POST /api/driver/courses/{course_id}/cancel
  - Toast de succès/erreur + rafraîchissement de la liste
  - Désactivation automatique après 3 annulations tardives

### Portail Client Léger (NEW)
- ✅ Accès via token sécurisé `/my-booking/{token}`
- ✅ Voir sa réservation
- ✅ Envoyer un message à l'admin
- ✅ Demander modification
- ✅ Demander annulation
- ✅ Sans création de compte

### Sécurité & Qualité (NEW)
- ✅ Flag client abusif (`is_abusive_client`)
- ✅ Compteur annulations tardives chauffeur (`late_cancellation_count`)
- ✅ Journal d'activité (collection `activity_logs`)
- ✅ Logs : attribution, annulations, changements statut, messages client

### Administration
- ✅ Page historique des commissions /admin/commissions (NEW)
  - Tableau détaillé avec filtres (date, chauffeur, statut, mode test/live)
  - Total des commissions sur la période
  - Export CSV

## Tech Stack
- **Backend:** FastAPI, Motor (MongoDB async), ReportLab (PDF), Resend (emails)
- **Frontend:** React, TailwindCSS, Shadcn UI
- **Paiement:** Stripe SDK Python natif
- **Database:** MongoDB

## Key API Endpoints
- `POST /api/reservations` - Création réservation + course sous-traitance
- `POST /api/driver/register` - Inscription chauffeur (+ email admin)
- `POST /api/driver/login` - Connexion chauffeur
- `GET /api/subcontracting/claim/{token}` - Infos course à réclamer
- `POST /api/subcontracting/claim/{token}/reserve` - Réservation 3 min
- `POST /api/subcontracting/claim/{token}/initiate-payment` - Session Stripe
- `POST /api/subcontracting/stripe-webhook` - Confirmation paiement
- `POST /api/admin/subcontracting/drivers/{id}/activate` - Activer chauffeur (+ email)
- `GET /api/admin/subcontracting/commissions` - Historique commissions (NEW)
- `GET /api/admin/subcontracting/commissions/export-csv` - Export CSV (NEW)

## What's Been Implemented

### 2025-02-15 (Session 3)
- ✅ Bouton "Annuler la course" dans l'espace chauffeur finalisé
  - Apparaît uniquement pour les courses status=ASSIGNED
  - Modale de confirmation avec avertissement annulation tardive (< 1h)
  - Appel API /api/driver/courses/{course_id}/cancel
  - Refresh automatique de la liste après annulation
  - Gestion des toasts (succès, warning tardive, erreur)
- ✅ Compteur d'annulations tardives visible
  - **Admin** : Badge coloré X/3 dans la liste des chauffeurs (vert=0, orange=1-2, rouge=3)
  - **Chauffeur** : Section dans le profil avec compteur et avertissement
  - **Emails automatiques** : Avertissement à 1 et 2 annulations, désactivation à 3

### 2025-02-13 (Session 2)
- ✅ Email admin automatique quand course attribuée après paiement commission
  - ID réservation, trajet, prix, commission, infos chauffeur, PaymentIntent Stripe
- ✅ Email chauffeur automatique quand compte validé par admin
  - Message de bienvenue, explication du fonctionnement, lien espace chauffeur
- ✅ Page /admin/commissions - Historique des commissions encaissées
  - Tableau complet avec toutes les infos de paiement
  - Filtres par période, chauffeur, statut, mode test/live
  - Total des commissions sur la période filtrée
  - Export CSV
  - Bouton d'accès depuis la page admin sous-traitance

### 2025-02-13 (Session 1)
- ✅ Bouton "Partager via WhatsApp" dans l'email admin (nouvelle réservation)
- ✅ Email automatique à l'admin lors de l'inscription d'un nouveau chauffeur

### Previous Sessions
- Module sous-traitance complet (subcontracting.py)
- Intégration Stripe fonctionnelle
- Interface admin et espace chauffeur
- Corrections UI/UX mobile
- Bug fix URLs production

## Architecture Files
```
/app/backend/
├── server.py           # Routes principales, emails, PDF
├── subcontracting.py   # Module sous-traitance isolé
└── .env                # Config (Stripe, Resend, MongoDB)

/app/frontend/src/
├── pages/
│   ├── BookingPage.jsx
│   ├── ClaimPage.jsx
│   ├── AdminDashboard.jsx
│   ├── admin/
│   │   ├── AdminSubcontractingPage.jsx
│   │   └── AdminCommissionsPage.jsx  # NEW
│   └── driver/
│       ├── DriverLoginPage.jsx
│       ├── DriverCoursesPage.jsx
│       └── DriverProfilePage.jsx
└── App.js
```

## Test Credentials
- **Admin:** admin / admin123
- **Driver (test):** chauffeur1@test.com / test123

## Backlog / Future Tasks
- P1: Dashboard statistiques admin avancées
- P2: Notifications push chauffeurs (optionnel)
- P3: Chat en temps réel
