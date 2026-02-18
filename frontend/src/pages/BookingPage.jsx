import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { 
  MapPin, Users, Briefcase, MessageSquare, 
  Phone, Mail, Loader2, Clock, CheckCircle,
  User, Euro, Shield, Headphones
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

// Official assets from UI pack
const ASSETS = {
  logo: "/ui_pack/logo_original.png",
  car: "/ui_pack/car.png",
};

// Pricing constants
const PRICE_PER_KM = 1.50;
const PRICE_PER_MIN = 0.50;
const MIN_PRICE = 10;
const MIN_BOOKING_DELAY_HOURS = 6;
const PHONE_REGEX = /^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$/;

// Google Maps loading
let googleMapsLoaded = false;
let googleMapsLoading = false;
let mapsReadyCallbacks = [];

const notifyMapsReady = () => {
  googleMapsLoaded = true;
  googleMapsLoading = false;
  mapsReadyCallbacks.forEach(cb => cb());
  mapsReadyCallbacks = [];
};

const loadGoogleMapsScript = () => {
  return new Promise((resolve) => {
    if (googleMapsLoaded && window.google?.maps?.places) {
      resolve();
      return;
    }
    if (googleMapsLoading) {
      mapsReadyCallbacks.push(resolve);
      return;
    }
    if (window.google?.maps?.places) {
      googleMapsLoaded = true;
      resolve();
      return;
    }
    googleMapsLoading = true;
    mapsReadyCallbacks.push(resolve);
    const callbackName = `gmapsCallback_${Date.now()}`;
    window[callbackName] = () => {
      notifyMapsReady();
      delete window[callbackName];
    };
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places&language=fr&region=FR&callback=${callbackName}`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  });
};

export default function BookingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [phoneError, setPhoneError] = useState("");
  const [priceLoading, setPriceLoading] = useState(false);
  const [priceData, setPriceData] = useState(null);
  const [mapsReady, setMapsReady] = useState(false);
  
  const pickupInputRef = useRef(null);
  const dropoffInputRef = useRef(null);
  const pickupAutocompleteRef = useRef(null);
  const dropoffAutocompleteRef = useRef(null);
  const distanceServiceRef = useRef(null);
  
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    email: "",
    pickup_address: "",
    dropoff_address: "",
    date: "",
    time: "",
    passengers: 1,
    luggage: "",
    notes: ""
  });

  // Load Google Maps
  useEffect(() => {
    if (!GOOGLE_MAPS_API_KEY) return;
    loadGoogleMapsScript().then(() => {
      if (window.google?.maps?.places) setMapsReady(true);
    });
  }, []);

  // Initialize Autocomplete
  useEffect(() => {
    if (!mapsReady || !window.google?.maps?.places) return;

    const initAutocomplete = (inputRef, autocompleteRef, fieldName) => {
      if (!inputRef.current || autocompleteRef.current) return;
      try {
        const autocomplete = new window.google.maps.places.Autocomplete(inputRef.current, {
          types: ["address"],
          componentRestrictions: { country: "fr" },
          fields: ["formatted_address", "geometry", "name"]
        });
        autocomplete.addListener("place_changed", () => {
          const place = autocomplete.getPlace();
          if (place?.formatted_address) {
            setFormData(prev => ({ ...prev, [fieldName]: place.formatted_address }));
            if (inputRef.current) inputRef.current.value = place.formatted_address;
            setTimeout(() => triggerPriceCalculation(), 200);
          }
        });
        autocompleteRef.current = autocomplete;
      } catch (error) {
        console.error(`Failed to init autocomplete for ${fieldName}:`, error);
      }
    };

    if (!distanceServiceRef.current) {
      try {
        distanceServiceRef.current = new window.google.maps.DistanceMatrixService();
      } catch (error) {
        console.error("Failed to init Distance Matrix Service:", error);
      }
    }

    const timer = setTimeout(() => {
      initAutocomplete(pickupInputRef, pickupAutocompleteRef, "pickup_address");
      initAutocomplete(dropoffInputRef, dropoffAutocompleteRef, "dropoff_address");
    }, 200);

    return () => clearTimeout(timer);
  }, [mapsReady]);

  const triggerPriceCalculation = useCallback(() => {
    const pickup = pickupInputRef.current?.value;
    const dropoff = dropoffInputRef.current?.value;
    if (pickup && dropoff && pickup.length > 5 && dropoff.length > 5) {
      calculatePrice(pickup, dropoff);
    }
  }, []);

  const calculatePrice = useCallback((pickup, dropoff) => {
    if (!pickup || !dropoff || pickup.length < 5 || dropoff.length < 5) {
      setPriceData(null);
      return;
    }
    if (!distanceServiceRef.current) return;
    setPriceLoading(true);
    try {
      distanceServiceRef.current.getDistanceMatrix(
        {
          origins: [pickup],
          destinations: [dropoff],
          travelMode: window.google.maps.TravelMode.DRIVING,
          unitSystem: window.google.maps.UnitSystem.METRIC,
        },
        (response, status) => {
          setPriceLoading(false);
          if (status === "OK" && response?.rows?.[0]?.elements?.[0]?.status === "OK") {
            const element = response.rows[0].elements[0];
            const distanceKm = element.distance.value / 1000;
            const durationMin = element.duration.value / 60;
            let price = (distanceKm * PRICE_PER_KM) + (durationMin * PRICE_PER_MIN);
            if (price < MIN_PRICE) price = MIN_PRICE;
            price = Math.ceil(price);
            setPriceData({
              distance_km: Math.round(distanceKm * 10) / 10,
              duration_min: Math.round(durationMin),
              estimated_price: price
            });
          } else {
            setPriceData(null);
          }
        }
      );
    } catch (error) {
      setPriceLoading(false);
      setPriceData(null);
    }
  }, []);

  useEffect(() => {
    if (!mapsReady) return;
    const timer = setTimeout(() => triggerPriceCalculation(), 1000);
    return () => clearTimeout(timer);
  }, [formData.pickup_address, formData.dropoff_address, mapsReady, triggerPriceCalculation]);

  const validatePhone = (phone) => {
    if (!phone) return "Le téléphone est obligatoire";
    const cleaned = phone.replace(/\s/g, "");
    if (!PHONE_REGEX.test(phone) && !/^(0|\+33|0033)[1-9]\d{8}$/.test(cleaned)) {
      return "Numéro de téléphone français invalide";
    }
    return "";
  };

  const getMinTime = (selectedDate) => {
    if (!selectedDate) return "";
    const today = new Date().toISOString().split('T')[0];
    if (selectedDate === today) {
      const minTime = new Date();
      minTime.setHours(minTime.getHours() + MIN_BOOKING_DELAY_HOURS);
      minTime.setMinutes(Math.ceil(minTime.getMinutes() / 15) * 15);
      return `${String(minTime.getHours()).padStart(2, '0')}:${String(minTime.getMinutes()).padStart(2, '0')}`;
    }
    return "";
  };

  const isDateTimeValid = () => {
    if (!formData.date || !formData.time) return false;
    const selectedDateTime = new Date(`${formData.date}T${formData.time}`);
    const minDateTime = new Date();
    minDateTime.setHours(minDateTime.getHours() + MIN_BOOKING_DELAY_HOURS);
    return selectedDateTime >= minDateTime;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (name === "phone") setPhoneError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const actualPickup = pickupInputRef.current?.value || formData.pickup_address;
    const actualDropoff = dropoffInputRef.current?.value || formData.dropoff_address;
    
    const submissionData = {
      ...formData,
      pickup_address: actualPickup,
      dropoff_address: actualDropoff
    };

    const phoneValidation = validatePhone(submissionData.phone);
    if (phoneValidation) {
      setPhoneError(phoneValidation);
      toast.error(phoneValidation);
      return;
    }

    if (!submissionData.name || !actualPickup || !actualDropoff || !submissionData.date || !submissionData.time) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const selectedDate = new Date(`${submissionData.date}T${submissionData.time}`);
    if (selectedDate < new Date()) {
      toast.error("La date et l'heure ne peuvent pas être dans le passé");
      return;
    }

    const minBookingTime = new Date();
    minBookingTime.setHours(minBookingTime.getHours() + MIN_BOOKING_DELAY_HOURS);
    if (selectedDate < minBookingTime) {
      toast.error(`Les réservations doivent être effectuées au minimum ${MIN_BOOKING_DELAY_HOURS} heures à l'avance.`);
      return;
    }

    setLoading(true);
    try {
      const reservationData = {
        ...submissionData,
        distance_km: priceData?.distance_km || null,
        duration_min: priceData?.duration_min || null,
        estimated_price: priceData?.estimated_price || null
      };
      const response = await axios.post(`${API}/reservations`, reservationData);
      toast.success("Réservation enregistrée !");
      navigate(`/confirmation/${response.data.id}`);
    } catch (error) {
      toast.error("Erreur lors de la réservation. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="jaba-page">
      {/* Neon Background */}
      <div className="jaba-bg">
        <div className="jaba-grid" />
        <svg className="jaba-routes" viewBox="0 0 1024 1536" preserveAspectRatio="xMidYMid slice">
          <defs>
            <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="transparent" />
              <stop offset="50%" stopColor="#00B6FF" />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
            <filter id="neonGlow">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path className="route-path" d="M0,300 Q200,250 400,320 T800,280 T1024,350" />
          <path className="route-path delay-1" d="M0,500 Q300,450 500,520 T900,480" />
          <path className="route-path delay-2" d="M100,700 Q400,650 600,720 T1024,680" />
          <path className="route-path delay-3" d="M0,900 Q250,850 450,920 T850,880 T1024,950" />
        </svg>
        <div className="jaba-glow-center" />
      </div>

      {/* Header */}
      <header className="jaba-header">
        <div className="jaba-header-inner">
          <img src={ASSETS.logo} alt="JABADRIVER" className="jaba-header-logo" />
          <div className="jaba-header-buttons">
            <a href="/driver/login" className="jaba-btn-gold" data-testid="driver-space-link">
              <span>🚗</span> Chauffeur
            </a>
            <a href="/admin" className="jaba-btn-blue" data-testid="admin-link">
              <span>⚙️</span> Admin
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="jaba-main">
        {/* Hero Section */}
        <section className="jaba-hero">
          <img src={ASSETS.logo} alt="JABADRIVER" className="jaba-hero-logo" />
          <h1 className="jaba-title">
            Réservez votre <span className="jaba-title-accent">VTC</span>
          </h1>
          <p className="jaba-subtitle">Service premium, votre chauffeur privé en Île-de-France</p>
        </section>

        {/* Feature Tiles */}
        <section className="jaba-tiles">
          <div className="jaba-tile">
            <div className="jaba-tile-icon">
              <Clock className="w-5 h-5" />
            </div>
            <div className="jaba-tile-text">
              <span className="jaba-tile-title">Ponctualité</span>
              <span className="jaba-tile-desc">Arrivée à l'heure, toujours</span>
            </div>
          </div>
          <div className="jaba-tile">
            <div className="jaba-tile-icon">
              <Shield className="w-5 h-5" />
            </div>
            <div className="jaba-tile-text">
              <span className="jaba-tile-title">Confort</span>
              <span className="jaba-tile-desc">Véhicules haut de gamme</span>
            </div>
          </div>
          <div className="jaba-tile">
            <div className="jaba-tile-icon">
              <Euro className="w-5 h-5" />
            </div>
            <div className="jaba-tile-text">
              <span className="jaba-tile-title">Prix clair</span>
              <span className="jaba-tile-desc">Tarifs fixés à l'avance</span>
            </div>
          </div>
        </section>

        {/* Booking Form Card */}
        <section className="jaba-form-section">
          <form onSubmit={handleSubmit} id="booking-form" className="jaba-form-card" data-testid="booking-form">
            <h2 className="jaba-form-title">RÉSERVATION</h2>

            {/* Name */}
            <div className="jaba-field">
              <label className="jaba-label">NOM COMPLET *</label>
              <div className="jaba-input-wrap">
                <User className="jaba-input-icon" />
                <input
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Jean Dupont"
                  className="jaba-input"
                  data-testid="input-name"
                  required
                />
              </div>
            </div>

            {/* Phone */}
            <div className="jaba-field">
              <label className="jaba-label">TÉLÉPHONE *</label>
              <div className="jaba-input-wrap">
                <Phone className="jaba-input-icon" />
                <input
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="06 12 34 56 78"
                  className={`jaba-input ${phoneError ? 'error' : ''}`}
                  data-testid="input-phone"
                  required
                />
              </div>
              {phoneError && <span className="jaba-error">{phoneError}</span>}
            </div>

            {/* Email */}
            <div className="jaba-field">
              <label className="jaba-label">EMAIL (OPTIONNEL)</label>
              <div className="jaba-input-wrap">
                <Mail className="jaba-input-icon" />
                <input
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="jean@example.com"
                  className="jaba-input"
                  data-testid="input-email"
                />
              </div>
            </div>

            {/* Pickup */}
            <div className="jaba-field">
              <label className="jaba-label">ADRESSE DE DÉPART *</label>
              <div className="jaba-input-wrap">
                <MapPin className="jaba-input-icon green" />
                <input
                  ref={pickupInputRef}
                  name="pickup_address"
                  type="text"
                  defaultValue={formData.pickup_address}
                  onChange={handleChange}
                  placeholder="Entrez une adresse..."
                  className="jaba-input"
                  data-testid="input-pickup"
                  autoComplete="off"
                  required
                />
              </div>
            </div>

            {/* Dropoff */}
            <div className="jaba-field">
              <label className="jaba-label">ADRESSE D'ARRIVÉE *</label>
              <div className="jaba-input-wrap">
                <MapPin className="jaba-input-icon red" />
                <input
                  ref={dropoffInputRef}
                  name="dropoff_address"
                  type="text"
                  defaultValue={formData.dropoff_address}
                  onChange={handleChange}
                  placeholder="Entrez une adresse..."
                  className="jaba-input"
                  data-testid="input-dropoff"
                  autoComplete="off"
                  required
                />
              </div>
            </div>

            {/* Price Display */}
            <div className="jaba-price-box" data-testid="price-estimation">
              <div className="jaba-price-icon">
                <Euro className="w-5 h-5" />
              </div>
              <div className="jaba-price-info">
                <span className="jaba-price-label">PRIX ESTIMÉ</span>
                {priceLoading ? (
                  <span className="jaba-price-loading"><Loader2 className="w-4 h-4 animate-spin" /> Calcul...</span>
                ) : priceData ? (
                  <span className="jaba-price-value">{priceData.estimated_price}€</span>
                ) : (
                  <span className="jaba-price-placeholder">Entrez les adresses</span>
                )}
              </div>
              {priceData && (
                <div className="jaba-price-details">
                  <span>{priceData.distance_km} km</span>
                  <span>{priceData.duration_min} min</span>
                </div>
              )}
            </div>

            {/* Date & Time */}
            <div className="jaba-row">
              <div className="jaba-field half">
                <label className="jaba-label">DATE *</label>
                <input
                  name="date"
                  type="date"
                  value={formData.date}
                  onChange={handleChange}
                  min={today}
                  className="jaba-input"
                  data-testid="input-date"
                  required
                />
              </div>
              <div className="jaba-field half">
                <label className="jaba-label">HEURE *</label>
                <input
                  name="time"
                  type="time"
                  value={formData.time}
                  onChange={handleChange}
                  min={getMinTime(formData.date)}
                  className="jaba-input"
                  data-testid="input-time"
                  required
                />
              </div>
            </div>
            <p className="jaba-hint"><Clock className="w-3 h-3" /> Minimum {MIN_BOOKING_DELAY_HOURS}h à l'avance</p>

            {/* Passengers */}
            <div className="jaba-field">
              <label className="jaba-label">PASSAGERS</label>
              <div className="jaba-input-wrap">
                <Users className="jaba-input-icon" />
                <select
                  name="passengers"
                  value={formData.passengers}
                  onChange={handleChange}
                  className="jaba-input"
                  data-testid="input-passengers"
                >
                  {[1,2,3,4,5,6,7].map(n => (
                    <option key={n} value={n}>{n} passager{n > 1 ? 's' : ''}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Luggage */}
            <div className="jaba-field">
              <label className="jaba-label">BAGAGES (OPTIONNEL)</label>
              <div className="jaba-input-wrap">
                <Briefcase className="jaba-input-icon" />
                <input
                  name="luggage"
                  type="text"
                  value={formData.luggage}
                  onChange={handleChange}
                  placeholder="2 valises, 1 sac cabine"
                  className="jaba-input"
                  data-testid="input-luggage"
                />
              </div>
            </div>

            {/* Notes */}
            <div className="jaba-field">
              <label className="jaba-label">NOTE AU CHAUFFEUR (OPTIONNEL)</label>
              <div className="jaba-input-wrap textarea">
                <MessageSquare className="jaba-input-icon top" />
                <textarea
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  placeholder="Instructions spéciales, numéro de vol..."
                  className="jaba-input textarea"
                  data-testid="input-notes"
                />
              </div>
            </div>

            {/* CTA Button */}
            <button
              type="submit"
              disabled={loading || !isDateTimeValid()}
              className="jaba-cta"
              data-testid="submit-booking"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Réservation en cours...</>
              ) : (
                <><CheckCircle className="w-5 h-5" /> RÉSERVER MAINTENANT</>
              )}
            </button>

            <p className="jaba-support-text">
              Annulation gratuite jusqu'à 1h avant
            </p>
          </form>
        </section>

        {/* Car Visual */}
        <div className="jaba-car-container">
          <img src={ASSETS.car} alt="Voiture VTC" className="jaba-car" />
        </div>

        {/* Bottom Badges */}
        <section className="jaba-badges">
          <div className="jaba-badge">
            <div className="jaba-badge-icon">
              <Clock className="w-4 h-4" />
            </div>
            <span>Disponible 24/7</span>
          </div>
          <div className="jaba-badge">
            <div className="jaba-badge-icon">
              <CheckCircle className="w-4 h-4" />
            </div>
            <span>Chauffeurs vérifiés</span>
          </div>
          <div className="jaba-badge">
            <div className="jaba-badge-icon">
              <Headphones className="w-4 h-4" />
            </div>
            <span>Support tel</span>
          </div>
        </section>
      </main>

      {/* Inline Styles */}
      <style>{`
        /* ========================================
           JABADRIVER PREMIUM LANDING PAGE
           ======================================== */
        
        .jaba-page {
          min-height: 100vh;
          background: #030B1A;
          color: white;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          position: relative;
          overflow-x: hidden;
        }

        /* Background */
        .jaba-bg {
          position: fixed;
          inset: 0;
          z-index: 0;
          pointer-events: none;
        }

        .jaba-grid {
          position: absolute;
          inset: 0;
          background-image: 
            linear-gradient(rgba(46, 167, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(46, 167, 255, 0.03) 1px, transparent 1px);
          background-size: 50px 50px;
          opacity: 0.5;
        }

        .jaba-routes {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          opacity: 0.6;
        }

        .route-path {
          fill: none;
          stroke: url(#routeGrad);
          stroke-width: 2;
          filter: url(#neonGlow);
          animation: routePulse 4s ease-in-out infinite;
        }

        .route-path.delay-1 { animation-delay: 1s; }
        .route-path.delay-2 { animation-delay: 2s; }
        .route-path.delay-3 { animation-delay: 3s; }

        @keyframes routePulse {
          0%, 100% { opacity: 0.3; stroke-width: 1.5; }
          50% { opacity: 0.8; stroke-width: 2.5; }
        }

        .jaba-glow-center {
          position: absolute;
          top: 20%;
          left: 50%;
          transform: translateX(-50%);
          width: 600px;
          height: 400px;
          background: radial-gradient(ellipse, rgba(0, 182, 255, 0.15) 0%, transparent 70%);
        }

        /* Header */
        .jaba-header {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 100;
          padding: 12px 16px;
          background: rgba(3, 11, 26, 0.85);
          backdrop-filter: blur(20px);
          border-bottom: 1px solid rgba(46, 167, 255, 0.15);
        }

        .jaba-header-inner {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .jaba-header-logo {
          height: 40px;
          width: auto;
          filter: drop-shadow(0 0 10px rgba(0, 182, 255, 0.3));
        }

        .jaba-header-buttons {
          display: flex;
          gap: 8px;
        }

        .jaba-btn-gold {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          background: rgba(255, 180, 0, 0.15);
          border: 1px solid rgba(255, 180, 0, 0.4);
          border-radius: 10px;
          color: #FFB400;
          font-size: 13px;
          font-weight: 600;
          text-decoration: none;
          transition: all 0.3s ease;
        }

        .jaba-btn-gold:hover {
          background: rgba(255, 180, 0, 0.25);
          box-shadow: 0 0 20px rgba(255, 180, 0, 0.3);
        }

        .jaba-btn-blue {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          background: rgba(46, 167, 255, 0.15);
          border: 1px solid rgba(46, 167, 255, 0.3);
          border-radius: 10px;
          color: #2EA7FF;
          font-size: 13px;
          font-weight: 500;
          text-decoration: none;
          transition: all 0.3s ease;
        }

        .jaba-btn-blue:hover {
          background: rgba(46, 167, 255, 0.25);
          box-shadow: 0 0 15px rgba(46, 167, 255, 0.3);
        }

        /* Main Content */
        .jaba-main {
          position: relative;
          z-index: 1;
          padding: 80px 16px 40px;
          max-width: 600px;
          margin: 0 auto;
        }

        /* Hero */
        .jaba-hero {
          text-align: center;
          padding: 40px 0 30px;
        }

        .jaba-hero-logo {
          height: 80px;
          width: auto;
          margin-bottom: 20px;
          filter: drop-shadow(0 0 30px rgba(0, 182, 255, 0.5));
          animation: logoBreath 3s ease-in-out infinite;
        }

        @keyframes logoBreath {
          0%, 100% { 
            filter: drop-shadow(0 0 20px rgba(0, 182, 255, 0.4));
            transform: scale(1);
          }
          50% { 
            filter: drop-shadow(0 0 40px rgba(0, 182, 255, 0.7));
            transform: scale(1.02);
          }
        }

        .jaba-title {
          font-size: 28px;
          font-weight: 700;
          margin-bottom: 8px;
          letter-spacing: -0.02em;
        }

        .jaba-title-accent {
          background: linear-gradient(135deg, #00B6FF, #2EA7FF);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .jaba-subtitle {
          color: rgba(255, 255, 255, 0.6);
          font-size: 14px;
        }

        /* Feature Tiles */
        .jaba-tiles {
          display: flex;
          justify-content: center;
          gap: 12px;
          margin-bottom: 24px;
          flex-wrap: wrap;
        }

        .jaba-tile {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          transition: all 0.3s ease;
        }

        .jaba-tile:hover {
          background: rgba(46, 167, 255, 0.08);
          border-color: rgba(46, 167, 255, 0.2);
          transform: translateY(-2px);
        }

        .jaba-tile-icon {
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #00B6FF, #2EA7FF);
          border-radius: 10px;
          color: #030B1A;
        }

        .jaba-tile-text {
          display: flex;
          flex-direction: column;
        }

        .jaba-tile-title {
          font-size: 13px;
          font-weight: 600;
          color: white;
        }

        .jaba-tile-desc {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
        }

        /* Form Card */
        .jaba-form-section {
          margin-bottom: 20px;
        }

        .jaba-form-card {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 20px;
          padding: 28px 24px;
          position: relative;
        }

        .jaba-form-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 20px;
          right: 20px;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(46, 167, 255, 0.5), transparent);
        }

        .jaba-form-title {
          text-align: center;
          font-size: 16px;
          font-weight: 700;
          letter-spacing: 0.1em;
          color: white;
          margin-bottom: 24px;
        }

        .jaba-field {
          margin-bottom: 16px;
        }

        .jaba-field.half {
          flex: 1;
        }

        .jaba-row {
          display: flex;
          gap: 12px;
        }

        .jaba-label {
          display: block;
          font-size: 10px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.5);
          letter-spacing: 0.1em;
          margin-bottom: 8px;
        }

        .jaba-input-wrap {
          position: relative;
        }

        .jaba-input-wrap.textarea {
          align-items: flex-start;
        }

        .jaba-input-icon {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          width: 18px;
          height: 18px;
          color: rgba(255, 255, 255, 0.4);
          transition: color 0.3s ease;
        }

        .jaba-input-icon.top {
          top: 16px;
          transform: none;
        }

        .jaba-input-icon.green { color: #22c55e; }
        .jaba-input-icon.red { color: #ef4444; }

        .jaba-input {
          width: 100%;
          height: 48px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 0 14px 0 44px;
          font-size: 14px;
          color: white;
          transition: all 0.3s ease;
        }

        .jaba-input.textarea {
          height: 80px;
          padding: 14px 14px 14px 44px;
          resize: none;
        }

        .jaba-input::placeholder {
          color: rgba(255, 255, 255, 0.3);
        }

        .jaba-input:focus {
          outline: none;
          border-color: #2EA7FF;
          box-shadow: 0 0 0 3px rgba(46, 167, 255, 0.15);
          background: rgba(46, 167, 255, 0.05);
        }

        .jaba-input.error {
          border-color: #ef4444;
        }

        .jaba-input::-webkit-calendar-picker-indicator {
          filter: invert(1);
          opacity: 0.5;
        }

        select.jaba-input {
          cursor: pointer;
          appearance: none;
        }

        .jaba-error {
          display: block;
          font-size: 11px;
          color: #ef4444;
          margin-top: 4px;
        }

        .jaba-hint {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          color: rgba(255, 255, 255, 0.4);
          margin-bottom: 16px;
        }

        /* Price Box */
        .jaba-price-box {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 16px;
          background: linear-gradient(135deg, rgba(46, 167, 255, 0.1) 0%, rgba(0, 182, 255, 0.05) 100%);
          border: 1px solid rgba(46, 167, 255, 0.2);
          border-radius: 14px;
          margin-bottom: 16px;
        }

        .jaba-price-icon {
          width: 44px;
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #00B6FF, #2EA7FF);
          border-radius: 12px;
          color: #030B1A;
          flex-shrink: 0;
        }

        .jaba-price-info {
          flex: 1;
        }

        .jaba-price-label {
          display: block;
          font-size: 10px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.5);
          letter-spacing: 0.1em;
        }

        .jaba-price-value {
          font-size: 28px;
          font-weight: 800;
          background: linear-gradient(135deg, #00B6FF, #2EA7FF);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .jaba-price-loading {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: rgba(255, 255, 255, 0.5);
        }

        .jaba-price-placeholder {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.3);
        }

        .jaba-price-details {
          display: flex;
          flex-direction: column;
          font-size: 11px;
          color: rgba(255, 255, 255, 0.4);
          text-align: right;
        }

        /* CTA Button */
        .jaba-cta {
          width: 100%;
          height: 54px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          background: linear-gradient(135deg, #00B6FF, #2EA7FF);
          border: none;
          border-radius: 14px;
          color: #030B1A;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
          box-shadow: 0 8px 30px rgba(0, 182, 255, 0.3);
          margin-top: 8px;
        }

        .jaba-cta::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
          transition: left 0.5s ease;
        }

        .jaba-cta:hover::before {
          left: 100%;
        }

        .jaba-cta:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 40px rgba(0, 182, 255, 0.4);
        }

        .jaba-cta:disabled {
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.3);
          box-shadow: none;
          cursor: not-allowed;
        }

        .jaba-support-text {
          text-align: center;
          font-size: 11px;
          color: rgba(255, 255, 255, 0.4);
          margin-top: 12px;
        }

        /* Car Visual */
        .jaba-car-container {
          display: flex;
          justify-content: center;
          margin: -20px 0 10px;
          pointer-events: none;
        }

        .jaba-car {
          width: 90%;
          max-width: 400px;
          height: auto;
          filter: drop-shadow(0 20px 40px rgba(0, 182, 255, 0.2));
          animation: carFloat 5s ease-in-out infinite;
        }

        @keyframes carFloat {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }

        /* Bottom Badges */
        .jaba-badges {
          display: flex;
          justify-content: center;
          gap: 10px;
          flex-wrap: wrap;
          padding-bottom: 20px;
        }

        .jaba-badge {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          color: rgba(255, 255, 255, 0.7);
          font-size: 12px;
          font-weight: 500;
        }

        .jaba-badge-icon {
          width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(46, 167, 255, 0.15);
          border-radius: 8px;
          color: #2EA7FF;
        }

        /* Responsive */
        @media (min-width: 640px) {
          .jaba-hero-logo {
            height: 100px;
          }
          
          .jaba-title {
            font-size: 36px;
          }
          
          .jaba-form-card {
            padding: 36px 32px;
          }
        }

        @media (max-width: 400px) {
          .jaba-tiles {
            flex-direction: column;
            align-items: stretch;
          }
          
          .jaba-tile {
            justify-content: center;
          }
          
          .jaba-badges {
            flex-direction: column;
            align-items: center;
          }
        }
      `}</style>
    </div>
  );
}
