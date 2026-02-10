import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { 
  MapPin, Calendar, Users, Briefcase, MessageSquare, 
  Phone, Mail, Loader2, Clock, CheckCircle, Shield, CreditCard,
  User, Euro
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/logo.png";
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

// Pricing constants
const PRICE_PER_KM = 1.50;
const PRICE_PER_MIN = 0.50;
const MIN_PRICE = 10;

// French phone validation regex
const PHONE_REGEX = /^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$/;

export default function BookingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [phoneError, setPhoneError] = useState("");
  const [priceLoading, setPriceLoading] = useState(false);
  const [priceData, setPriceData] = useState(null);
  const debounceTimer = useRef(null);
  
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

  const validatePhone = (phone) => {
    if (!phone) return "Le téléphone est obligatoire";
    const cleaned = phone.replace(/\s/g, "");
    if (!PHONE_REGEX.test(phone) && !/^(0|\+33|0033)[1-9]\d{8}$/.test(cleaned)) {
      return "Numéro de téléphone français invalide";
    }
    return "";
  };

  // Calculate price using Google Maps Directions API
  const calculatePrice = useCallback(async (pickup, dropoff) => {
    if (!pickup || !dropoff || pickup.length < 5 || dropoff.length < 5) {
      setPriceData(null);
      return;
    }

    setPriceLoading(true);
    
    try {
      // Use Google Maps Directions API via CORS proxy or directly
      const directionsUrl = `https://maps.googleapis.com/maps/api/directions/json?origin=${encodeURIComponent(pickup)}&destination=${encodeURIComponent(dropoff)}&key=${GOOGLE_MAPS_API_KEY}`;
      
      // Since we can't call Google API directly from browser (CORS), we'll use the Distance Matrix API
      // which can be loaded via script
      const service = new window.google.maps.DistanceMatrixService();
      
      service.getDistanceMatrix(
        {
          origins: [pickup],
          destinations: [dropoff],
          travelMode: window.google.maps.TravelMode.DRIVING,
          unitSystem: window.google.maps.UnitSystem.METRIC,
        },
        (response, status) => {
          setPriceLoading(false);
          
          if (status === "OK" && response.rows[0].elements[0].status === "OK") {
            const element = response.rows[0].elements[0];
            const distanceKm = element.distance.value / 1000; // meters to km
            const durationMin = element.duration.value / 60; // seconds to minutes
            
            // Calculate price
            let price = (distanceKm * PRICE_PER_KM) + (durationMin * PRICE_PER_MIN);
            
            // Apply minimum
            if (price < MIN_PRICE) {
              price = MIN_PRICE;
            }
            
            // Round up to next euro
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
      console.error("Price calculation error:", error);
      setPriceLoading(false);
      setPriceData(null);
    }
  }, []);

  // Debounced price calculation
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    
    debounceTimer.current = setTimeout(() => {
      if (formData.pickup_address && formData.dropoff_address) {
        calculatePrice(formData.pickup_address, formData.dropoff_address);
      }
    }, 800);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [formData.pickup_address, formData.dropoff_address, calculatePrice]);

  // Load Google Maps script
  useEffect(() => {
    if (!window.google) {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      document.head.appendChild(script);
    }
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    if (name === "phone") {
      setPhoneError("");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    const phoneValidation = validatePhone(formData.phone);
    if (phoneValidation) {
      setPhoneError(phoneValidation);
      toast.error(phoneValidation);
      return;
    }

    if (!formData.name || !formData.pickup_address || 
        !formData.dropoff_address || !formData.date || !formData.time) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    // Check date is not in the past
    const selectedDate = new Date(`${formData.date}T${formData.time}`);
    if (selectedDate < new Date()) {
      toast.error("La date et l'heure ne peuvent pas être dans le passé");
      return;
    }

    setLoading(true);
    try {
      // Include pricing data in reservation
      const reservationData = {
        ...formData,
        distance_km: priceData?.distance_km || null,
        duration_min: priceData?.duration_min || null,
        estimated_price: priceData?.estimated_price || null
      };
      
      const response = await axios.post(`${API}/reservations`, reservationData);
      toast.success("Réservation enregistrée !");
      navigate(`/confirmation/${response.data.id}`);
    } catch (error) {
      console.error("Booking error:", error);
      toast.error("Erreur lors de la réservation. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  // Get min date (today)
  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="px-5 py-5 border-b border-white/10">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={LOGO_URL} alt="JABA DRIVER" className="h-10 w-auto" />
            <span className="text-xl font-bold text-white tracking-tight hidden sm:block" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABA DRIVER
            </span>
          </div>
          <a 
            href="/admin" 
            className="text-white/40 hover:text-white/70 text-sm font-medium transition-colors"
            data-testid="admin-link"
          >
            Admin
          </a>
        </div>
      </header>

      {/* Hero Section */}
      <section className="px-5 pt-12 pb-8 sm:pt-16 sm:pb-12">
        <div className="max-w-5xl mx-auto text-center">
          <h1 
            className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white mb-4 animate-fadeIn"
            style={{ fontFamily: 'Manrope, sans-serif', lineHeight: 1.1 }}
          >
            Réservez votre <span className="text-[#7dd3fc]">VTC</span>
          </h1>
          <p className="text-white/60 text-base sm:text-lg mb-10 max-w-xl mx-auto animate-fadeIn" style={{ animationDelay: '0.1s' }}>
            Service premium, votre chauffeur privé en Île-de-France
          </p>

          {/* Badges */}
          <div className="flex flex-wrap justify-center gap-3 sm:gap-4 animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            <div className="hero-badge">
              <div className="hero-badge-icon">
                <Clock className="w-5 h-5" />
              </div>
              <span>Ponctualité</span>
            </div>
            <div className="hero-badge">
              <div className="hero-badge-icon">
                <Shield className="w-5 h-5" />
              </div>
              <span>Confort</span>
            </div>
            <div className="hero-badge">
              <div className="hero-badge-icon">
                <CreditCard className="w-5 h-5" />
              </div>
              <span>Prix clair</span>
            </div>
          </div>
        </div>
      </section>

      {/* Form Section */}
      <section className="px-4 sm:px-5 pb-32 sm:pb-12 overflow-x-hidden">
        <div className="max-w-lg mx-auto w-full">
          <form 
            onSubmit={handleSubmit} 
            className="card-light p-5 sm:p-6 md:p-8 animate-slideUp overflow-x-hidden"
            data-testid="booking-form"
            style={{ maxWidth: '100%' }}
          >
            {/* Name */}
            <div className="mb-5">
              <label htmlFor="name" className="form-label">
                Nom complet *
              </label>
              <div className="relative">
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Jean Dupont"
                  className="form-input"
                  data-testid="input-name"
                  required
                />
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Phone */}
            <div className="mb-5">
              <label htmlFor="phone" className="form-label">
                Téléphone *
              </label>
              <div className="relative">
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="06 12 34 56 78"
                  className={`form-input ${phoneError ? 'input-error' : ''}`}
                  data-testid="input-phone"
                  required
                />
                <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
              {phoneError && <p className="error-message">{phoneError}</p>}
            </div>

            {/* Email */}
            <div className="mb-5">
              <label htmlFor="email" className="form-label">
                Email (optionnel)
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="jean@example.com"
                  className="form-input"
                  data-testid="input-email"
                />
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Pickup Address */}
            <div className="mb-5">
              <label htmlFor="pickup_address" className="form-label">
                Adresse de départ *
              </label>
              <div className="relative">
                <input
                  id="pickup_address"
                  name="pickup_address"
                  type="text"
                  value={formData.pickup_address}
                  onChange={handleChange}
                  placeholder="123 Rue de Paris, 75001 Paris"
                  className="form-input"
                  data-testid="input-pickup"
                  required
                />
                <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-emerald-500" />
              </div>
            </div>

            {/* Dropoff Address */}
            <div className="mb-5">
              <label htmlFor="dropoff_address" className="form-label">
                Adresse d'arrivée *
              </label>
              <div className="relative">
                <input
                  id="dropoff_address"
                  name="dropoff_address"
                  type="text"
                  value={formData.dropoff_address}
                  onChange={handleChange}
                  placeholder="Aéroport CDG Terminal 2E"
                  className="form-input"
                  data-testid="input-dropoff"
                  required
                />
                <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-red-500" />
              </div>
            </div>

            {/* Price Estimation */}
            <div className="mb-6 p-4 bg-gradient-to-r from-[#0a0a0a] to-[#1a1a1a] rounded-xl border border-white/10" data-testid="price-estimation">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#7dd3fc] rounded-xl flex items-center justify-center">
                    <Euro className="w-5 h-5 text-[#0a0a0a]" />
                  </div>
                  <div>
                    <p className="text-white/60 text-sm">Prix estimé de la course</p>
                    {priceLoading ? (
                      <div className="flex items-center gap-2 mt-1">
                        <Loader2 className="w-4 h-4 text-[#7dd3fc] spinner" />
                        <span className="text-white/40 text-sm">Calcul en cours...</span>
                      </div>
                    ) : priceData ? (
                      <p className="text-white font-bold text-2xl" style={{ fontFamily: 'Manrope, sans-serif' }}>
                        {priceData.estimated_price}€
                      </p>
                    ) : (
                      <p className="text-white/40 text-sm mt-1">Entrez les adresses pour estimer</p>
                    )}
                  </div>
                </div>
                {priceData && (
                  <div className="text-right">
                    <p className="text-white/40 text-xs">{priceData.distance_km} km</p>
                    <p className="text-white/40 text-xs">{priceData.duration_min} min</p>
                  </div>
                )}
              </div>
              <p className="text-white/30 text-xs mt-3">Prix estimatif — minimum 10€</p>
            </div>

            {/* Date & Time */}
            <div className="flex flex-col md:flex-row gap-3 md:gap-4 mb-5">
              <div className="flex-1 min-w-0">
                <label htmlFor="date" className="form-label">
                  Date *
                </label>
                <input
                  id="date"
                  name="date"
                  type="date"
                  value={formData.date}
                  onChange={handleChange}
                  min={today}
                  className="form-input-datetime"
                  data-testid="input-date"
                  required
                />
              </div>
              <div className="flex-1 min-w-0">
                <label htmlFor="time" className="form-label">
                  Heure *
                </label>
                <input
                  id="time"
                  name="time"
                  type="time"
                  value={formData.time}
                  onChange={handleChange}
                  className="form-input-datetime"
                  data-testid="input-time"
                  required
                />
              </div>
            </div>

            {/* Passengers */}
            <div className="mb-5">
              <label htmlFor="passengers" className="form-label">
                Nombre de passagers
              </label>
              <div className="relative">
                <select
                  id="passengers"
                  name="passengers"
                  value={formData.passengers}
                  onChange={handleChange}
                  className="form-input form-select"
                  data-testid="input-passengers"
                >
                  {[1, 2, 3, 4, 5, 6, 7].map(n => (
                    <option key={n} value={n}>{n} passager{n > 1 ? 's' : ''}</option>
                  ))}
                </select>
                <Users className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Luggage */}
            <div className="mb-5">
              <label htmlFor="luggage" className="form-label">
                Bagages (optionnel)
              </label>
              <div className="relative">
                <input
                  id="luggage"
                  name="luggage"
                  type="text"
                  value={formData.luggage}
                  onChange={handleChange}
                  placeholder="2 valises, 1 sac cabine"
                  className="form-input"
                  data-testid="input-luggage"
                />
                <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Notes */}
            <div className="mb-6">
              <label htmlFor="notes" className="form-label">
                Note au chauffeur (optionnel)
              </label>
              <div className="relative">
                <textarea
                  id="notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  placeholder="Instructions spéciales, numéro de vol, siège bébé..."
                  className="form-input form-textarea"
                  data-testid="input-notes"
                />
                <MessageSquare className="absolute left-4 top-4 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Desktop Submit Button */}
            <div className="hidden sm:block">
              <button
                type="submit"
                disabled={loading}
                className="submit-btn"
                data-testid="submit-booking"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 spinner" />
                    Réservation en cours...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Confirmer la réservation
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Mobile Sticky Submit Button */}
          <div className="sm:hidden sticky-btn-mobile">
            <button
              type="submit"
              form="booking-form"
              disabled={loading}
              onClick={handleSubmit}
              className="submit-btn"
              data-testid="submit-booking-mobile"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 spinner" />
                  Réservation en cours...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Confirmer la réservation
                </>
              )}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
