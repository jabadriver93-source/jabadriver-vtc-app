import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./LegalPages.css";

export default function MentionsLegales() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button onClick={() => navigate("/")} className="legal-back-btn">
          <ArrowLeft className="w-5 h-5" />
          Retour
        </button>

        <h1 className="legal-title">Mentions Légales</h1>

        <section className="legal-section">
          <h2>Éditeur du site</h2>
          <p>Le site www.jabadriver.fr est édité par :</p>
          <div className="legal-info-block">
            <p><strong>JABADRIVER</strong></p>
            <p>Entrepreneur individuel</p>
            <p>SIREN : 941 473 217</p>
            <p>SIRET : 941 473 217 00011</p>
          </div>
          <div className="legal-info-block">
            <p><strong>Adresse :</strong></p>
            <p>49 boulevard Marc Chagall</p>
            <p>93600 Aulnay-sous-Bois — France</p>
          </div>
          <p>Téléphone : 07 56 92 37 11</p>
          <p>Email : contact@jabadriver.fr</p>
          <p>Responsable de la publication : JABADRIVER</p>
        </section>

        <section className="legal-section">
          <h2>Hébergement</h2>
          <div className="legal-info-block">
            <p><strong>IONOS SARL</strong></p>
            <p>7 Place de la Gare</p>
            <p>57200 Sarreguemines — France</p>
            <p>https://www.ionos.fr</p>
            <p>0970 808 911</p>
          </div>
        </section>

        <section className="legal-section">
          <h2>Nature de l'activité</h2>
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
        </section>

        <section className="legal-section">
          <h2>Responsabilité</h2>
          <p>Lorsque la prestation est réalisée par un chauffeur partenaire, celui-ci est seul responsable de l'exécution du transport.</p>
          <p>JABADRIVER agit alors comme intermédiaire technique.</p>
        </section>

        <section className="legal-section">
          <h2>Propriété intellectuelle</h2>
          <p>Tous les éléments du site sont la propriété exclusive de JABADRIVER sauf mention contraire.</p>
        </section>

        <section className="legal-section">
          <h2>Données personnelles</h2>
          <p>Les données collectées sont utilisées uniquement pour :</p>
          <ul className="legal-list">
            <li>gestion des réservations</li>
            <li>relation client</li>
            <li>facturation</li>
            <li>mise en relation avec les chauffeurs</li>
          </ul>
          <p>Conformément au RGPD, vous disposez d'un droit d'accès, rectification et suppression.</p>
          <p>Contact : contact@jabadriver.fr</p>
        </section>

        <section className="legal-section">
          <h2>Droit applicable</h2>
          <p>Le droit français est applicable.</p>
        </section>
      </div>
    </div>
  );
}
