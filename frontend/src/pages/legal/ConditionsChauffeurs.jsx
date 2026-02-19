import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./LegalPages.css";

export default function ConditionsChauffeurs() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button onClick={() => navigate("/")} className="legal-back-btn">
          <ArrowLeft className="w-5 h-5" />
          Retour
        </button>

        <h1 className="legal-title">Conditions Chauffeurs Partenaires</h1>

        <section className="legal-section">
          <h2>Article 1 — Objet</h2>
          <p>Les présentes conditions définissent la collaboration entre JABADRIVER et les chauffeurs partenaires indépendants utilisant la plateforme.</p>
        </section>

        <section className="legal-section">
          <h2>Article 2 — Statut</h2>
          <p>Le chauffeur partenaire exerce en qualité d'indépendant.</p>
          <p>Aucun lien de subordination n'existe entre JABADRIVER et le chauffeur.</p>
        </section>

        <section className="legal-section">
          <h2>Article 3 — Conditions d'accès</h2>
          <p>Le chauffeur doit :</p>
          <ul className="legal-list">
            <li>posséder une carte professionnelle VTC valide</li>
            <li>disposer des assurances obligatoires</li>
            <li>utiliser un véhicule conforme à la réglementation</li>
            <li>être en situation légale d'exercice</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 4 — Attribution des courses</h2>
          <p>Les courses peuvent être proposées via la plateforme selon :</p>
          <ul className="legal-list">
            <li>disponibilité</li>
            <li>validation du chauffeur</li>
            <li>paiement de commission</li>
            <li>règles internes de la plateforme</li>
          </ul>
          <p>JABADRIVER ne garantit aucun volume de courses.</p>
        </section>

        <section className="legal-section">
          <h2>Article 5 — Commission</h2>
          <p>Une commission peut être demandée pour l'attribution des courses.</p>
          <p>Les modalités sont communiquées avant validation.</p>
        </section>

        <section className="legal-section">
          <h2>Article 6 — Responsabilité</h2>
          <p>Le chauffeur partenaire est seul responsable :</p>
          <ul className="legal-list">
            <li>de l'exécution du transport</li>
            <li>des passagers</li>
            <li>du respect de la réglementation</li>
            <li>des assurances professionnelles</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 7 — Obligations du chauffeur</h2>
          <p>Le chauffeur s'engage à :</p>
          <ul className="legal-list">
            <li>respecter les clients</li>
            <li>être ponctuel</li>
            <li>maintenir un véhicule propre et conforme</li>
            <li>adopter un comportement professionnel</li>
            <li>ne pas nuire à l'image de JABADRIVER</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 8 — Annulations</h2>
          <p>Le chauffeur doit prévenir rapidement en cas d'empêchement.</p>
          <p>Des mesures peuvent être prises en cas d'annulations répétées.</p>
        </section>

        <section className="legal-section">
          <h2>Article 9 — Suspension ou exclusion</h2>
          <p>JABADRIVER peut suspendre ou exclure un chauffeur en cas :</p>
          <ul className="legal-list">
            <li>de manquement professionnel</li>
            <li>comportement inapproprié</li>
            <li>non-respect des règles</li>
            <li>litiges clients</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 10 — Résiliation</h2>
          <p>Chaque partie peut mettre fin à la collaboration à tout moment.</p>
        </section>
      </div>
    </div>
  );
}
