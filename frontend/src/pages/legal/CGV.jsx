import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./LegalPages.css";

export default function CGV() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button onClick={() => navigate("/")} className="legal-back-btn">
          <ArrowLeft className="w-5 h-5" />
          Retour
        </button>

        <h1 className="legal-title">CGV / Conditions de Réservation</h1>

        <section className="legal-section">
          <h2>Article 1 — Objet</h2>
          <p>Les présentes conditions définissent les modalités de réservation des prestations proposées par JABADRIVER.</p>
        </section>

        <section className="legal-section">
          <h2>Article 2 — Réservation</h2>
          <p>Les courses sont disponibles uniquement sur réservation préalable.</p>
          <p>Un délai minimum de 6 heures avant la prise en charge est requis.</p>
          <p>La réservation devient effective après confirmation.</p>
        </section>

        <section className="legal-section">
          <h2>Article 3 — Tarifs</h2>
          <p>Les prix sont communiqués avant validation.</p>
          <p>Ils peuvent varier selon :</p>
          <ul className="legal-list">
            <li>distance</li>
            <li>durée</li>
            <li>conditions de circulation</li>
            <li>suppléments</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 4 — Exécution de la prestation</h2>
          <p>La course peut être réalisée :</p>
          <ul className="legal-list">
            <li>par JABADRIVER</li>
            <li>par un chauffeur partenaire indépendant</li>
          </ul>
          <p>Le client accepte cette possibilité lors de la réservation.</p>
        </section>

        <section className="legal-section">
          <h2>Article 5 — Paiement</h2>
          <p>Le paiement peut être effectué :</p>
          <ul className="legal-list">
            <li>en ligne</li>
            <li>auprès du chauffeur</li>
            <li>ou selon modalités convenues</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 6 — Annulation</h2>
          <p>Annulation gratuite jusqu'à 1 heure avant la course.</p>
          <p>Passé ce délai, des frais peuvent être appliqués.</p>
        </section>

        <section className="legal-section">
          <h2>Article 7 — Retard client</h2>
          <p>Un temps d'attente raisonnable est inclus.</p>
          <p>Des frais peuvent être facturés au-delà.</p>
        </section>

        <section className="legal-section">
          <h2>Article 8 — Responsabilité</h2>
          <p>Lorsque la prestation est réalisée par un chauffeur partenaire, celui-ci est seul responsable du transport.</p>
        </section>

        <section className="legal-section">
          <h2>Article 9 — Comportement</h2>
          <p>Le chauffeur peut refuser la prise en charge en cas de comportement dangereux.</p>
        </section>

        <section className="legal-section">
          <h2>Article 10 — Litiges</h2>
          <p>Le droit français est applicable.</p>
        </section>
      </div>
    </div>
  );
}
