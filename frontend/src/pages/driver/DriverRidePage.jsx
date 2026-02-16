import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  MapPin, Clock, Phone, User, Euro, FileText, 
  Loader2, Play, CheckCircle, AlertTriangle, Car, Navigation
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Status display configuration
const STATUS_CONFIG = {
  ASSIGNED: {
    label: 'Attribuée',
    color: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
    icon: Car
  },
  IN_PROGRESS: {
    label: 'En cours',
    color: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    icon: Navigation
  },
  DRIVER_COMPLETED: {
    label: 'Terminée chauffeur',
    color: 'bg-green-500/20 text-green-400 border-green-500/30',
    icon: CheckCircle
  },
  DONE: {
    label: 'Terminée',
    color: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    icon: CheckCircle
  }
};

export default function DriverRidePage() {
  const { rideId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [ride, setRide] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Token d\'accès manquant');
      setLoading(false);
      return;
    }
    fetchRide();
  }, [rideId, token]);

  const fetchRide = async () => {
    try {
      const res = await fetch(`${API_URL}/api/driver/ride/${rideId}?token=${token}`);
      
      if (!res.ok) {
        const data = await res.json();
        if (res.status === 403) {
          setError(data.detail || 'Accès refusé');
        } else if (res.status === 404) {
          setError('Course non trouvée');
        } else {
          setError(data.detail || 'Erreur lors du chargement');
        }
        return;
      }
      
      const data = await res.json();
      setRide(data);
    } catch (err) {
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const handleStartRide = async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/driver/ride/${rideId}/start?token=${token}`, {
        method: 'POST'
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        toast.error(data.detail || 'Erreur lors du démarrage');
        return;
      }
      
      toast.success(data.message || 'Course démarrée !');
      fetchRide(); // Refresh data
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEndRide = async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/driver/ride/${rideId}/end?token=${token}`, {
        method: 'POST'
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        toast.error(data.detail || 'Erreur lors de la finalisation');
        return;
      }
      
      toast.success(data.message || 'Course terminée !');
      fetchRide(); // Refresh data
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setActionLoading(false);
    }
  };

  const downloadPDF = async (type) => {
    // Use standard driver auth for PDF download
    const driverToken = localStorage.getItem('driver_token');
    if (!driverToken) {
      toast.error('Connexion requise pour télécharger les documents');
      return;
    }
    
    try {
      const endpoint = type === 'bon' 
        ? `${API_URL}/api/driver/courses/${rideId}/bon-commande-pdf`
        : `${API_URL}/api/driver/courses/${rideId}/invoice-pdf`;
      
      const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${driverToken}` }
      });
      
      if (!res.ok) {
        toast.error('Erreur téléchargement');
        return;
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = type === 'bon' ? `bon-commande-${rideId.slice(0,8)}.pdf` : `facture-${rideId.slice(0,8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Erreur téléchargement');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: 'numeric',
        month: 'long'
      });
    } catch {
      return dateStr;
    }
  };

  const formatTime = (timeStr) => {
    if (!timeStr) return '-';
    return timeStr;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
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

  const statusConfig = STATUS_CONFIG[ride?.status] || STATUS_CONFIG.ASSIGNED;
  const StatusIcon = statusConfig.icon;
  const netDriver = (ride?.price_with_supplements || ride?.price_total || 0) - (ride?.commission_amount || 0);

  return (
    <div className="min-h-screen bg-gray-950 pb-32">
      {/* Header */}
      <div className="bg-gradient-to-b from-amber-500/20 to-gray-950 px-4 pt-6 pb-8">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold text-white">Ma Course</h1>
            <span className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${statusConfig.color} flex items-center gap-1.5`}>
              <StatusIcon className="w-3.5 h-3.5" />
              {statusConfig.label}
            </span>
          </div>
          
          {/* Course ID */}
          <p className="text-gray-400 text-sm">
            Réservation <span className="font-mono text-white">#{ride?.id?.slice(0, 8).toUpperCase()}</span>
          </p>
        </div>
      </div>

      <div className="px-4 -mt-2">
        <div className="max-w-lg mx-auto space-y-4">
          
          {/* Date & Time Card */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-amber-500/20 rounded-xl flex items-center justify-center">
                  <Clock className="w-6 h-6 text-amber-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Date & Heure</p>
                  <p className="text-white font-semibold text-lg">
                    {formatDate(ride?.date)} à {formatTime(ride?.time)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Client Info Card */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-sky-500/20 rounded-xl flex items-center justify-center">
                    <User className="w-6 h-6 text-sky-400" />
                  </div>
                  <div>
                    <p className="text-gray-400 text-sm">Client</p>
                    <p className="text-white font-semibold">{ride?.client_name}</p>
                  </div>
                </div>
                <a 
                  href={`tel:${ride?.client_phone}`}
                  className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center hover:bg-green-500/30 transition-colors"
                  data-testid="call-client-btn"
                >
                  <Phone className="w-5 h-5 text-green-400" />
                </a>
              </div>
            </CardContent>
          </Card>

          {/* Addresses Card */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4 space-y-4">
              {/* Pickup */}
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <MapPin className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Départ</p>
                  <p className="text-white text-sm leading-relaxed">{ride?.pickup_address}</p>
                </div>
              </div>
              
              {/* Dotted line connector */}
              <div className="ml-5 border-l-2 border-dashed border-gray-700 h-4"></div>
              
              {/* Dropoff */}
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <MapPin className="w-5 h-5 text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Arrivée</p>
                  <p className="text-white text-sm leading-relaxed">{ride?.dropoff_address}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Price Summary Card */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
                  <Euro className="w-5 h-5 text-amber-400" />
                </div>
                <p className="text-gray-400 text-sm">Récapitulatif financier</p>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Prix course</span>
                  <span className="text-white">{ride?.price_total}€</span>
                </div>
                
                {(ride?.supplement_peage > 0 || ride?.supplement_parking > 0 || ride?.supplement_attente_amount > 0) && (
                  <>
                    {ride?.supplement_peage > 0 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Péage</span>
                        <span className="text-white">+{ride.supplement_peage}€</span>
                      </div>
                    )}
                    {ride?.supplement_parking > 0 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Parking</span>
                        <span className="text-white">+{ride.supplement_parking}€</span>
                      </div>
                    )}
                    {ride?.supplement_attente_amount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Attente ({ride.supplement_attente_minutes} min)</span>
                        <span className="text-white">+{ride.supplement_attente_amount}€</span>
                      </div>
                    )}
                  </>
                )}
                
                <div className="flex justify-between text-red-400">
                  <span>Commission payée</span>
                  <span>-{ride?.commission_amount?.toFixed(2)}€</span>
                </div>
                
                <div className="border-t border-gray-700 pt-2 mt-2">
                  <div className="flex justify-between">
                    <span className="text-white font-semibold">Votre gain net</span>
                    <span className="text-green-400 font-bold text-lg">{netDriver.toFixed(2)}€</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notes if present */}
          {ride?.notes && (
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-2">Notes client</p>
                <p className="text-white text-sm">{ride.notes}</p>
              </CardContent>
            </Card>
          )}

          {/* Document Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="outline"
              className="border-gray-700 text-gray-300 hover:bg-gray-800 h-12"
              onClick={() => downloadPDF('bon')}
              data-testid="download-bon-btn"
            >
              <FileText className="w-4 h-4 mr-2" />
              Bon de commande
            </Button>
            <Button
              variant="outline"
              className={`border-gray-700 h-12 ${ride?.invoice_status === 'ISSUED' ? 'text-green-400 border-green-500/30' : 'text-gray-300'} hover:bg-gray-800`}
              onClick={() => downloadPDF('facture')}
              data-testid="download-invoice-btn"
            >
              <FileText className="w-4 h-4 mr-2" />
              Facture
            </Button>
          </div>
        </div>
      </div>

      {/* Fixed Bottom Action Button */}
      {(ride?.status === 'ASSIGNED' || ride?.status === 'IN_PROGRESS') && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent pt-8">
          <div className="max-w-lg mx-auto">
            {ride?.status === 'ASSIGNED' && (
              <Button
                onClick={handleStartRide}
                disabled={actionLoading}
                className="w-full h-14 bg-amber-500 hover:bg-amber-600 text-black font-bold text-lg rounded-xl shadow-lg shadow-amber-500/20"
                data-testid="start-ride-btn"
              >
                {actionLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                ) : (
                  <Play className="w-5 h-5 mr-2" />
                )}
                Démarrer la course
              </Button>
            )}
            
            {ride?.status === 'IN_PROGRESS' && (
              <Button
                onClick={handleEndRide}
                disabled={actionLoading}
                className="w-full h-14 bg-green-500 hover:bg-green-600 text-white font-bold text-lg rounded-xl shadow-lg shadow-green-500/20"
                data-testid="end-ride-btn"
              >
                {actionLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                ) : (
                  <CheckCircle className="w-5 h-5 mr-2" />
                )}
                Terminer la course
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Completed State Message */}
      {(ride?.status === 'DRIVER_COMPLETED' || ride?.status === 'DONE') && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent pt-8">
          <div className="max-w-lg mx-auto">
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
              <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <p className="text-green-400 font-semibold">
                {ride?.status === 'DRIVER_COMPLETED' ? 'Course terminée' : 'Course clôturée'}
              </p>
              <p className="text-gray-400 text-sm mt-1">
                {ride?.status === 'DRIVER_COMPLETED' 
                  ? 'En attente de confirmation client' 
                  : 'Merci pour cette course !'
                }
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
