import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { 
  MapPin, Calendar, Users, Briefcase, MessageSquare, 
  Phone, Mail, Loader2, Clock, CheckCircle, Shield,
  User, Euro, Headphones
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/ui_pack/logo_original.png";
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

// Pricing constants
const PRICE_PER_KM = 1.50;
const PRICE_PER_MIN = 0.50;
const MIN_PRICE = 10;

// Booking delay requirement (in hours)
const MIN_BOOKING_DELAY_HOURS = 6;

// French phone validation regex
const PHONE_REGEX = /^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$/;

// Track if Google Maps script is loaded
let googleMapsLoaded = false;
let googleMapsLoading = false;
let mapsReadyCallbacks = [];

// Global function to notify when maps is ready
const notifyMapsReady = () => {
  googleMapsLoaded = true;
  googleMapsLoading = false;
  mapsReadyCallbacks.forEach(cb => cb());
  mapsReadyCallbacks = [];
};

// Load Google Maps once
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
    script.onerror = () => {
      googleMapsLoading = false;
      console.error("Failed to load Google Maps script");
      delete window[callbackName];
    };
    
    document.head.appendChild(script);
  });
};

// Premium Neon Background Component
const PremiumBackground = () => {
  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Dark gradient base */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#030B1A] via-[#020617] to-[#030B1A]" />
      
      {/* Animated grid */}
      <div 
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage: `
            linear-gradient(rgba(46, 167, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(46, 167, 255, 0.05) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
          animation: 'gridMove 25s linear infinite'
        }}
      />
      
      {/* Neon routes - animated glow paths */}
      <svg className="absolute inset-0 w-full h-full" style={{ opacity: 0.6 }}>
        <defs>
          <linearGradient id="neonGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="50%" stopColor="#00B6FF" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* Animated route paths */}
        <path
          d="M-50,200 Q200,150 400,250 T800,180 T1200,280"
          stroke="url(#neonGradient)"
          strokeWidth="2"
          fill="none"
          filter="url(#glow)"
          className="animate-route-1"
        />
        <path
          d="M-50,400 Q300,350 500,450 T900,380"
          stroke="url(#neonGradient)"
          strokeWidth="2"
          fill="none"
          filter="url(#glow)"
          className="animate-route-2"
        />
        <path
          d="M100,600 Q400,550 600,650 T1100,580"
          stroke="url(#neonGradient)"
          strokeWidth="1.5"
          fill="none"
          filter="url(#glow)"
          className="animate-route-3"
        />
      </svg>
      
      {/* Radial glow center */}
      <div 
        className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px]"
        style={{
          background: 'radial-gradient(ellipse, rgba(0, 182, 255, 0.08) 0%, transparent 70%)',
        }}
      />
      
      {/* Floating particles */}
      <div className="particles-premium">
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="particle-premium"
            style={{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 15}s`,
              animationDuration: `${18 + Math.random() * 12}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
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

  // Load Google Maps script manually
  useEffect(() => {
    if (!GOOGLE_MAPS_API_KEY) {
      console.warn("Google Maps API key not configured");
      return;
    }

    loadGoogleMapsScript().then(() => {
      if (window.google?.maps?.places) {
        setMapsReady(true);
      }
    });
  }, []);

  // Initialize Autocomplete when maps is ready
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
          if (place && place.formatted_address) {
            setFormData(prev => ({
              ...prev,
              [fieldName]: place.formatted_address
            }));
            if (inputRef.current) {
              inputRef.current.value = place.formatted_address;
            }
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

          if (status === "OK" && 
              response?.rows?.[0]?.elements?.[0]?.status === "OK") {
            
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
      console.error("Price calculation error:", error);
      setPriceLoading(false);
      setPriceData(null);
    }
  }, []);

  useEffect(() => {
    if (!mapsReady) return;
    
    const timer = setTimeout(() => {
      triggerPriceCalculation();
    }, 1000);

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
      
      const hours = String(minTime.getHours()).padStart(2, '0');
      const minutes = String(minTime.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
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

  const autoCorrectTime = (date, time) => {
    if (!date || !time) return time;
    
    const minTime = getMinTime(date);
    if (!minTime) return time;
    
    if (time < minTime) {
      return minTime;
    }
    return time;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    if (name === "date") {
      const correctedTime = autoCorrectTime(value, formData.time);
      setFormData(prev => ({ 
        ...prev, 
        date: value,
        time: correctedTime
      }));
    } else if (name === "time") {
      const correctedTime = autoCorrectTime(formData.date, value);
      setFormData(prev => ({ ...prev, time: correctedTime }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    
    if (name === "phone") {
      setPhoneError("");
    }
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

    if (!submissionData.name || !actualPickup || !actualDropoff || 
        !submissionData.date || !submissionData.time) {
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
      console.error("Booking error:", error);
      toast.error("Erreur lors de la réservation. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Premium Animated Background */}
      <PremiumBackground />
      
      {/* Content Container */}
      <div className="relative z-10">
        
        {/* Premium Header */}
        <header className="fixed top-0 left-0 right-0 z-50 px-4 py-3 bg-[#030B1A]/80 backdrop-blur-xl border-b border-white/5">
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#00B6FF]/50 to-transparent" />
          
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img 
                src={LOGO_URL}
                alt="JABADRIVER" 
                className="h-10 w-auto hero-logo-glow"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <a 
                href="/driver/login" 
                className="btn-gold"
                data-testid="driver-space-link"
              >
                <span className="text-base">🚗</span>
                <span className="hidden sm:inline">Chauffeur</span>
              </a>
              <a 
                href="/admin" 
                className="btn-neon"
                data-testid="admin-link"
              >
                <span className="text-base">⚙️</span>
                <span className="hidden sm:inline">Admin</span>
              </a>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <section className="pt-28 sm:pt-32 pb-8 px-4">
          <div className="max-w-4xl mx-auto text-center">
            {/* Logo Hero */}
            <div className="mb-6 animate-fade-up">
              <img 
                src={LOGO_URL}
                alt="JABADRIVER"
                className="h-20 sm:h-28 w-auto mx-auto hero-logo-pulse"
              />
            </div>
            
            {/* Tagline */}
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-3 animate-fade-up animate-delay-1" style={{ fontFamily: 'Manrope, sans-serif', letterSpacing: '-0.02em' }}>
              LA MOBILITÉ <span className="text-gradient-neon">PREMIUM</span>
            </h1>
            <h2 className="text-lg sm:text-xl text-white/60 font-light tracking-wider animate-fade-up animate-delay-2">
              EN ÎLE-DE-FRANCE
            </h2>
            
            {/* Signature */}
            <p className="mt-4 text-sm text-[#00B6FF]/80 tracking-[0.3em] uppercase animate-fade-up animate-delay-3">
              Rapide • Sûr • Élégant
            </p>
          </div>
        </section>

        {/* Feature Tiles */}
        <section className="px-4 pb-8">
          <div className="max-w-2xl mx-auto">
            <div className="flex flex-wrap justify-center gap-3 animate-fade-up animate-delay-3">
              <div className="value-tile">
                <div className="value-icon">
                  <Clock className="w-5 h-5" />
                </div>
                <span className="value-text">Ponctualité</span>
              </div>
              <div className="value-tile">
                <div className="value-icon">
                  <Shield className="w-5 h-5" />
                </div>
                <span className="value-text">Confort</span>
              </div>
              <div className="value-tile">
                <div className="value-icon">
                  <Euro className="w-5 h-5" />
                </div>
                <span className="value-text">Prix clair</span>
              </div>
            </div>
          </div>
        </section>

        {/* Booking Form Card */}
        <section className="px-4 pb-32 sm:pb-16">
          <div className="max-w-lg mx-auto">
            <form 
              onSubmit={handleSubmit}
              id="booking-form"
              className="premium-form-card animate-fade-up animate-delay-4"
              data-testid="booking-form"
            >
              <h3 className="form-title-premium">
                RÉSERVEZ VOTRE VTC — EN 1 CLIC
              </h3>

              {/* Name */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Nom complet *
                </label>
                <div className="relative input-group-premium">
                  <User className="input-icon-premium w-5 h-5" />
                  <input
                    name="name"
                    type="text"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="Jean Dupont"
                    className="input-premium"
                    data-testid="input-name"
                    required
                  />
                </div>
              </div>

              {/* Phone */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Téléphone *
                </label>
                <div className="relative input-group-premium">
                  <Phone className="input-icon-premium w-5 h-5" />
                  <input
                    name="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="06 12 34 56 78"
                    className={`input-premium ${phoneError ? 'border-red-500' : ''}`}
                    data-testid="input-phone"
                    required
                  />
                </div>
                {phoneError && <p className="text-red-400 text-xs mt-1">{phoneError}</p>}
              </div>

              {/* Email */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Email (optionnel)
                </label>
                <div className="relative input-group-premium">
                  <Mail className="input-icon-premium w-5 h-5" />
                  <input
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="jean@example.com"
                    className="input-premium"
                    data-testid="input-email"
                  />
                </div>
              </div>

              {/* Pickup Address */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Adresse de départ *
                </label>
                <div className="relative input-group-premium">
                  <MapPin className="input-icon-premium w-5 h-5 text-emerald-400" />
                  <input
                    ref={pickupInputRef}
                    name="pickup_address"
                    type="text"
                    defaultValue={formData.pickup_address}
                    onChange={handleChange}
                    placeholder="Entrez une adresse..."
                    className="input-premium"
                    data-testid="input-pickup"
                    autoComplete="off"
                    required
                  />
                </div>
              </div>

              {/* Dropoff Address */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Adresse d'arrivée *
                </label>
                <div className="relative input-group-premium">
                  <MapPin className="input-icon-premium w-5 h-5 text-red-400" />
                  <input
                    ref={dropoffInputRef}
                    name="dropoff_address"
                    type="text"
                    defaultValue={formData.dropoff_address}
                    onChange={handleChange}
                    placeholder="Entrez une adresse..."
                    className="input-premium"
                    data-testid="input-dropoff"
                    autoComplete="off"
                    required
                  />
                </div>
              </div>

              {/* Price Display */}
              <div className="price-display-premium mb-4" data-testid="price-estimation">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 bg-gradient-to-br from-[#00B6FF] to-[#2EA7FF] rounded-xl flex items-center justify-center shadow-lg shadow-[#00B6FF]/30">
                      <Euro className="w-5 h-5 text-[#030B1A]" />
                    </div>
                    <div>
                      <p className="text-white/50 text-xs font-medium uppercase tracking-wider">Prix estimé</p>
                      {priceLoading ? (
                        <div className="flex items-center gap-2 mt-1">
                          <Loader2 className="w-4 h-4 text-[#00B6FF] animate-spin" />
                          <span className="text-white/40 text-sm">Calcul...</span>
                        </div>
                      ) : priceData ? (
                        <p className="price-value-premium">{priceData.estimated_price}€</p>
                      ) : (
                        <p className="text-white/30 text-sm mt-0.5">Entrez les adresses</p>
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
              </div>

              {/* Date & Time */}
              <div className="flex gap-3 mb-4">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                    Date *
                  </label>
                  <input
                    name="date"
                    type="date"
                    value={formData.date}
                    onChange={handleChange}
                    min={today}
                    className="input-premium !pl-4"
                    data-testid="input-date"
                    required
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                    Heure *
                  </label>
                  <input
                    name="time"
                    type="time"
                    value={formData.time}
                    onChange={handleChange}
                    min={getMinTime(formData.date)}
                    className="input-premium !pl-4"
                    data-testid="input-time"
                    required
                  />
                </div>
              </div>
              
              <p className="text-xs text-white/40 mb-4 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Minimum {MIN_BOOKING_DELAY_HOURS}h à l'avance
              </p>

              {/* Passengers */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Passagers
                </label>
                <div className="relative input-group-premium">
                  <Users className="input-icon-premium w-5 h-5" />
                  <select
                    name="passengers"
                    value={formData.passengers}
                    onChange={handleChange}
                    className="input-premium appearance-none cursor-pointer"
                    data-testid="input-passengers"
                  >
                    {[1,2,3,4,5,6,7].map(n => (
                      <option key={n} value={n}>{n} passager{n > 1 ? 's' : ''}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Luggage */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Bagages (optionnel)
                </label>
                <div className="relative input-group-premium">
                  <Briefcase className="input-icon-premium w-5 h-5" />
                  <input
                    name="luggage"
                    type="text"
                    value={formData.luggage}
                    onChange={handleChange}
                    placeholder="2 valises, 1 sac cabine"
                    className="input-premium"
                    data-testid="input-luggage"
                  />
                </div>
              </div>

              {/* Notes */}
              <div className="mb-6">
                <label className="block text-xs font-semibold text-white/50 mb-2 uppercase tracking-wider">
                  Note au chauffeur (optionnel)
                </label>
                <div className="relative input-group-premium">
                  <MessageSquare className="absolute left-4 top-4 w-5 h-5 text-white/40" />
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder="Instructions spéciales, numéro de vol..."
                    className="input-premium !h-24 !pt-4 resize-none"
                    data-testid="input-notes"
                  />
                </div>
              </div>

              {/* CTA Button */}
              <button
                type="submit"
                disabled={loading || !isDateTimeValid()}
                className="cta-premium"
                data-testid="submit-booking"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Réservation en cours...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    RÉSERVER MAINTENANT
                  </>
                )}
              </button>

              {/* Support Info */}
              <div className="mt-4 text-center">
                <p className="text-xs text-white/40">
                  Annulation gratuite jusqu'à 1h avant
                </p>
                <a 
                  href="https://wa.me/message/MQ6BTZ7KU26OM1" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-[#25D366] hover:underline"
                >
                  Support WhatsApp
                </a>
              </div>
            </form>
          </div>
        </section>

        {/* Bottom Badges */}
        <section className="px-4 pb-24 sm:pb-16">
          <div className="max-w-2xl mx-auto">
            <div className="flex flex-wrap justify-center gap-3">
              <div className="badge-premium">
                <div className="badge-icon-premium">
                  <Clock className="w-4 h-4" />
                </div>
                <span>Disponible 24/7</span>
              </div>
              <div className="badge-premium">
                <div className="badge-icon-premium">
                  <CheckCircle className="w-4 h-4" />
                </div>
                <span>Chauffeurs vérifiés</span>
              </div>
              <div className="badge-premium">
                <div className="badge-icon-premium">
                  <Headphones className="w-4 h-4" />
                </div>
                <span>Support tel</span>
              </div>
            </div>
          </div>
        </section>

        {/* Mobile Sticky CTA */}
        <div className="sm:hidden fixed bottom-0 left-0 right-0 p-4 bg-[#030B1A]/95 backdrop-blur-xl border-t border-white/5 z-40">
          <button
            type="submit"
            form="booking-form"
            disabled={loading || !isDateTimeValid()}
            onClick={handleSubmit}
            className="cta-premium"
            data-testid="submit-booking-mobile"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Réservation...
              </>
            ) : (
              <>
                <CheckCircle className="w-5 h-5" />
                RÉSERVER MAINTENANT
              </>
            )}
          </button>
        </div>
      </div>

      {/* WhatsApp Floating Button */}
      <a
        href="https://wa.me/message/MQ6BTZ7KU26OM1"
        target="_blank"
        rel="noopener noreferrer"
        className="whatsapp-btn"
        aria-label="Contact WhatsApp"
      >
        <svg viewBox="0 0 24 24" className="w-7 h-7 text-white fill-current">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
        </svg>
      </a>

      {/* Inline Styles for animations */}
      <style>{`
        @keyframes gridMove {
          0% { transform: translate(0, 0); }
          100% { transform: translate(60px, 60px); }
        }
        
        .hero-logo-glow {
          filter: drop-shadow(0 0 10px rgba(0, 182, 255, 0.3));
        }
        
        .hero-logo-pulse {
          animation: logoPulse 3s ease-in-out infinite;
        }
        
        @keyframes logoPulse {
          0%, 100% { 
            filter: drop-shadow(0 0 20px rgba(0, 182, 255, 0.4));
            transform: scale(1);
          }
          50% { 
            filter: drop-shadow(0 0 40px rgba(0, 182, 255, 0.6));
            transform: scale(1.02);
          }
        }
        
        .text-gradient-neon {
          background: linear-gradient(135deg, #00B6FF 0%, #2EA7FF 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 20px rgba(0, 182, 255, 0.5));
        }
        
        .animate-route-1 { animation: routeGlow 4s ease-in-out infinite; }
        .animate-route-2 { animation: routeGlow 4s ease-in-out infinite 1.3s; }
        .animate-route-3 { animation: routeGlow 4s ease-in-out infinite 2.6s; }
        
        @keyframes routeGlow {
          0%, 100% { opacity: 0.2; stroke-width: 1.5; }
          50% { opacity: 0.8; stroke-width: 2.5; }
        }
        
        .particles-premium {
          position: absolute;
          inset: 0;
          overflow: hidden;
          pointer-events: none;
        }
        
        .particle-premium {
          position: absolute;
          width: 3px;
          height: 3px;
          background: #00B6FF;
          border-radius: 50%;
          filter: blur(1px);
          opacity: 0;
          animation: particleRise 20s linear infinite;
        }
        
        @keyframes particleRise {
          0% { transform: translateY(100vh); opacity: 0; }
          10% { opacity: 0.5; }
          90% { opacity: 0.5; }
          100% { transform: translateY(-10vh); opacity: 0; }
        }
        
        .animate-fade-up {
          animation: fadeInUp 0.6s ease-out forwards;
          opacity: 0;
        }
        
        .animate-delay-1 { animation-delay: 0.1s; }
        .animate-delay-2 { animation-delay: 0.2s; }
        .animate-delay-3 { animation-delay: 0.3s; }
        .animate-delay-4 { animation-delay: 0.4s; }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        /* Input date/time dark styling */
        .input-premium::-webkit-calendar-picker-indicator {
          filter: invert(1);
          opacity: 0.5;
        }
        
        /* Select arrow */
        .input-premium option {
          background: #030B1A;
          color: white;
        }
      `}</style>
    </div>
  );
}
