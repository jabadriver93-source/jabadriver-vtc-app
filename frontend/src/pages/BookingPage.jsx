import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { 
  MapPin, Calendar, Users, Briefcase, MessageSquare, 
  Phone, Mail, Loader2, Clock, CheckCircle, Shield, CreditCard,
  User
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/logo.png";

// French phone validation regex
const PHONE_REGEX = /^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}$/;

export default function BookingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [phoneError, setPhoneError] = useState("");
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
      const response = await axios.post(`${API}/reservations`, formData);
      toast.success("Réservation enregistrée !");
      navigate(`/confirmation/${response.data.id}`);
    } catch (error) {
      console.error("Booking error:", error);
      toast.error("Erreur lors de la réservation. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  // Get min date (today) and min time
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
      <section className="px-5 pb-32 sm:pb-12">
        <div className="max-w-lg mx-auto">
          <form 
            onSubmit={handleSubmit} 
            className="card-light p-6 sm:p-8 animate-slideUp"
            data-testid="booking-form"
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

            {/* Date & Time */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              <div>
                <label htmlFor="date" className="form-label">
                  Date *
                </label>
                <div className="relative">
                  <input
                    id="date"
                    name="date"
                    type="date"
                    value={formData.date}
                    onChange={handleChange}
                    min={today}
                    className="form-input !pl-4"
                    data-testid="input-date"
                    required
                  />
                </div>
              </div>
              <div>
                <label htmlFor="time" className="form-label">
                  Heure *
                </label>
                <input
                  id="time"
                  name="time"
                  type="time"
                  value={formData.time}
                  onChange={handleChange}
                  className="form-input !pl-4"
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
