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
- ✅ Bouton "Partager via WhatsApp" dans l'email admin (NEW - 2025-02-13)
- ✅ Email admin "Nouveau chauffeur inscrit" avec bouton validation (NEW - 2025-02-13)

## Tech Stack
- **Backend:** FastAPI, Motor (MongoDB async), ReportLab (PDF), Resend (emails)
- **Frontend:** React, TailwindCSS, Shadcn UI
- **Paiement:** Stripe SDK Python natif
- **Database:** MongoDB

## Key API Endpoints
- `POST /api/reservations` - Création réservation + course sous-traitance
- `POST /api/driver/register` - Inscription chauffeur (+ email admin automatique)
- `POST /api/driver/login` - Connexion chauffeur
- `GET /api/subcontracting/claim/{token}` - Infos course à réclamer
- `POST /api/subcontracting/claim/{token}/reserve` - Réservation 3 min
- `POST /api/subcontracting/claim/{token}/initiate-payment` - Session Stripe
- `POST /api/subcontracting/stripe-webhook` - Confirmation paiement

## What's Been Implemented

### 2025-02-13
- ✅ Bouton "Partager via WhatsApp" dans l'email admin (nouvelle réservation)
  - Message pré-rempli : prix, villes (pas adresses), date/heure, lien claim
  - Utilise wa.me/?text= pour ouvrir WhatsApp directement
- ✅ Email automatique à l'admin lors de l'inscription d'un nouveau chauffeur
  - Résumé infos chauffeur (nom, société, email, téléphone, SIRET, adresse)
  - Statut "En attente de validation"
  - Bouton "Ouvrir / Valider le chauffeur" vers /admin/subcontracting

### Previous Sessions
- Module sous-traitance complet (subcontracting.py)
- Intégration Stripe fonctionnelle
- Interface admin et espace chauffeur
- Corrections UI/UX mobile
- Bug fix URLs production (corrigé par support)

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
│   ├── admin/AdminSubcontractingPage.jsx
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
- P1: Notifications push chauffeurs (optionnel)
- P2: Historique paiements commissions
- P2: Dashboard statistiques admin
