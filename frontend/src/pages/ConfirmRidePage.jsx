import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  MapPin, Clock, Euro, User, Loader2, CheckCircle, 
  AlertTriangle, Car, Calendar
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ConfirmRidePage() {
  const { rideId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [ride, setRide] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Lien de confirmation invalide');
      setLoading(false);
      return;
    }
    fetchRide();
  }, [rideId, token]);

  const fetchRide = async () => {
    try {
      const res = await fetch(`${API_URL}/api/driver/confirm-ride/${rideId}?token=${token}`);
      
      if (!res.ok) {
        // Handle error responses
        if (res.status === 403) {
          setError('Ce lien de confirmation n\'est plus valide');
        } else if (res.status === 404) {
          setError('Course non trouvée');
        } else {
          try {
            const data = await res.json();
            setError(data.detail || 'Erreur lors du chargement');
          } catch {
            setError('Erreur lors du chargement');
          }
        }
        return;
      }
      
      const data = await res.json();
      setRide(data);
      
      if (data.already_confirmed) {
        setConfirmed(true);
      }
    } catch (err) {
      console.error('fetchRide error:', err);
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const res = await fetch(`${API_URL}/api/driver/confirm-ride/${rideId}?token=${token}`, {
        method: 'POST'
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        toast.error(data.detail || 'Erreur lors de la confirmation');
        return;
      }
      
      toast.success('Merci ! Votre course a été confirmée.');
      setConfirmed(true);
      setRide(prev => ({ ...prev, status: 'DONE', confirmed_at: data.confirmed_at }));
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setConfirming(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return '-';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '-';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-green-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <Card className="bg-gray-900 border-gray-800 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
            <h2 className="text-xl font-bold text-white mb-2">Erreur</h2>
            <p className="text-gray-400">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Already confirmed state
  if (confirmed || ride?.already_confirmed) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <Card className="bg-gray-900 border-gray-800 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Course confirmée !</h2>
            <p className="text-gray-400 mb-6">
              Merci d'avoir voyagé avec JABADRIVER.
            </p>
            <div className="bg-gray-800 rounded-lg p-4 text-left">
              <p className="text-gray-400 text-sm">Réservation</p>
              <p className="text-white font-mono">#{rideId?.slice(0, 8).toUpperCase()}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 pb-32">
      {/* Header */}
      <div className="bg-gradient-to-b from-green-500/20 to-gray-950 px-4 pt-8 pb-10">
        <div className="max-w-lg mx-auto text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Car className="w-8 h-8 text-green-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Confirmer votre course</h1>
          <p className="text-gray-400 text-sm">
            Merci de confirmer que votre trajet s'est bien déroulé
          </p>
        </div>
      </div>

      <div className="px-4 -mt-4">
        <div className="max-w-lg mx-auto space-y-4">
          
          {/* Hello Client */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-5">
              <p className="text-gray-300">
                Bonjour <span className="text-white font-semibold">{ride?.client_name}</span>,
              </p>
              <p className="text-gray-400 text-sm mt-1">
                Votre chauffeur a indiqué que la course est terminée.
              </p>
            </CardContent>
          </Card>

          {/* Ride Summary */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-5 space-y-4">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Calendar className="w-4 h-4 text-green-400" />
                Récapitulatif
              </h3>
              
              {/* Date & Driver */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Date</p>
                  <p className="text-white text-sm">{formatDate(ride?.date)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Chauffeur</p>
                  <p className="text-white text-sm">{ride?.driver?.company_name || ride?.driver?.name || '-'}</p>
                </div>
              </div>
              
              {/* Timeline */}
              <div className="bg-gray-800/50 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-gray-400 text-xs">Démarrée à {formatTime(ride?.started_at)}</p>
                  </div>
                </div>
                <div className="ml-1 border-l border-dashed border-gray-600 h-3"></div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-gray-400 text-xs">Terminée à {formatTime(ride?.ended_at)}</p>
                  </div>
                </div>
              </div>

              {/* Addresses */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-3">
                  <MapPin className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-gray-400 text-xs">Départ</p>
                    <p className="text-white text-sm">{ride?.pickup_address}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-gray-400 text-xs">Arrivée</p>
                    <p className="text-white text-sm">{ride?.dropoff_address}</p>
                  </div>
                </div>
              </div>

              {/* Price Breakdown */}
              <div className="pt-3 border-t border-gray-700 space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <Euro className="w-4 h-4 text-green-400" />
                  <span className="text-gray-400 font-medium">Détail du prix</span>
                </div>
                
                {/* Base price */}
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Prix initial</span>
                  <span className="text-white">{ride?.totals?.base_price_eur || ride?.price_base || ride?.price_total}€</span>
                </div>
                
                {/* Waiting fee (if any) */}
                {(ride?.totals?.waiting_fee_eur > 0 || ride?.waiting_price > 0) && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Attente ({ride?.totals?.waiting_billable_minutes || ride?.waiting_billable_minutes || 0} min)</span>
                    <span className="text-amber-400">+{ride?.totals?.waiting_fee_eur || ride?.waiting_price || 0}€</span>
                  </div>
                )}
                
                {/* Manual supplements (if any) */}
                {(ride?.totals?.manual_supplements_capped_eur > 0 || 
                  (ride?.supplement_peage || 0) + (ride?.supplement_parking || 0) + (ride?.supplement_traffic || 0) > 0) && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Suppléments</span>
                    <span className="text-amber-400">+{ride?.totals?.manual_supplements_capped_eur || 
                      ((ride?.supplement_peage || 0) + (ride?.supplement_parking || 0) + (ride?.supplement_traffic || 0))}€</span>
                  </div>
                )}
                
                {/* Total */}
                <div className="flex justify-between pt-2 border-t border-gray-700/50">
                  <span className="text-white font-semibold">Total</span>
                  <span className="text-green-400 font-bold text-xl">
                    {ride?.totals?.final_total_eur || ride?.price_with_supplements || ride?.price_total}€
                  </span>
                </div>
                
                {/* Price adjustment notice */}
                {(ride?.totals?.extras_total_eur > 0 || ride?.waiting_price > 0 || 
                  (ride?.supplement_peage || 0) + (ride?.supplement_parking || 0) + (ride?.supplement_traffic || 0) > 0) && (
                  <p className="text-gray-500 text-xs mt-2 text-center">
                    Le prix a été ajusté en fonction des conditions réelles de la course.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Info Box */}
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
            <p className="text-green-400 text-sm text-center">
              En confirmant, vous attestez que la course s'est bien déroulée.
            </p>
          </div>
        </div>
      </div>

      {/* Fixed Bottom Button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent pt-8">
        <div className="max-w-lg mx-auto">
          <Button
            onClick={handleConfirm}
            disabled={confirming}
            className="w-full h-14 bg-green-500 hover:bg-green-600 text-white font-bold text-lg rounded-xl shadow-lg shadow-green-500/20"
            data-testid="confirm-ride-btn"
          >
            {confirming ? (
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
            ) : (
              <CheckCircle className="w-5 h-5 mr-2" />
            )}
            Confirmer ma course
          </Button>
        </div>
      </div>
    </div>
  );
}
