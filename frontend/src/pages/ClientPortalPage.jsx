import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Calendar, Clock, MapPin, Users, Euro, 
  MessageSquare, Edit, X, Loader2, CheckCircle, 
  AlertTriangle, Lock, User, Phone
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_PUBLIC_GOOGLE_MAPS_API_KEY;

// Price calculation constants - must match backend
const PRICE_PER_KM = 1.50;
const PRICE_PER_MIN = 0.50;

// Google Maps loading state (singleton pattern to avoid multiple loads)
let googleMapsLoaded = false;
let googleMapsLoading = false;
let mapsReadyCallbacks = [];

const notifyMapsReady = () => {
  googleMapsLoaded = true;
  googleMapsLoading = false;
  mapsReadyCallbacks.forEach(cb => cb());
  mapsReadyCallbacks = [];
};

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

    const callbackName = `gmapsCallback_portal_${Date.now()}`;
    
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

export default function ClientPortalPage() {
  const { token } = useParams();
  const [reservation, setReservation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal states
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [showModifyModal, setShowModifyModal] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Form states
  const [message, setMessage] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  
  // Direct modification states
  const [modifyData, setModifyData] = useState({
    pickup_address: '',
    dropoff_address: '',
    date: '',
    time: '',
    passengers: 1
  });
  const [calculatingPrice, setCalculatingPrice] = useState(false);
  const [newEstimate, setNewEstimate] = useState(null);
  
  // Google Maps autocomplete refs
  const [mapsReady, setMapsReady] = useState(false);
  const pickupInputRef = useRef(null);
  const dropoffInputRef = useRef(null);
  const pickupAutocompleteRef = useRef(null);
  const dropoffAutocompleteRef = useRef(null);

  useEffect(() => {
    fetchReservation();
  }, [token]);

  // Load Google Maps script
  useEffect(() => {
    if (!GOOGLE_MAPS_API_KEY) {
      console.warn("Google Maps API key not configured");
      return;
    }

    loadGoogleMapsScript().then(() => {
      if (window.google?.maps?.places) {
        setMapsReady(true);
        console.log("Google Maps Places API ready for client portal");
      }
    });
  }, []);

  // Initialize Autocomplete when modal opens and maps is ready
  useEffect(() => {
    if (!showModifyModal || !mapsReady || !window.google?.maps?.places) return;

    const initAutocomplete = (inputRef, autocompleteRef, fieldName) => {
      // Wait for input to be mounted
      const timer = setTimeout(() => {
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
              setModifyData(prev => ({
                ...prev,
                [fieldName]: place.formatted_address
              }));
              // Update input value directly
              if (inputRef.current) {
                inputRef.current.value = place.formatted_address;
              }
              // Trigger price recalculation after address selection
              setTimeout(() => {
                calculateNewPrice();
              }, 300);
            }
          });

          autocompleteRef.current = autocomplete;
          console.log(`Autocomplete initialized for ${fieldName}`);
        } catch (error) {
          console.error(`Failed to init autocomplete for ${fieldName}:`, error);
        }
      }, 200);

      return () => clearTimeout(timer);
    };

    // Initialize autocomplete for both fields
    const cleanup1 = initAutocomplete(pickupInputRef, pickupAutocompleteRef, "pickup_address");
    const cleanup2 = initAutocomplete(dropoffInputRef, dropoffAutocompleteRef, "dropoff_address");

    // Cleanup on modal close
    return () => {
      if (cleanup1) cleanup1();
      if (cleanup2) cleanup2();
      pickupAutocompleteRef.current = null;
      dropoffAutocompleteRef.current = null;
    };
  }, [showModifyModal, mapsReady]);

  const fetchReservation = async () => {
    try {
      const res = await fetch(`${API_URL}/api/client-portal/${token}`);
      if (!res.ok) {
        if (res.status === 404) {
          setError('Réservation non trouvée ou lien invalide');
        } else {
          setError('Erreur lors du chargement');
        }
        return;
      }
      const data = await res.json();
      setReservation(data);
      // Initialize modification form with current values
      setModifyData({
        pickup_address: data.pickup_address || '',
        dropoff_address: data.dropoff_address || '',
        date: data.date || '',
        time: data.time || '',
        passengers: data.passengers || 1
      });
    } catch (err) {
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim()) {
      toast.error('Veuillez entrer un message');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/client-portal/${token}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await res.json();
      toast.success(data.message);
      setShowMessageModal(false);
      setMessage('');
    } catch (err) {
      toast.error('Erreur lors de l\'envoi');
    } finally {
      setSubmitting(false);
    }
  };

  // Helper to get current address values from refs (autocomplete may update DOM directly)
  const getCurrentAddresses = useCallback(() => {
    const pickup = pickupInputRef.current?.value || modifyData.pickup_address;
    const dropoff = dropoffInputRef.current?.value || modifyData.dropoff_address;
    return { pickup, dropoff };
  }, [modifyData.pickup_address, modifyData.dropoff_address]);

  // Wrapper to trigger price calculation with ref values
  const calculateNewPrice = useCallback(async () => {
    const { pickup, dropoff } = getCurrentAddresses();
    
    if (!pickup || !dropoff) {
      setNewEstimate(null);
      return;
    }
    
    // Check if addresses actually changed from original
    if (pickup === reservation?.pickup_address && 
        dropoff === reservation?.dropoff_address) {
      setNewEstimate(null);
      return;
    }

    // Update modifyData with current ref values
    setModifyData(prev => ({
      ...prev,
      pickup_address: pickup,
      dropoff_address: dropoff
    }));

    setCalculatingPrice(true);
    
    try {
      const params = new URLSearchParams({
        origin: pickup,
        destination: dropoff
      });
      
      const res = await fetch(`${API_URL}/api/calculate-route?${params}`);
      if (res.ok) {
        const data = await res.json();
        const distanceKm = data.distance_km || 0;
        const durationMin = data.duration_min || 0;
        const newPrice = (distanceKm * PRICE_PER_KM) + (durationMin * PRICE_PER_MIN);
        
        setNewEstimate({
          distance_km: distanceKm,
          duration_min: durationMin,
          price: Math.round(newPrice * 100) / 100
        });
      } else {
        setNewEstimate(null);
        toast.warning('Impossible de calculer l\'itinéraire');
      }
    } catch (err) {
      console.error('Route calculation error:', err);
      setNewEstimate(null);
    } finally {
      setCalculatingPrice(false);
    }
  }, [getCurrentAddresses, reservation]);

  // Calculate route and price using Google Maps
  const calculateRoute = useCallback(async () => {
    if (!modifyData.pickup_address || !modifyData.dropoff_address) {
      setNewEstimate(null);
      return;
    }
    
    // Check if addresses actually changed
    if (modifyData.pickup_address === reservation.pickup_address && 
        modifyData.dropoff_address === reservation.dropoff_address) {
      setNewEstimate(null);
      return;
    }

    setCalculatingPrice(true);
    
    try {
      // Use backend route calculation endpoint
      const params = new URLSearchParams({
        origin: modifyData.pickup_address,
        destination: modifyData.dropoff_address
      });
      
      const res = await fetch(`${API_URL}/api/calculate-route?${params}`);
      if (res.ok) {
        const data = await res.json();
        const distanceKm = data.distance_km || 0;
        const durationMin = data.duration_min || 0;
        const newPrice = (distanceKm * PRICE_PER_KM) + (durationMin * PRICE_PER_MIN);
        
        setNewEstimate({
          distance_km: distanceKm,
          duration_min: durationMin,
          price: Math.round(newPrice * 100) / 100
        });
      } else {
        // Fallback: show warning but allow modification
        setNewEstimate(null);
        toast.warning('Impossible de calculer l\'itinéraire - le prix sera recalculé manuellement');
      }
    } catch (err) {
      console.error('Route calculation error:', err);
      setNewEstimate(null);
    } finally {
      setCalculatingPrice(false);
    }
  }, [modifyData.pickup_address, modifyData.dropoff_address, reservation]);

  // Debounce route calculation
  useEffect(() => {
    const timer = setTimeout(() => {
      if (showModifyModal && modifyData.pickup_address && modifyData.dropoff_address) {
        calculateRoute();
      }
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [modifyData.pickup_address, modifyData.dropoff_address, showModifyModal, calculateRoute]);

  const handleDirectModification = async () => {
    setSubmitting(true);
    try {
      // Get current values from refs (autocomplete may have updated them)
      const { pickup, dropoff } = getCurrentAddresses();
      
      const payload = {
        pickup_address: pickup !== reservation.pickup_address ? pickup : null,
        dropoff_address: dropoff !== reservation.dropoff_address ? dropoff : null,
        date: modifyData.date !== reservation.date ? modifyData.date : null,
        time: modifyData.time !== reservation.time ? modifyData.time : null,
        passengers: modifyData.passengers !== reservation.passengers ? modifyData.passengers : null,
        new_distance_km: newEstimate?.distance_km || null,
        new_duration_min: newEstimate?.duration_min || null
      };

      // Check if any change was made
      const hasChanges = Object.values(payload).some(v => v !== null);
      if (!hasChanges) {
        toast.info('Aucune modification détectée');
        setShowModifyModal(false);
        return;
      }

      const res = await fetch(`${API_URL}/api/client-portal/${token}/modify-direct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Erreur lors de la modification');
      }

      toast.success(data.message);
      setShowModifyModal(false);
      setNewEstimate(null);
      // Refresh reservation data
      fetchReservation();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancellationRequest = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/client-portal/${token}/cancellation-request?reason=${encodeURIComponent(cancelReason)}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.is_late_cancellation) {
        toast.warning(data.message);
      } else {
        toast.success(data.message);
      }
      setShowCancelModal(false);
      setCancelReason('');
      fetchReservation();
    } catch (err) {
      toast.error('Erreur lors de l\'envoi');
    } finally {
      setSubmitting(false);
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

  const openModifyModal = () => {
    // Reset autocomplete refs for new initialization
    pickupAutocompleteRef.current = null;
    dropoffAutocompleteRef.current = null;
    
    // Reset form to current reservation values
    setModifyData({
      pickup_address: reservation.pickup_address || '',
      dropoff_address: reservation.dropoff_address || '',
      date: reservation.date || '',
      time: reservation.time || '',
      passengers: reservation.passengers || 1
    });
    setNewEstimate(null);
    setShowModifyModal(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <Card className="bg-gray-900 border-gray-800 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <X className="w-12 h-12 mx-auto mb-4 text-red-500" />
            <h2 className="text-xl font-bold text-white mb-2">Lien invalide</h2>
            <p className="text-gray-400">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const canModify = reservation.can_modify !== false && reservation.invoice_status !== 'ISSUED';

  return (
    <div className="min-h-screen bg-gray-950 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Ma Réservation</h1>
          <p className="text-gray-400 text-sm">Gérez votre course VTC</p>
        </div>

        {/* Main Card */}
        <Card className="bg-gray-900 border-gray-800 mb-6">
          <CardHeader className="border-b border-gray-800">
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-500" />
                Réservation #{reservation.id?.slice(0, 8).toUpperCase()}
              </CardTitle>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                reservation.status === 'confirmed' ? 'bg-green-500/20 text-green-400' :
                reservation.status === 'cancelled' ? 'bg-red-500/20 text-red-400' :
                'bg-sky-500/20 text-sky-400'
              }`}>
                {reservation.status === 'confirmed' ? 'Confirmée' : 
                 reservation.status === 'cancelled' ? 'Annulée' : 'En cours'}
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Driver info if assigned */}
            {reservation.assigned_driver_name && (
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-green-400 text-sm font-medium">Chauffeur attribué</p>
                    <p className="text-white font-semibold">{reservation.assigned_driver_name}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Invoice Status Warning */}
            {reservation.invoice_status === 'ISSUED' && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-amber-400" />
                  <div>
                    <p className="text-amber-400 text-sm font-medium">Facture émise</p>
                    <p className="text-gray-400 text-xs">Les modifications ne sont plus possibles</p>
                  </div>
                </div>
              </div>
            )}

            {/* Trip Details */}
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-sky-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Date</p>
                  <p className="text-white">{formatDate(reservation.date)}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <Clock className="w-5 h-5 text-sky-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Heure</p>
                  <p className="text-white">{reservation.time}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-green-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Départ</p>
                  <p className="text-white">{reservation.pickup_address}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-red-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Arrivée</p>
                  <p className="text-white">{reservation.dropoff_address}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Users className="w-5 h-5 text-sky-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Passagers</p>
                  <p className="text-white">{reservation.passengers} personne(s)</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Euro className="w-5 h-5 text-sky-400 mt-0.5" />
                <div>
                  <p className="text-gray-400 text-sm">Prix estimé</p>
                  <p className="text-white text-xl font-bold">{reservation.estimated_price}€</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="grid grid-cols-1 gap-3">
          {canModify && (
            <Button 
              onClick={openModifyModal}
              className="bg-amber-500 hover:bg-amber-600 text-black"
              data-testid="modify-reservation-btn"
            >
              <Edit className="w-4 h-4 mr-2" />
              Modifier ma réservation
            </Button>
          )}
          
          <Button 
            onClick={() => setShowMessageModal(true)}
            variant="outline"
            className="border-gray-700 text-gray-300 hover:bg-gray-800"
            data-testid="contact-btn"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Contacter l'équipe
          </Button>

          {reservation.status !== 'cancelled' && canModify && (
            <Button 
              onClick={() => setShowCancelModal(true)}
              variant="ghost"
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
              data-testid="cancel-btn"
            >
              <X className="w-4 h-4 mr-2" />
              Annuler ma réservation
            </Button>
          )}
        </div>

        {/* WhatsApp Contact */}
        <div className="mt-6 text-center">
          <a 
            href="https://wa.me/message/MQ6BTZ7KU26OM1" 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-green-400 hover:text-green-300"
          >
            <Phone className="w-4 h-4" />
            Besoin d'aide ? WhatsApp
          </a>
        </div>
      </div>

      {/* Message Modal */}
      {showMessageModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 rounded-xl max-w-md w-full p-6 border border-gray-800">
            <h3 className="text-lg font-bold text-white mb-4">Envoyer un message</h3>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Votre message..."
              className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg p-3 text-white resize-none focus:outline-none focus:border-sky-500"
              data-testid="message-textarea"
            />
            <div className="flex gap-3 mt-4">
              <Button 
                onClick={() => setShowMessageModal(false)} 
                variant="outline"
                className="flex-1 border-gray-700"
              >
                Annuler
              </Button>
              <Button 
                onClick={handleSendMessage} 
                className="flex-1 bg-sky-500 hover:bg-sky-600"
                disabled={submitting}
                data-testid="send-message-btn"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Envoyer'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Direct Modification Modal */}
      {showModifyModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-gray-900 rounded-xl max-w-lg w-full p-6 border border-gray-800 my-8">
            <h3 className="text-lg font-bold text-white mb-2">Modifier ma réservation</h3>
            <p className="text-gray-400 text-sm mb-4">
              Le prix sera automatiquement recalculé ({PRICE_PER_KM}€/km + {PRICE_PER_MIN}€/min)
            </p>
            
            <div className="space-y-4">
              {/* Pickup Address with Autocomplete */}
              <div>
                <Label className="text-gray-300 text-sm flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-emerald-500" />
                  Adresse de départ
                </Label>
                <input
                  ref={pickupInputRef}
                  type="text"
                  defaultValue={modifyData.pickup_address}
                  onChange={(e) => setModifyData({...modifyData, pickup_address: e.target.value})}
                  className="w-full h-10 px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
                  placeholder="Tapez pour rechercher une adresse..."
                  autoComplete="off"
                  data-testid="modify-pickup-input"
                />
              </div>

              {/* Dropoff Address with Autocomplete */}
              <div>
                <Label className="text-gray-300 text-sm flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-red-500" />
                  Adresse d'arrivée
                </Label>
                <input
                  ref={dropoffInputRef}
                  type="text"
                  defaultValue={modifyData.dropoff_address}
                  onChange={(e) => setModifyData({...modifyData, dropoff_address: e.target.value})}
                  className="w-full h-10 px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
                  placeholder="Tapez pour rechercher une adresse..."
                  autoComplete="off"
                  data-testid="modify-dropoff-input"
                />
              </div>

              {/* Date and Time */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-gray-300 text-sm">Date</Label>
                  <Input
                    type="date"
                    value={modifyData.date}
                    onChange={(e) => setModifyData({...modifyData, date: e.target.value})}
                    className="bg-gray-800 border-gray-700 text-white"
                    data-testid="modify-date-input"
                  />
                </div>
                <div>
                  <Label className="text-gray-300 text-sm">Heure</Label>
                  <Input
                    type="time"
                    value={modifyData.time}
                    onChange={(e) => setModifyData({...modifyData, time: e.target.value})}
                    className="bg-gray-800 border-gray-700 text-white"
                    data-testid="modify-time-input"
                  />
                </div>
              </div>

              {/* Passengers */}
              <div>
                <Label className="text-gray-300 text-sm">Nombre de passagers</Label>
                <Input
                  type="number"
                  min="1"
                  max="8"
                  value={modifyData.passengers}
                  onChange={(e) => setModifyData({...modifyData, passengers: parseInt(e.target.value) || 1})}
                  className="bg-gray-800 border-gray-700 text-white"
                  data-testid="modify-passengers-input"
                />
              </div>

              {/* Price Comparison */}
              {(newEstimate || calculatingPrice) && (
                <div className="bg-gray-800 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Ancien prix:</span>
                    <span className="text-white">{reservation.estimated_price}€</span>
                  </div>
                  
                  {calculatingPrice ? (
                    <div className="flex items-center justify-center gap-2 py-2">
                      <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                      <span className="text-gray-400 text-sm">Calcul en cours...</span>
                    </div>
                  ) : newEstimate && (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">Nouveau prix:</span>
                        <span className={`font-bold ${newEstimate.price > reservation.estimated_price ? 'text-amber-400' : 'text-green-400'}`}>
                          {newEstimate.price}€
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 pt-2 border-t border-gray-700">
                        {newEstimate.distance_km} km • {Math.round(newEstimate.duration_min)} min
                      </div>
                      {newEstimate.price !== reservation.estimated_price && (
                        <div className={`flex items-center gap-2 text-sm ${newEstimate.price > reservation.estimated_price ? 'text-amber-400' : 'text-green-400'}`}>
                          <AlertTriangle className="w-4 h-4" />
                          Différence: {newEstimate.price > reservation.estimated_price ? '+' : ''}{(newEstimate.price - reservation.estimated_price).toFixed(2)}€
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <Button 
                onClick={() => {
                  setShowModifyModal(false);
                  setNewEstimate(null);
                }}
                variant="outline"
                className="flex-1 border-gray-700"
              >
                Annuler
              </Button>
              <Button 
                onClick={handleDirectModification}
                className="flex-1 bg-amber-500 hover:bg-amber-600 text-black"
                disabled={submitting || calculatingPrice}
                data-testid="confirm-modification-btn"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Valider la modification'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 rounded-xl max-w-md w-full p-6 border border-gray-800">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-red-500" />
              <h3 className="text-lg font-bold text-white">Annuler ma réservation</h3>
            </div>
            <p className="text-gray-400 text-sm mb-4">
              Une annulation moins d'1h avant la prise en charge peut entraîner des frais.
            </p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Raison de l'annulation (optionnel)..."
              className="w-full h-24 bg-gray-800 border border-gray-700 rounded-lg p-3 text-white resize-none focus:outline-none focus:border-red-500"
              data-testid="cancel-reason-textarea"
            />
            <div className="flex gap-3 mt-4">
              <Button 
                onClick={() => setShowCancelModal(false)} 
                variant="outline"
                className="flex-1 border-gray-700"
              >
                Retour
              </Button>
              <Button 
                onClick={handleCancellationRequest}
                className="flex-1 bg-red-500 hover:bg-red-600"
                disabled={submitting}
                data-testid="confirm-cancel-btn"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirmer l\'annulation'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
