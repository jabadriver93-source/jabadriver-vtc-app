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
          <p>Les présentes conditions définissent la collaboration entre JABADRIVER et les chauffeurs partenaires.</p>
        </section>

        <section className="legal-section">
          <h2>Article 2 — Statut</h2>
          <p>Le chauffeur est indépendant.</p>
          <p>Aucun lien de subordination n'existe.</p>
        </section>

        <section className="legal-section">
          <h2>Article 3 — Conditions d'accès</h2>
          <p>Le chauffeur doit :</p>
          <ul className="legal-list">
            <li>posséder carte VTC valide</li>
            <li>assurances obligatoires</li>
            <li>véhicule conforme</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 4 — Attribution des courses</h2>
          <p>Les courses sont proposées selon :</p>
          <ul className="legal-list">
            <li>disponibilité</li>
            <li>validation</li>
            <li>paiement commission</li>
          </ul>
          <p>Aucun volume n'est garanti.</p>
        </section>

        <section className="legal-section">
          <h2>Article 5 — Commission</h2>
          <p>Une commission peut être demandée pour l'attribution des courses.</p>
        </section>

        <section className="legal-section">
          <h2>Article 6 — Responsabilité</h2>
          <p>Le chauffeur est seul responsable :</p>
          <ul className="legal-list">
            <li>du transport</li>
            <li>du client</li>
            <li>des assurances</li>
            <li>de la réglementation</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 7 — Obligations</h2>
          <p>Le chauffeur s'engage à :</p>
          <ul className="legal-list">
            <li>respecter les clients</li>
            <li>être ponctuel</li>
            <li>maintenir véhicule propre</li>
            <li>comportement professionnel</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 8 — Suspension</h2>
          <p>JABADRIVER peut suspendre un chauffeur en cas de manquement.</p>
        </section>

        <section className="legal-section">
          <h2>Article 9 — Résiliation</h2>
          <p>Chaque partie peut mettre fin à la collaboration.</p>
        </section>
      </div>
    </div>
  );
}
