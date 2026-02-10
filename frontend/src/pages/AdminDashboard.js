import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Download, Eye, RefreshCw, FileText } from 'lucide-react';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [prixFinal, setPrixFinal] = useState('');
  const [updatingPrice, setUpdatingPrice] = useState(false);

  useEffect(() => {
    chargerReservations();
  }, []);

  const chargerReservations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/reservations`);
      setReservations(response.data);
    } catch (error) {
      console.error('Erreur chargement réservations:', error);
      toast.error('Erreur lors du chargement des réservations');
    } finally {
      setLoading(false);
    }
  };

  const telechargerBonCommande = async (reservationId, numeroReservation) => {
    try {
      const response = await axios.get(
        `${API}/reservations/${reservationId}/bon-commande-pdf`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bon_commande_${numeroReservation}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Bon de commande téléchargé');
    } catch (error) {
      console.error('Erreur téléchargement bon de commande:', error);
      toast.error('Erreur lors du téléchargement');
    }
  };

  const telechargerFacture = async (reservationId, numeroReservation) => {
    try {
      const response = await axios.get(
        `${API}/reservations/${reservationId}/facture-pdf`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `facture_${numeroReservation}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Facture téléchargée');
    } catch (error) {
      console.error('Erreur téléchargement facture:', error);
      toast.error('Erreur lors du téléchargement');
    }
  };

  const modifierPrixFinal = async (reservationId) => {
    if (!prixFinal || parseFloat(prixFinal) <= 0) {
      toast.error('Veuillez entrer un prix valide');
      return;
    }

    setUpdatingPrice(true);
    try {
      await axios.patch(`${API}/reservations/${reservationId}`, {
        prix_final: parseFloat(prixFinal)
      });
      
      toast.success('Prix final mis à jour');
      setPrixFinal('');
      setSelectedReservation(null);
      chargerReservations();
    } catch (error) {
      console.error('Erreur modification prix:', error);
      toast.error('Erreur lors de la modification du prix');
    } finally {
      setUpdatingPrice(false);
    }
  };

  const getStatutBadge = (statut) => {
    const variants = {
      'nouvelle': 'default',
      'confirmee': 'secondary',
      'terminee': 'outline',
      'annulee': 'destructive'
    };
    
    return (
      <Badge variant={variants[statut] || 'default'} data-testid={`badge-statut-${statut}`}>
        {statut.charAt(0).toUpperCase() + statut.slice(1)}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center mb-6">
          <Button
            variant="outline"
            onClick={() => navigate('/')}
            data-testid="back-home-button"
          >
            ← Retour
          </Button>
          
          <Button
            onClick={chargerReservations}
            disabled={loading}
            data-testid="refresh-button"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </Button>
        </div>

        <Card data-testid="admin-dashboard-card">
          <CardHeader>
            <CardTitle className="text-3xl">⚙️ Dashboard Admin</CardTitle>
            <CardDescription>
              Gestion des réservations et génération de documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8" data-testid="loading-indicator">
                <p className="text-gray-500">Chargement des réservations...</p>
              </div>
            ) : reservations.length === 0 ? (
              <div className="text-center py-8" data-testid="no-reservations">
                <p className="text-gray-500">Aucune réservation pour le moment</p>
                <Button
                  onClick={() => navigate('/reservation')}
                  className="mt-4"
                  data-testid="create-first-reservation-button"
                >
                  Créer la première réservation
                </Button>
              </div>
            ) : (
              <div className="space-y-4" data-testid="reservations-list">
                {reservations.map((reservation) => (
                  <Card key={reservation.id} className="border-l-4 border-l-blue-500" data-testid={`reservation-card-${reservation.id}`}>
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-bold text-gray-900" data-testid={`reservation-numero-${reservation.id}`}>
                            {reservation.numero_reservation}
                          </h3>
                          <p className="text-sm text-gray-600" data-testid={`reservation-client-${reservation.id}`}>
                            {reservation.client_nom} • {reservation.client_telephone}
                          </p>
                        </div>
                        {getStatutBadge(reservation.statut)}
                      </div>

                      <div className="grid md:grid-cols-2 gap-4 mb-4 text-sm">
                        <div>
                          <p className="text-gray-600"><strong>Date:</strong> {reservation.date_course} à {reservation.heure_course}</p>
                          <p className="text-gray-600"><strong>Départ:</strong> {reservation.adresse_depart}</p>
                          <p className="text-gray-600"><strong>Arrivée:</strong> {reservation.adresse_arrivee}</p>
                        </div>
                        <div>
                          <p className="text-gray-600"><strong>Distance:</strong> {reservation.distance_km} km</p>
                          <p className="text-gray-600"><strong>Durée:</strong> {reservation.duree_minutes} min</p>
                          <p className="text-gray-600"><strong>Passagers:</strong> {reservation.nombre_passagers}</p>
                          <p className="text-gray-900 font-semibold" data-testid={`reservation-prix-${reservation.id}`}>
                            <strong>Prix:</strong> {reservation.prix_final || reservation.prix_estime} €
                            {reservation.prix_final && ' (final)'}
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedReservation(reservation);
                                setPrixFinal(reservation.prix_final || reservation.prix_estime);
                              }}
                              data-testid={`detail-button-${reservation.id}`}
                            >
                              <Eye className="mr-2 h-4 w-4" />
                              Voir détail
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl" data-testid={`detail-modal-${reservation.id}`}>
                            <DialogHeader>
                              <DialogTitle>Détails de la réservation</DialogTitle>
                              <DialogDescription>
                                {selectedReservation?.numero_reservation}
                              </DialogDescription>
                            </DialogHeader>
                            {selectedReservation && (
                              <div className="space-y-4">
                                <div>
                                  <h4 className="font-semibold mb-2">Informations client</h4>
                                  <p><strong>Nom:</strong> {selectedReservation.client_nom}</p>
                                  <p><strong>Téléphone:</strong> {selectedReservation.client_telephone}</p>
                                  <p><strong>Email:</strong> {selectedReservation.client_email}</p>
                                </div>

                                <div>
                                  <h4 className="font-semibold mb-2">Modifier le prix final</h4>
                                  <div className="flex gap-2">
                                    <Input
                                      type="number"
                                      step="0.01"
                                      value={prixFinal}
                                      onChange={(e) => setPrixFinal(e.target.value)}
                                      placeholder="Prix final"
                                      data-testid="input-prix-final"
                                    />
                                    <Button
                                      onClick={() => modifierPrixFinal(selectedReservation.id)}
                                      disabled={updatingPrice}
                                      data-testid="update-prix-button"
                                    >
                                      {updatingPrice ? 'Mise à jour...' : 'Mettre à jour'}
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            )}
                          </DialogContent>
                        </Dialog>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => telechargerBonCommande(reservation.id, reservation.numero_reservation)}
                          data-testid={`download-bon-commande-button-${reservation.id}`}
                        >
                          <FileText className="mr-2 h-4 w-4" />
                          Bon de commande
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => telechargerFacture(reservation.id, reservation.numero_reservation)}
                          data-testid={`download-facture-button-${reservation.id}`}
                        >
                          <Download className="mr-2 h-4 w-4" />
                          Facture PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminDashboard;
