import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  MapPin, Clock, Phone, User, Euro, FileText, 
  Loader2, Play, CheckCircle, AlertTriangle, Car, Navigation,
  MessageCircle, ExternalLink, Plus, X
} from 'lucide-react';
import { getDriverActions, logDriverActions } from '@/utils/driverActionsHelper';

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
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlToken = searchParams.get('token'); // Token from URL (email link)
  const sessionToken = localStorage.getItem('driver_token'); // Session token (logged-in driver)
  
  const [ride, setRide] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null); // Track successful actions
  const [isActionDisabled, setIsActionDisabled] = useState(false); // Prevent double-clicks
  
  // Supplements modal state
  const [showSupplementsModal, setShowSupplementsModal] = useState(false);
  const [supplements, setSupplements] = useState({
    peage: '',
    parking: '',
    attente_minutes: ''
  });
  const [savingSupplements, setSavingSupplements] = useState(false);

  // Determine auth mode
  const authMode = urlToken ? 'token' : (sessionToken ? 'session' : null);

  // Helper to safely read JSON response body ONCE (fixes iOS Safari "Body is disturbed" error)
  const safeReadJson = async (res) => {
    try {
      const raw = await res.text(); // Read body ONCE
      try {
        return { ok: true, data: JSON.parse(raw || '{}'), raw };
      } catch {
        return { ok: false, data: null, raw };
      }
    } catch (err) {
      console.error('[FETCH] Body read error:', err);
      return { ok: false, data: null, raw: '' };
    }
  };

  // Map HTTP status to user-friendly error message
  const getErrorMessage = (status, data) => {
    switch (status) {
      case 409:
        return data?.detail || 'Course déjà démarrée ou terminée';
      case 401:
        return 'Session expirée. Veuillez vous reconnecter.';
      case 403:
        return data?.detail || 'Accès refusé';
      case 404:
        return 'Course non trouvée';
      default:
        return data?.detail || `Erreur serveur (${status})`;
    }
  };

  // Build headers for API calls
  const getAuthHeaders = () => {
    const headers = { 
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache'
    };
    if (!urlToken && sessionToken) {
      headers['Authorization'] = `Bearer ${sessionToken}`;
    }
    return headers;
  };

  // Fetch options with no-store for Safari
  const getFetchOptions = (method = 'GET', headers = {}) => ({
    method,
    headers: { ...getAuthHeaders(), ...headers },
    cache: 'no-store' // Critical for Safari
  });

  // Build URL with token if available
  const buildUrl = (endpoint) => {
    const base = `${API_URL}/api/driver/ride/${rideId}${endpoint}`;
    return urlToken ? `${base}?token=${urlToken}` : base;
  };

  useEffect(() => {
    if (!authMode) {
      setError('Authentification requise. Connectez-vous ou utilisez le lien email.');
      setLoading(false);
      return;
    }
    fetchRide();
  }, [rideId, urlToken, sessionToken]);

  const fetchRide = async () => {
    try {
      const url = buildUrl('');
      console.log('[FETCH] Loading ride:', url, '| Auth mode:', authMode);
      
      const res = await fetch(url, getFetchOptions('GET'));
      
      // Read body ONCE using helper
      const { data } = await safeReadJson(res);
      console.log('[FETCH] Response:', res.status, data);
      
      if (!res.ok) {
        if (res.status === 401) {
          setError('Session expirée. Reconnectez-vous.');
        } else {
          setError(getErrorMessage(res.status, data));
        }
        return;
      }
      
      console.log('[FETCH] Ride loaded:', data?.status);
      setRide(data);
      // Reset action states on fresh data
      setActionSuccess(null);
      setIsActionDisabled(false);
    } catch (err) {
      console.error('[FETCH] Network error:', err);
      setError(`Erreur réseau: ${err.message || 'Connexion impossible'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRide = async () => {
    // Prevent double-clicks
    if (actionLoading || isActionDisabled) {
      console.log('[SECURITY] Prevented double-click on start');
      return;
    }
    
    setActionLoading(true);
    setIsActionDisabled(true); // Immediately disable to prevent rapid clicks
    
    try {
      const url = buildUrl('/start');
      console.log('[START] Calling:', url, '| Auth mode:', authMode);
      
      const res = await fetch(url, getFetchOptions('POST'));
      
      // Read body ONCE using helper
      const { data } = await safeReadJson(res);
      console.log('[START] Response:', res.status, data);
      
      if (!res.ok) {
        // Handle specific error codes with clear messages
        if (res.status === 409) {
          toast.error(data?.detail || 'Course déjà démarrée');
          setActionSuccess('already_done');
          // Refresh to show current state
          setTimeout(() => fetchRide(), 1000);
        } else if (res.status === 403) {
          toast.error(data?.detail || 'Accès refusé');
          setError(data?.detail || 'Accès refusé');
        } else if (res.status === 401) {
          toast.error('Session expirée. Reconnectez-vous.');
          setError('Session expirée');
        } else {
          toast.error(getErrorMessage(res.status, data));
          setIsActionDisabled(false);
        }
        return;
      }
      
      setActionSuccess('started');
      toast.success(data?.message || 'Course démarrée !');
      
      // Small delay before refresh to show success state
      setTimeout(() => {
        fetchRide();
      }, 500);
    } catch (err) {
      console.error('[START] Network error:', err);
      toast.error(`Erreur réseau: ${err.message || 'Connexion impossible'}`);
      setIsActionDisabled(false); // Re-enable on network error
    } finally {
      setActionLoading(false);
    }
  };

  const handleEndRide = async () => {
    // Prevent double-clicks
    if (actionLoading || isActionDisabled) {
      console.log('[SECURITY] Prevented double-click on end');
      return;
    }
    
    setActionLoading(true);
    setIsActionDisabled(true); // Immediately disable to prevent rapid clicks
    
    try {
      const url = buildUrl('/end');
      console.log('[END] Calling:', url, '| Auth mode:', authMode);
      
      const res = await fetch(url, getFetchOptions('POST'));
      
      // Read body ONCE using helper
      const { data } = await safeReadJson(res);
      console.log('[END] Response:', res.status, data);
      
      if (!res.ok) {
        // Handle specific error codes with clear messages
        if (res.status === 409) {
          toast.error(data?.detail || 'Course déjà terminée');
          setActionSuccess('already_done');
          // Refresh to show current state
          setTimeout(() => fetchRide(), 1000);
        } else if (res.status === 403) {
          toast.error(data?.detail || 'Accès refusé');
          setError(data?.detail || 'Accès refusé');
        } else if (res.status === 401) {
          toast.error('Session expirée. Reconnectez-vous.');
          setError('Session expirée');
        } else {
          toast.error(getErrorMessage(res.status, data));
          setIsActionDisabled(false);
        }
        return;
      }
      
      setActionSuccess('ended');
      toast.success(data?.message || 'Course terminée !');
      
      // Small delay before refresh to show success state
      setTimeout(() => {
        fetchRide();
      }, 500);
    } catch (err) {
      console.error('[END] Network error:', err);
      toast.error(`Erreur réseau: ${err.message || 'Connexion impossible'}`);
      setIsActionDisabled(false); // Re-enable on network error
    } finally {
      setActionLoading(false);
    }
  };

  const downloadPDF = async (type) => {
    // Support both session auth and token auth for document downloads
    const driverToken = localStorage.getItem('driver_token');
    
    try {
      let endpoint;
      let fetchOptions = {};
      
      if (driverToken) {
        // Session auth - use standard driver endpoints
        endpoint = type === 'bon' 
          ? `${API_URL}/api/driver/courses/${rideId}/bon-commande-pdf`
          : `${API_URL}/api/driver/courses/${rideId}/invoice-pdf`;
        fetchOptions = {
          headers: { 'Authorization': `Bearer ${driverToken}` }
        };
      } else if (urlToken) {
        // Token auth - use token-based endpoints
        endpoint = type === 'bon' 
          ? `${API_URL}/api/driver/ride/${rideId}/bon-commande-pdf?token=${urlToken}`
          : `${API_URL}/api/driver/ride/${rideId}/invoice-pdf?token=${urlToken}`;
      } else {
        toast.error('Authentification requise');
        return;
      }
      
      toast.info('Génération du document en cours...');
      
      const res = await fetch(endpoint, fetchOptions);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('[PDF] Download error:', res.status, errorText);
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
      
      toast.success('Document téléchargé');
    } catch (err) {
      console.error('[PDF] Exception:', err);
      toast.error('Erreur téléchargement');
    }
  };
  
  // Save supplements (supports both auth methods)
  const saveSupplements = async () => {
    setSavingSupplements(true);
    
    try {
      let endpoint;
      let fetchOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplement_peage: parseFloat(supplements.peage) || 0,
          supplement_parking: parseFloat(supplements.parking) || 0,
          supplement_attente_minutes: parseInt(supplements.attente_minutes) || 0
        })
      };
      
      if (sessionToken) {
        endpoint = `${API_URL}/api/driver/courses/${rideId}/supplements`;
        fetchOptions.headers['Authorization'] = `Bearer ${sessionToken}`;
      } else if (urlToken) {
        endpoint = `${API_URL}/api/driver/ride/${rideId}/supplements?token=${urlToken}`;
      } else {
        toast.error('Authentification requise');
        return;
      }
      
      const res = await fetch(endpoint, fetchOptions);
      const data = await res.json();
      
      if (!res.ok) {
        toast.error(data.detail || 'Erreur sauvegarde suppléments');
        return;
      }
      
      toast.success('Suppléments enregistrés');
      setShowSupplementsModal(false);
      fetchRide(); // Refresh ride data
    } catch (err) {
      console.error('[SUPPLEMENTS] Error:', err);
      toast.error('Erreur sauvegarde');
    } finally {
      setSavingSupplements(false);
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

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return null;
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return null;
    }
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
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 bg-sky-500/20 rounded-xl flex items-center justify-center">
                  <User className="w-6 h-6 text-sky-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Client</p>
                  <p className="text-white font-semibold">{ride?.client_name}</p>
                  <p className="text-gray-400 text-xs">{ride?.client_phone}</p>
                </div>
              </div>
              
              {/* Communication Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <a 
                  href={`tel:${ride?.client_phone}`}
                  className="flex items-center justify-center gap-2 h-12 bg-green-500/20 rounded-xl hover:bg-green-500/30 transition-colors active:scale-95"
                  data-testid="call-client-btn"
                >
                  <Phone className="w-5 h-5 text-green-400" />
                  <span className="text-green-400 font-medium text-sm">Appeler</span>
                </a>
                <a 
                  href={`https://wa.me/${ride?.client_phone?.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 h-12 bg-emerald-500/20 rounded-xl hover:bg-emerald-500/30 transition-colors active:scale-95"
                  data-testid="whatsapp-client-btn"
                >
                  <MessageCircle className="w-5 h-5 text-emerald-400" />
                  <span className="text-emerald-400 font-medium text-sm">WhatsApp</span>
                </a>
              </div>
            </CardContent>
          </Card>

          {/* Timeline Card - Only show if ride has started */}
          {(ride?.started_at || ride?.ended_at || ride?.status === 'DONE') && (
            <Card className="bg-gray-900 border-gray-800">
              <CardContent className="p-4">
                <p className="text-gray-400 text-xs uppercase tracking-wider mb-3">Timeline</p>
                <div className="space-y-0">
                  {/* Assigned */}
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-sky-500 rounded-full ring-4 ring-sky-500/20"></div>
                    <div className="flex-1 flex justify-between items-center">
                      <span className="text-gray-300 text-sm">Attribuée</span>
                      <span className="text-gray-500 text-xs">{formatTimestamp(ride?.assigned_at) || '-'}</span>
                    </div>
                  </div>
                  <div className="ml-1.5 border-l-2 border-gray-700 h-4"></div>
                  
                  {/* Started */}
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ring-4 ${ride?.started_at ? 'bg-amber-500 ring-amber-500/20' : 'bg-gray-600 ring-gray-600/20'}`}></div>
                    <div className="flex-1 flex justify-between items-center">
                      <span className={`text-sm ${ride?.started_at ? 'text-gray-300' : 'text-gray-500'}`}>Démarrée</span>
                      <span className={`text-xs ${ride?.started_at ? 'text-amber-400 font-medium' : 'text-gray-500'}`}>
                        {formatTimestamp(ride?.started_at) || '-'}
                      </span>
                    </div>
                  </div>
                  <div className="ml-1.5 border-l-2 border-gray-700 h-4"></div>
                  
                  {/* Ended */}
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ring-4 ${ride?.ended_at ? 'bg-green-500 ring-green-500/20' : 'bg-gray-600 ring-gray-600/20'}`}></div>
                    <div className="flex-1 flex justify-between items-center">
                      <span className={`text-sm ${ride?.ended_at ? 'text-gray-300' : 'text-gray-500'}`}>Terminée</span>
                      <span className={`text-xs ${ride?.ended_at ? 'text-green-400 font-medium' : 'text-gray-500'}`}>
                        {formatTimestamp(ride?.ended_at) || '-'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Confirmed - only if DONE */}
                  {ride?.status === 'DONE' && (
                    <>
                      <div className="ml-1.5 border-l-2 border-gray-700 h-4"></div>
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 bg-emerald-500 rounded-full ring-4 ring-emerald-500/20"></div>
                        <div className="flex-1 flex justify-between items-center">
                          <span className="text-gray-300 text-sm">Confirmée client</span>
                          <span className="text-emerald-400 text-xs font-medium">✓</span>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

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

          {/* Navigation Buttons Card */}
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Navigation className="w-4 h-4 text-amber-400" />
                <p className="text-gray-400 text-xs uppercase tracking-wider">
                  {ride?.status === 'IN_PROGRESS' ? 'Naviguer vers destination' : 'Naviguer vers client'}
                </p>
              </div>
              
              {/* Navigation destination hint */}
              <p className="text-gray-500 text-xs mb-3 truncate">
                {ride?.status === 'IN_PROGRESS' ? ride?.dropoff_address : ride?.pickup_address}
              </p>
              
              <div className="grid grid-cols-2 gap-3">
                {/* Google Maps Button */}
                <a 
                  href={
                    ride?.status === 'IN_PROGRESS' && ride?.dropoff_lat && ride?.dropoff_lng
                      ? `https://www.google.com/maps/dir/?api=1&destination=${ride.dropoff_lat},${ride.dropoff_lng}`
                      : ride?.pickup_lat && ride?.pickup_lng
                        ? `https://www.google.com/maps/dir/?api=1&destination=${ride.pickup_lat},${ride.pickup_lng}`
                        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(ride?.status === 'IN_PROGRESS' ? ride?.dropoff_address : ride?.pickup_address)}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 h-14 bg-blue-500/20 rounded-xl hover:bg-blue-500/30 transition-colors active:scale-95 border border-blue-500/30"
                  data-testid="nav-google-maps-btn"
                >
                  <ExternalLink className="w-5 h-5 text-blue-400" />
                  <span className="text-blue-400 font-semibold text-sm">Google Maps</span>
                </a>
                
                {/* Waze Button */}
                <a 
                  href={
                    ride?.status === 'IN_PROGRESS' && ride?.dropoff_lat && ride?.dropoff_lng
                      ? `https://waze.com/ul?ll=${ride.dropoff_lat},${ride.dropoff_lng}&navigate=yes`
                      : ride?.pickup_lat && ride?.pickup_lng
                        ? `https://waze.com/ul?ll=${ride.pickup_lat},${ride.pickup_lng}&navigate=yes`
                        : `https://waze.com/ul?q=${encodeURIComponent(ride?.status === 'IN_PROGRESS' ? ride?.dropoff_address : ride?.pickup_address)}&navigate=yes`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 h-14 bg-cyan-500/20 rounded-xl hover:bg-cyan-500/30 transition-colors active:scale-95 border border-cyan-500/30"
                  data-testid="nav-waze-btn"
                >
                  <Navigation className="w-5 h-5 text-cyan-400" />
                  <span className="text-cyan-400 font-semibold text-sm">Waze</span>
                </a>
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
                disabled={actionLoading || isActionDisabled}
                className={`w-full h-14 font-bold text-lg rounded-xl shadow-lg transition-all duration-200 ${
                  actionSuccess === 'started' 
                    ? 'bg-green-500 text-white shadow-green-500/20' 
                    : isActionDisabled 
                      ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                      : 'bg-amber-500 hover:bg-amber-600 text-black shadow-amber-500/20'
                }`}
                data-testid="start-ride-btn"
              >
                {actionLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Démarrage en cours...
                  </>
                ) : actionSuccess === 'started' ? (
                  <>
                    <CheckCircle className="w-5 h-5 mr-2" />
                    Course démarrée !
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    Démarrer la course
                  </>
                )}
              </Button>
            )}
            
            {ride?.status === 'IN_PROGRESS' && (
              <Button
                onClick={handleEndRide}
                disabled={actionLoading || isActionDisabled}
                className={`w-full h-14 font-bold text-lg rounded-xl shadow-lg transition-all duration-200 ${
                  actionSuccess === 'ended' 
                    ? 'bg-emerald-500 text-white shadow-emerald-500/20' 
                    : isActionDisabled 
                      ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                      : 'bg-green-500 hover:bg-green-600 text-white shadow-green-500/20'
                }`}
                data-testid="end-ride-btn"
              >
                {actionLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Finalisation...
                  </>
                ) : actionSuccess === 'ended' ? (
                  <>
                    <CheckCircle className="w-5 h-5 mr-2" />
                    Course terminée !
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5 mr-2" />
                    Terminer la course
                  </>
                )}
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
