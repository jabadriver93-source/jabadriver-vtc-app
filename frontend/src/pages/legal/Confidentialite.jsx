import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./LegalPages.css";

export default function Confidentialite() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button onClick={() => navigate("/")} className="legal-back-btn">
          <ArrowLeft className="w-5 h-5" />
          Retour
        </button>

        <h1 className="legal-title">Politique de Confidentialité</h1>

        <section className="legal-section">
          <h2>Responsable du traitement</h2>
          <div className="legal-info-block">
            <p><strong>JABADRIVER</strong></p>
            <p>SIRET : 941 473 217 00011</p>
            <p>Email : contact@jabadriver.fr</p>
          </div>
        </section>

        <section className="legal-section">
          <h2>Données collectées</h2>
          <h3>Clients</h3>
          <ul className="legal-list">
            <li>nom</li>
            <li>numéro de téléphone</li>
            <li>adresse email</li>
            <li>adresses de prise en charge et destination</li>
            <li>informations de réservation</li>
          </ul>
          <h3>Chauffeurs partenaires</h3>
          <ul className="legal-list">
            <li>identité</li>
            <li>coordonnées</li>
            <li>documents professionnels</li>
            <li>informations véhicule</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Finalités</h2>
          <p>Les données sont utilisées pour :</p>
          <ul className="legal-list">
            <li>gestion des réservations</li>
            <li>mise en relation client / chauffeur</li>
            <li>facturation</li>
            <li>support client</li>
            <li>obligations légales</li>
          </ul>
        </section>

        <section className="legal-section">
          <h2>Partage des données</h2>
          <p>Les données peuvent être transmises aux chauffeurs partenaires uniquement dans le cadre de la réalisation des prestations.</p>
          <p>JABADRIVER ne revend pas les données personnelles.</p>
        </section>

        <section className="legal-section">
          <h2>Durée de conservation</h2>
          <p>Les données sont conservées pendant la durée nécessaire à la relation commerciale et aux obligations légales.</p>
        </section>

        <section className="legal-section">
          <h2>Droits RGPD</h2>
          <p>Conformément à la réglementation, vous disposez :</p>
          <ul className="legal-list">
            <li>droit d'accès</li>
            <li>droit de rectification</li>
            <li>droit de suppression</li>
            <li>droit d'opposition</li>
          </ul>
          <p>Contact : contact@jabadriver.fr</p>
        </section>

        <section className="legal-section">
          <h2>Cookies</h2>
          <p>Le site peut utiliser des cookies techniques nécessaires à son fonctionnement et à l'amélioration de l'expérience utilisateur.</p>
        </section>
      </div>
    </div>
  );
}
