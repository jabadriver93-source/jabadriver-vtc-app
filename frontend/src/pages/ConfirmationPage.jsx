import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CheckCircle, MapPin, Calendar, Clock, Users, Briefcase, MessageSquare, Car, Phone, ArrowLeft, Loader2 } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-slate-400 spinner" />
      </div>
    );
  }

  if (!reservation) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
        <p className="text-slate-600 mb-4">Réservation non trouvée</p>
        <Button onClick={() => navigate("/")} variant="outline">
          Retour à l'accueil
        </Button>
      </div>
    );
  }

  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 px-6 py-6">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Car className="w-8 h-8 text-white" />
          <span className="text-2xl font-extrabold text-white tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
            JABADRIVER
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 py-12">
        <div className="max-w-lg mx-auto">
          {/* Success Icon */}
          <div className="text-center mb-8 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-4">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Réservation confirmée !
            </h1>
            <p className="text-slate-500">
              Merci {reservation.name}, votre demande a bien été enregistrée
            </p>
          </div>

          {/* Reservation Details Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 sm:p-8 animate-slideUp" data-testid="confirmation-card">
            {/* Reference */}
            <div className="flex items-center justify-between mb-6 pb-6 border-b border-slate-100">
              <span className="text-sm text-slate-500">Référence</span>
              <span className="font-mono text-sm bg-slate-100 px-3 py-1 rounded-full" data-testid="reservation-id">
                {reservation.id.slice(0, 8).toUpperCase()}
              </span>
            </div>

            {/* Details */}
            <div className="space-y-5">
              {/* Date & Time */}
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Calendar className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Date & Heure</p>
                  <p className="font-semibold text-slate-900">{formatDate(reservation.date)}</p>
                  <p className="text-slate-700 flex items-center gap-1 mt-1">
                    <Clock className="w-4 h-4" /> {reservation.time}
                  </p>
                </div>
              </div>

              {/* Pickup */}
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Départ</p>
                  <p className="font-medium text-slate-900">{reservation.pickup_address}</p>
                </div>
              </div>

              {/* Dropoff */}
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <MapPin className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Arrivée</p>
                  <p className="font-medium text-slate-900">{reservation.dropoff_address}</p>
                </div>
              </div>

              {/* Passengers */}
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
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
                  <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
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
                  <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <MessageSquare className="w-5 h-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500 mb-1">Note</p>
                    <p className="font-medium text-slate-900">{reservation.notes}</p>
                  </div>
                </div>
              )}

              {/* Contact */}
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Phone className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-1">Contact</p>
                  <p className="font-medium text-slate-900">{reservation.phone}</p>
                  {reservation.email && (
                    <p className="text-slate-600 text-sm">{reservation.email}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Info Message */}
            <div className="mt-8 p-4 bg-blue-50 rounded-xl">
              <p className="text-blue-800 text-sm">
                Nous vous contacterons rapidement pour confirmer votre course. Un email de confirmation a été envoyé à votre adresse.
              </p>
            </div>
          </div>

          {/* Back Button */}
          <div className="mt-8 text-center">
            <Button 
              onClick={() => navigate("/")} 
              variant="ghost"
              className="text-slate-600 hover:text-slate-900"
              data-testid="back-home"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Nouvelle réservation
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
