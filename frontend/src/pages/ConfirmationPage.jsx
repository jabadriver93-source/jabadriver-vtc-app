import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  CheckCircle, MapPin, Calendar, Clock, Users, 
  Briefcase, MessageSquare, Phone, ArrowLeft, Loader2, Euro, Route
} from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/logo.png";

export default function ConfirmationPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [reservation, setReservation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReservation = async () => {
      try {
        const response = await axios.get(`${API}/reservations/${id}`);
        setReservation(response.data);
      } catch (error) {
        console.error("Error fetching reservation:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReservation();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#7dd3fc] spinner" />
      </div>
    );
  }

  if (!reservation) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6">
        <p className="text-white/60 mb-4">Réservation non trouvée</p>
        <button 
          onClick={() => navigate("/")} 
          className="text-[#7dd3fc] hover:underline"
        >
          Retour à l'accueil
        </button>
      </div>
    );
  }

  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="px-5 py-5 border-b border-white/10">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <img src={LOGO_URL} alt="JABA DRIVER" className="h-10 w-auto" />
          <span className="text-xl font-bold text-white tracking-tight hidden sm:block" style={{ fontFamily: 'Manrope, sans-serif' }}>
            JABA DRIVER
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-5 py-12">
        <div className="max-w-lg mx-auto">
          {/* Success Icon */}
          <div className="text-center mb-10 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-24 h-24 bg-[#7dd3fc]/20 rounded-full mb-6">
              <CheckCircle className="w-12 h-12 text-[#7dd3fc]" />
            </div>
            <h1 
              className="text-3xl sm:text-4xl font-bold text-white mb-3" 
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              Réservation enregistrée !
            </h1>
            <p className="text-white/50 text-lg">
              Merci <span className="text-white font-medium">{reservation.name}</span>
            </p>
          </div>

          {/* Confirmation Message */}
          <div className="bg-[#7dd3fc]/10 border border-[#7dd3fc]/30 rounded-2xl p-5 mb-8 text-center animate-fadeIn" style={{ animationDelay: '0.1s' }}>
            <p className="text-[#7dd3fc] font-medium">
              On vous confirme rapidement par téléphone
            </p>
          </div>

          {/* Price Card (if available) */}
          {reservation.estimated_price && (
            <div className="bg-gradient-to-r from-[#7dd3fc] to-[#38bdf8] rounded-2xl p-6 mb-8 animate-fadeIn" style={{ animationDelay: '0.15s' }} data-testid="price-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[#0a0a0a]/70 text-sm font-medium">Prix estimé</p>
                  <p className="text-[#0a0a0a] font-extrabold text-4xl" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {Math.round(reservation.estimated_price)}€
                  </p>
                </div>
                <div className="text-right">
                  {reservation.distance_km && (
                    <p className="text-[#0a0a0a]/70 text-sm flex items-center justify-end gap-1">
                      <Route className="w-4 h-4" />
                      {reservation.distance_km} km
                    </p>
                  )}
                  {reservation.duration_min && (
                    <p className="text-[#0a0a0a]/70 text-sm flex items-center justify-end gap-1">
                      <Clock className="w-4 h-4" />
                      {Math.round(reservation.duration_min)} min
                    </p>
                  )}
                </div>
              </div>
              <p className="text-[#0a0a0a]/50 text-xs mt-3">Prix estimatif — minimum 10€</p>
            </div>
          )}

          {/* Reservation Details Card */}
          <div 
            className="card-light p-6 sm:p-8 animate-slideUp" 
            data-testid="confirmation-card"
          >
            {/* Reference */}
            <div className="flex items-center justify-between mb-6 pb-5 border-b border-slate-200">
              <span className="text-sm text-slate-500 font-medium">Référence</span>
              <span 
                className="font-mono text-sm bg-slate-100 px-4 py-2 rounded-lg font-semibold text-slate-700" 
                data-testid="reservation-id"
              >
                #{reservation.id.slice(0, 8).toUpperCase()}
              </span>
            </div>

            {/* Details */}
            <div className="space-y-5">
              {/* Name & Phone */}
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Phone className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Contact</p>
                  <p className="font-semibold text-slate-900">{reservation.name}</p>
                  <p className="text-slate-600">{reservation.phone}</p>
                </div>
              </div>

              {/* Date & Time */}
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 bg-[#7dd3fc]/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Calendar className="w-5 h-5 text-[#0ea5e9]" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Date & Heure</p>
                  <p className="font-semibold text-slate-900">{formatDate(reservation.date)}</p>
                  <p className="text-slate-600 flex items-center gap-1 mt-0.5">
                    <Clock className="w-4 h-4" /> {reservation.time}
                  </p>
                </div>
              </div>

              {/* Pickup */}
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 bg-emerald-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Départ</p>
                  <p className="font-medium text-slate-900">{reservation.pickup_address}</p>
                </div>
              </div>

              {/* Dropoff */}
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Arrivée</p>
                  <p className="font-medium text-slate-900">{reservation.dropoff_address}</p>
                </div>
              </div>

              {/* Passengers */}
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Users className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Passagers</p>
                  <p className="font-medium text-slate-900">{reservation.passengers} passager{reservation.passengers > 1 ? 's' : ''}</p>
                </div>
              </div>

              {/* Luggage */}
              {reservation.luggage && (
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Briefcase className="w-5 h-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500 mb-1">Bagages</p>
                    <p className="font-medium text-slate-900">{reservation.luggage}</p>
                  </div>
                </div>
              )}

              {/* Notes */}
              {reservation.notes && (
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <MessageSquare className="w-5 h-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500 mb-1">Note</p>
                    <p className="font-medium text-slate-900">{reservation.notes}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Back Button */}
          <div className="mt-10 text-center">
            <button 
              onClick={() => navigate("/")} 
              className="inline-flex items-center gap-2 text-white/50 hover:text-white transition-colors"
              data-testid="back-home"
            >
              <ArrowLeft className="w-4 h-4" />
              Nouvelle réservation
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
