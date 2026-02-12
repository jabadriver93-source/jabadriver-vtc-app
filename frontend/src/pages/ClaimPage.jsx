import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MapPin, Clock, Euro, User, Phone, AlertCircle, CheckCircle2, Timer, CreditCard } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ClaimPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [claimData, setClaimData] = useState(null);
  const [error, setError] = useState(null);
  const [reserving, setReserving] = useState(false);
  const [paying, setPaying] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Check for payment cancelled
  useEffect(() => {
    if (searchParams.get('payment') === 'cancelled') {
      toast.error('Paiement annulé');
    }
  }, [searchParams]);

  const fetchClaimInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/subcontracting/claim/${token}`);
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Lien invalide');
      }
      
      setClaimData(data);
      if (data.time_remaining_seconds !== null) {
        setTimeRemaining(data.time_remaining_seconds);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    const driverToken = localStorage.getItem('driver_token');
    setIsLoggedIn(!!driverToken);
    fetchClaimInfo();
  }, [fetchClaimInfo]);

  // Countdown timer
  useEffect(() => {
    if (timeRemaining === null || timeRemaining <= 0) return;
    
    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          fetchClaimInfo(); // Refresh when timer expires
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [timeRemaining, fetchClaimInfo]);

  const handleReserve = async () => {
    const driverToken = localStorage.getItem('driver_token');
    if (!driverToken) {
      // Save current URL and redirect to login
      sessionStorage.setItem('claim_redirect', `/claim/${token}`);
      navigate('/driver/login');
      return;
    }
    
    setReserving(true);
    try {
      const res = await fetch(`${API_URL}/api/subcontracting/claim/${token}/reserve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${driverToken}` }
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur réservation');
      }
      
      toast.success(data.message);
      fetchClaimInfo();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setReserving(false);
    }
  };

  const handlePay = async () => {
    const driverToken = localStorage.getItem('driver_token');
    if (!driverToken) {
      navigate('/driver/login');
      return;
    }
    
    setPaying(true);
    try {
      const res = await fetch(`${API_URL}/api/subcontracting/claim/${token}/pay`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${driverToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ origin_url: window.location.origin })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur paiement');
      }
      
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(err.message);
      setPaying(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-slate-800/50 border-slate-700">
          <CardContent className="py-12 text-center">
            <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl text-white mb-2">Lien invalide</h2>
            <p className="text-slate-400">{error}</p>
            <Button 
              className="mt-6"
              onClick={() => navigate('/')}
            >
              Retour à l'accueil
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const course = claimData?.course;
  const isReservedByMe = claimData?.course?.status === 'RESERVED' && timeRemaining > 0;
  const isAssigned = claimData?.course?.status === 'ASSIGNED';
  const isOpen = claimData?.course?.status === 'OPEN';
  const isReservedByOther = claimData?.course?.status === 'RESERVED' && claimData?.reserved_by && !isReservedByMe;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        <Card className="bg-slate-800/50 border-slate-700" data-testid="claim-card">
          <CardHeader className="border-b border-slate-700">
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl text-white">Course Disponible</CardTitle>
                <p className="text-slate-400 text-sm mt-1">
                  Commission: {(claimData?.commission_rate * 100).toFixed(0)}% = {claimData?.commission_amount?.toFixed(2)} €
                </p>
              </div>
              
              {/* Status Badge */}
              {isAssigned && (
                <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30 text-sm flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  Attribuée
                </span>
              )}
              {isReservedByMe && (
                <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-sm flex items-center gap-1">
                  <Timer className="w-4 h-4" />
                  {formatTime(timeRemaining)}
                </span>
              )}
              {isReservedByOther && (
                <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 text-sm">
                  Réservée
                </span>
              )}
              {isOpen && (
                <span className="px-3 py-1 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 text-sm">
                  Disponible
                </span>
              )}
            </div>
          </CardHeader>
          
          <CardContent className="p-6">
            {/* Course Details */}
            <div className="space-y-4 mb-6">
              <div className="flex items-center gap-3">
                <User className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-slate-500 text-xs">Client</p>
                  <p className="text-white">{course?.client_name}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-slate-500 text-xs">Date & Heure</p>
                  <p className="text-white">{course?.date} à {course?.time}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="text-slate-500 text-xs">Départ</p>
                    <p className="text-white text-sm">{course?.pickup_address}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-red-400 mt-0.5" />
                  <div>
                    <p className="text-slate-500 text-xs">Arrivée</p>
                    <p className="text-white text-sm">{course?.dropoff_address}</p>
                  </div>
                </div>
              </div>
              
              {course?.distance_km && (
                <div className="flex items-center gap-3">
                  <span className="text-slate-400">📏</span>
                  <div>
                    <p className="text-slate-500 text-xs">Distance</p>
                    <p className="text-white">{course?.distance_km} km</p>
                  </div>
                </div>
              )}
              
              {course?.notes && (
                <div className="bg-slate-700/30 p-3 rounded-lg">
                  <p className="text-slate-500 text-xs mb-1">Notes</p>
                  <p className="text-slate-300 text-sm">{course?.notes}</p>
                </div>
              )}
            </div>
            
            {/* Price */}
            <div className="bg-slate-700/50 p-4 rounded-lg mb-6">
              <div className="flex justify-between items-center">
                <span className="text-slate-300">Prix de la course</span>
                <span className="text-2xl font-bold text-white flex items-center gap-1">
                  <Euro className="w-6 h-6" />
                  {course?.price_total?.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-600">
                <span className="text-slate-400 text-sm">Commission à payer ({(claimData?.commission_rate * 100).toFixed(0)}%)</span>
                <span className="text-amber-400 font-medium">{claimData?.commission_amount?.toFixed(2)} €</span>
              </div>
            </div>
            
            {/* Actions */}
            {isAssigned ? (
              <div className="text-center py-4">
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-2" />
                <p className="text-green-400 font-medium">Cette course est déjà attribuée</p>
              </div>
            ) : isReservedByOther ? (
              <div className="text-center py-4">
                <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-2" />
                <p className="text-amber-400 font-medium">
                  Réservée par {claimData?.reserved_by}
                </p>
                <p className="text-slate-400 text-sm mt-1">
                  {timeRemaining > 0 
                    ? `Expire dans ${formatTime(timeRemaining)}`
                    : 'Réessayez dans quelques instants'}
                </p>
              </div>
            ) : isReservedByMe ? (
              <div className="space-y-4">
                <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-lg text-center">
                  <Timer className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                  <p className="text-amber-400 font-medium">
                    Vous avez réservé cette course
                  </p>
                  <p className="text-slate-400 text-sm">
                    Temps restant: <span className="text-white font-mono">{formatTime(timeRemaining)}</span>
                  </p>
                </div>
                <Button
                  className="w-full bg-green-600 hover:bg-green-700 h-12"
                  onClick={handlePay}
                  disabled={paying}
                  data-testid="pay-commission-btn"
                >
                  <CreditCard className="w-5 h-5 mr-2" />
                  {paying ? 'Redirection...' : `Payer ${claimData?.commission_amount?.toFixed(2)} € pour confirmer`}
                </Button>
              </div>
            ) : isOpen ? (
              <div className="space-y-3">
                {!isLoggedIn && (
                  <p className="text-slate-400 text-sm text-center">
                    Connectez-vous pour réserver cette course
                  </p>
                )}
                <Button
                  className="w-full bg-sky-600 hover:bg-sky-700 h-12"
                  onClick={handleReserve}
                  disabled={reserving}
                  data-testid="reserve-course-btn"
                >
                  {reserving ? 'Réservation...' : isLoggedIn ? 'Réserver cette course (3 min)' : 'Se connecter pour réserver'}
                </Button>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-slate-400">Cette course n'est plus disponible</p>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Info */}
        <div className="mt-4 text-center text-slate-500 text-sm">
          <p>En réservant, vous avez 3 minutes pour payer la commission.</p>
          <p>Une fois payée, la course vous est définitivement attribuée.</p>
        </div>
      </div>
    </div>
  );
}
