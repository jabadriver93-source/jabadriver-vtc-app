import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Car, MapPin, Calendar, Users, Briefcase, MessageSquare, Phone, Mail, Loader2 } from "lucide-react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BookingPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.name || !formData.phone || !formData.pickup_address || 
        !formData.dropoff_address || !formData.date || !formData.time) {
      toast.error("Veuillez remplir tous les champs obligatoires");
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

  // Get min date (today)
  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen hero-bg">
      {/* Header */}
      <header className="px-6 py-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Car className="w-8 h-8 text-white" />
            <span className="text-2xl font-extrabold text-white tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABADRIVER
            </span>
          </div>
          <a 
            href="/admin" 
            className="text-white/60 hover:text-white text-sm transition-colors"
            data-testid="admin-link"
          >
            Admin
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 pb-12 pt-4">
        <div className="max-w-lg mx-auto">
          {/* Hero Text */}
          <div className="text-center mb-8 animate-fadeIn">
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-3" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Réservez votre VTC
            </h1>
            <p className="text-white/70 text-base sm:text-lg">
              Service premium, confort et ponctualité garantis
            </p>
          </div>

          {/* Booking Form */}
          <form 
            onSubmit={handleSubmit} 
            className="glass-card rounded-2xl p-6 sm:p-8 booking-form animate-slideUp"
            data-testid="booking-form"
          >
            {/* Name */}
            <div className="mb-5">
              <Label htmlFor="name" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Nom complet *
              </Label>
              <div className="relative">
                <Input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Jean Dupont"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-name"
                  required
                />
                <Users className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Phone */}
            <div className="mb-5">
              <Label htmlFor="phone" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Téléphone *
              </Label>
              <div className="relative">
                <Input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="06 12 34 56 78"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-phone"
                  required
                />
                <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Email */}
            <div className="mb-5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Email (optionnel)
              </Label>
              <div className="relative">
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="jean@example.com"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-email"
                />
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Pickup Address */}
            <div className="mb-5">
              <Label htmlFor="pickup_address" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Adresse de départ *
              </Label>
              <div className="relative">
                <Input
                  id="pickup_address"
                  name="pickup_address"
                  type="text"
                  value={formData.pickup_address}
                  onChange={handleChange}
                  placeholder="123 Rue de Paris, 75001 Paris"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-pickup"
                  required
                />
                <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-green-500" />
              </div>
            </div>

            {/* Dropoff Address */}
            <div className="mb-5">
              <Label htmlFor="dropoff_address" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Adresse d'arrivée *
              </Label>
              <div className="relative">
                <Input
                  id="dropoff_address"
                  name="dropoff_address"
                  type="text"
                  value={formData.dropoff_address}
                  onChange={handleChange}
                  placeholder="Aéroport CDG Terminal 2E"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-dropoff"
                  required
                />
                <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-red-500" />
              </div>
            </div>

            {/* Date & Time */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              <div>
                <Label htmlFor="date" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                  Date *
                </Label>
                <div className="relative">
                  <Input
                    id="date"
                    name="date"
                    type="date"
                    value={formData.date}
                    onChange={handleChange}
                    min={today}
                    className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                    data-testid="input-date"
                    required
                  />
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                </div>
              </div>
              <div>
                <Label htmlFor="time" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                  Heure *
                </Label>
                <Input
                  id="time"
                  name="time"
                  type="time"
                  value={formData.time}
                  onChange={handleChange}
                  className="h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-time"
                  required
                />
              </div>
            </div>

            {/* Passengers */}
            <div className="mb-5">
              <Label htmlFor="passengers" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Nombre de passagers
              </Label>
              <div className="relative">
                <select
                  id="passengers"
                  name="passengers"
                  value={formData.passengers}
                  onChange={handleChange}
                  className="w-full pl-12 h-14 bg-slate-100/50 border-2 border-transparent focus:border-blue-500 rounded-xl appearance-none cursor-pointer"
                  data-testid="input-passengers"
                  style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 16px center' }}
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
              <Label htmlFor="luggage" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Bagages (optionnel)
              </Label>
              <div className="relative">
                <Input
                  id="luggage"
                  name="luggage"
                  type="text"
                  value={formData.luggage}
                  onChange={handleChange}
                  placeholder="2 valises, 1 sac"
                  className="pl-12 h-14 bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl"
                  data-testid="input-luggage"
                />
                <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Notes */}
            <div className="mb-6">
              <Label htmlFor="notes" className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 block">
                Note au chauffeur (optionnel)
              </Label>
              <div className="relative">
                <Textarea
                  id="notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  placeholder="Instructions spéciales, numéro de vol..."
                  className="pl-12 pt-4 min-h-[100px] bg-slate-100/50 border-transparent focus:border-blue-500 rounded-xl resize-none"
                  data-testid="input-notes"
                />
                <MessageSquare className="absolute left-4 top-4 w-5 h-5 text-slate-400" />
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={loading}
              className="w-full h-14 bg-slate-900 hover:bg-slate-800 text-white rounded-full font-semibold text-base btn-active"
              data-testid="submit-booking"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 spinner" />
                  Réservation en cours...
                </>
              ) : (
                "Réserver maintenant"
              )}
            </Button>
          </form>

          {/* Footer */}
          <p className="text-center text-white/50 text-sm mt-8">
            En réservant, vous acceptez nos conditions générales
          </p>
        </div>
      </main>
    </div>
  );
}
