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
          <p>Les présentes Conditions Générales de Vente et de Réservation définissent les modalités de réservation et d'exécution des prestations proposées par JABADRIVER via le site internet.</p>
        </section>

        <section className="legal-section">
          <h2>Article 2 — Nature du service</h2>
          <p>JABADRIVER exerce :</p>
          <ul className="legal-list">
            <li>une activité de transport de personnes avec chauffeur (VTC)</li>
            <li>une activité de plateforme de mise en relation entre clients et chauffeurs partenaires indépendants</li>
          </ul>
          <p>Selon la disponibilité, la course peut être réalisée :</p>
          <ul className="legal-list">
            <li>soit directement par JABADRIVER</li>
            <li>soit par un chauffeur partenaire indépendant</li>
          </ul>
          <p>Le client accepte cette possibilité lors de la réservation.</p>
        </section>

        <section className="legal-section">
          <h2>Article 3 — Réservation</h2>
          <p>Les prestations sont accessibles uniquement sur réservation préalable via :</p>
          <ul className="legal-list">
            <li>le site internet</li>
            <li>téléphone</li>
            <li>WhatsApp</li>
          </ul>
          <p>Un délai minimum de réservation de 6 heures avant la prise en charge peut être exigé.</p>
          <p>La réservation est considérée comme confirmée après validation.</p>
        </section>

        <section className="legal-section">
          <h2>Article 4 — Tarifs</h2>
          <p>Les tarifs sont communiqués avant validation de la réservation.</p>
          <p>Ils peuvent varier selon :</p>
          <ul className="legal-list">
            <li>distance</li>
            <li>durée</li>
            <li>conditions de circulation</li>
            <li>suppléments éventuels</li>
            <li>temps d'attente</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 5 — Paiement</h2>
          <p>Le paiement peut être effectué :</p>
          <ul className="legal-list">
            <li>en ligne</li>
            <li>auprès du chauffeur</li>
            <li>ou selon les modalités convenues</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 6 — Annulation</h2>
          <p>L'annulation est gratuite jusqu'à 1 heure avant la prise en charge.</p>
          <p>Passé ce délai, des frais peuvent être appliqués.</p>
        </section>

        <section className="legal-section">
          <h2>Article 7 — Retard client</h2>
          <p>Un délai d'attente raisonnable est inclus.</p>
          <p>Au-delà, des frais d'attente peuvent être facturés.</p>
          <p>En cas d'absence du client, la prestation pourra être considérée comme due.</p>
        </section>

        <section className="legal-section">
          <h2>Article 8 — Responsabilité</h2>
          <p>Lorsque la prestation est réalisée par un chauffeur partenaire indépendant, celui-ci est seul responsable de l'exécution du transport.</p>
          <p>JABADRIVER agit alors comme intermédiaire technique.</p>
        </section>

        <section className="legal-section">
          <h2>Article 9 — Comportement</h2>
          <p>Le chauffeur peut refuser la prise en charge en cas de :</p>
          <ul className="legal-list">
            <li>comportement dangereux</li>
            <li>état d'ébriété</li>
            <li>non-respect des règles de sécurité</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Article 10 — Litiges</h2>
          <p>Le droit français est applicable.</p>
          <p>En cas de litige, une solution amiable sera recherchée avant toute procédure judiciaire.</p>
        </section>
      </div>
    </div>
  );
}
