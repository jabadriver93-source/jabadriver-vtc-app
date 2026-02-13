import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Calendar, Clock, MapPin, Users, Euro, 
  MessageSquare, Edit, X, Loader2, CheckCircle
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

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
  const [modificationType, setModificationType] = useState('date');
  const [modificationDetails, setModificationDetails] = useState('');
  const [cancelReason, setCancelReason] = useState('');

  useEffect(() => {
    fetchReservation();
  }, [token]);

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
      setReservation(await res.json());
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

  const handleModificationRequest = async () => {
    if (!modificationDetails.trim()) {
      toast.error('Veuillez préciser votre demande');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/client-portal/${token}/modification-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          modification_type: modificationType, 
          details: modificationDetails 
        })
      });
      const data = await res.json();
      toast.success(data.message);
      setShowModifyModal(false);
      setModificationDetails('');
    } catch (err) {
      toast.error('Erreur lors de l\'envoi');
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

  return (
    <div className="min-h-screen bg-gray-950 p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
            🚗 Votre Réservation
          </h1>
          <p className="text-gray-400">JABADRIVER - Service VTC Premium</p>
        </div>

        {/* Reservation Card */}
        <Card className="bg-gray-900 border-gray-800 mb-6">
          <CardHeader className="border-b border-gray-800">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg text-white">Détails de la course</CardTitle>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                reservation.status === 'confirmée' 
                  ? 'bg-green-900/50 text-green-400 border border-green-700'
                  : reservation.status === 'annulée'
                  ? 'bg-red-900/50 text-red-400 border border-red-700'
                  : 'bg-blue-900/50 text-blue-400 border border-blue-700'
              }`}>
                {reservation.status?.toUpperCase()}
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-sky-400 mt-0.5" />
              <div>
                <p className="text-gray-400 text-sm">Date</p>
                <p className="text-white font-medium">{formatDate(reservation.date)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Clock className="w-5 h-5 text-sky-400 mt-0.5" />
              <div>
                <p className="text-gray-400 text-sm">Heure de prise en charge</p>
                <p className="text-white font-medium">{reservation.time}</p>
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

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-400" />
                <span className="text-white">{reservation.passengers} passager(s)</span>
              </div>
              <div className="flex items-center gap-2">
                <Euro className="w-5 h-5 text-yellow-400" />
                <span className="text-white font-bold">{reservation.estimated_price}€</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Button 
            onClick={() => setShowMessageModal(true)}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="btn-message"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Envoyer un message
          </Button>
          
          <Button 
            onClick={() => setShowModifyModal(true)}
            variant="outline"
            className="border-yellow-600 text-yellow-400 hover:bg-yellow-900/30"
            data-testid="btn-modify"
          >
            <Edit className="w-4 h-4 mr-2" />
            Demander modification
          </Button>
          
          <Button 
            onClick={() => setShowCancelModal(true)}
            variant="outline"
            className="border-red-600 text-red-400 hover:bg-red-900/30"
            data-testid="btn-cancel"
          >
            <X className="w-4 h-4 mr-2" />
            Demander annulation
          </Button>
        </div>

        {/* Info */}
        <div className="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-800">
          <p className="text-gray-400 text-sm text-center">
            Pour toute question urgente, contactez-nous via WhatsApp :<br/>
            <a href="https://wa.me/33756923711" className="text-green-400 hover:underline">
              +33 7 56 92 37 11
            </a>
          </p>
        </div>
      </div>

      {/* Message Modal */}
      {showMessageModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-white">📬 Envoyer un message</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Votre message..."
                className="w-full h-32 p-3 bg-gray-800 border border-gray-700 rounded-lg text-white resize-none"
              />
              <div className="flex gap-2">
                <Button 
                  onClick={handleSendMessage} 
                  disabled={submitting}
                  className="flex-1"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Envoyer'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setShowMessageModal(false)}
                  className="border-gray-700"
                >
                  Annuler
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Modification Modal */}
      {showModifyModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-white">✏️ Demander une modification</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-gray-400 text-sm">Type de modification</label>
                <select
                  value={modificationType}
                  onChange={(e) => setModificationType(e.target.value)}
                  className="w-full p-3 bg-gray-800 border border-gray-700 rounded-lg text-white mt-1"
                >
                  <option value="date">Date / Heure</option>
                  <option value="address">Adresse de prise en charge</option>
                  <option value="destination">Destination</option>
                  <option value="passengers">Nombre de passagers</option>
                  <option value="other">Autre</option>
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Précisez votre demande</label>
                <textarea
                  value={modificationDetails}
                  onChange={(e) => setModificationDetails(e.target.value)}
                  placeholder="Décrivez la modification souhaitée..."
                  className="w-full h-24 p-3 bg-gray-800 border border-gray-700 rounded-lg text-white resize-none mt-1"
                />
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={handleModificationRequest} 
                  disabled={submitting}
                  className="flex-1 bg-yellow-600 hover:bg-yellow-700"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Envoyer la demande'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setShowModifyModal(false)}
                  className="border-gray-700"
                >
                  Annuler
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Cancellation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-white">❌ Demander une annulation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-yellow-900/30 border border-yellow-700 rounded-lg">
                <p className="text-yellow-400 text-sm">
                  ⚠️ Les annulations moins d'1 heure avant la prise en charge peuvent entraîner des frais.
                </p>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Raison (optionnel)</label>
                <textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Raison de l'annulation..."
                  className="w-full h-20 p-3 bg-gray-800 border border-gray-700 rounded-lg text-white resize-none mt-1"
                />
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={handleCancellationRequest} 
                  disabled={submitting}
                  className="flex-1 bg-red-600 hover:bg-red-700"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirmer l\'annulation'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setShowCancelModal(false)}
                  className="border-gray-700"
                >
                  Retour
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
