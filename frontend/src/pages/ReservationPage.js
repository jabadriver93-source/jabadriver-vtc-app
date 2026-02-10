import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

const ReservationPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    client_nom: '',
    client_telephone: '',
    client_email: '',
    adresse_depart: '',
    adresse_arrivee: '',
    date_course: '',
    heure_course: '',
    distance_km: '',
    duree_minutes: '',
    prix_estime: '',
    nombre_passagers: 1
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Conversion des types
      const payload = {
        ...formData,
        distance_km: parseFloat(formData.distance_km),
        duree_minutes: parseInt(formData.duree_minutes),
        prix_estime: parseFloat(formData.prix_estime),
        nombre_passagers: parseInt(formData.nombre_passagers)
      };

      const response = await axios.post(`${API}/reservations`, payload);
      
      toast.success(
        `Réservation créée avec succès !`,
        {
          description: `Numéro : ${response.data.numero_reservation}`
        }
      );

      // Reset form
      setFormData({
        client_nom: '',
        client_telephone: '',
        client_email: '',
        adresse_depart: '',
        adresse_arrivee: '',
        date_course: '',
        heure_course: '',
        distance_km: '',
        duree_minutes: '',
        prix_estime: '',
        nombre_passagers: 1
      });

      // Redirection après 2 secondes
      setTimeout(() => {
        navigate('/admin');
      }, 2000);

    } catch (error) {
      console.error('Erreur création réservation:', error);
      toast.error(
        'Erreur lors de la création de la réservation',
        {
          description: error.response?.data?.detail || 'Veuillez réessayer'
        }
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <div className="container mx-auto px-4 max-w-3xl">
        <Button
          variant="outline"
          onClick={() => navigate('/')}
          className="mb-4"
          data-testid="back-home-button"
        >
          ← Retour
        </Button>

        <Card data-testid="reservation-form-card">
          <CardHeader>
            <CardTitle className="text-3xl">🚕 Nouvelle Réservation VTC</CardTitle>
            <CardDescription>
              Remplissez le formulaire pour réserver votre course
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Informations Client */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Informations Client</h3>
                
                <div>
                  <Label htmlFor="client_nom">Nom complet *</Label>
                  <Input
                    id="client_nom"
                    name="client_nom"
                    value={formData.client_nom}
                    onChange={handleChange}
                    required
                    placeholder="Jean Dupont"
                    data-testid="input-client-nom"
                  />
                </div>

                <div>
                  <Label htmlFor="client_telephone">Téléphone *</Label>
                  <Input
                    id="client_telephone"
                    name="client_telephone"
                    value={formData.client_telephone}
                    onChange={handleChange}
                    required
                    placeholder="+33 6 12 34 56 78"
                    data-testid="input-client-telephone"
                  />
                </div>

                <div>
                  <Label htmlFor="client_email">Email *</Label>
                  <Input
                    id="client_email"
                    name="client_email"
                    type="email"
                    value={formData.client_email}
                    onChange={handleChange}
                    required
                    placeholder="jean.dupont@email.fr"
                    data-testid="input-client-email"
                  />
                </div>
              </div>

              {/* Détails de la Course */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Détails de la Course</h3>
                
                <div>
                  <Label htmlFor="adresse_depart">Adresse de départ *</Label>
                  <Input
                    id="adresse_depart"
                    name="adresse_depart"
                    value={formData.adresse_depart}
                    onChange={handleChange}
                    required
                    placeholder="123 Rue de Paris, 75001 Paris"
                    data-testid="input-adresse-depart"
                  />
                </div>

                <div>
                  <Label htmlFor="adresse_arrivee">Adresse d'arrivée *</Label>
                  <Input
                    id="adresse_arrivee"
                    name="adresse_arrivee"
                    value={formData.adresse_arrivee}
                    onChange={handleChange}
                    required
                    placeholder="Aéroport Charles de Gaulle, 95700 Roissy"
                    data-testid="input-adresse-arrivee"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="date_course">Date *</Label>
                    <Input
                      id="date_course"
                      name="date_course"
                      type="date"
                      value={formData.date_course}
                      onChange={handleChange}
                      required
                      data-testid="input-date-course"
                    />
                  </div>

                  <div>
                    <Label htmlFor="heure_course">Heure *</Label>
                    <Input
                      id="heure_course"
                      name="heure_course"
                      type="time"
                      value={formData.heure_course}
                      onChange={handleChange}
                      required
                      data-testid="input-heure-course"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="distance_km">Distance (km) *</Label>
                    <Input
                      id="distance_km"
                      name="distance_km"
                      type="number"
                      step="0.1"
                      value={formData.distance_km}
                      onChange={handleChange}
                      required
                      placeholder="25.5"
                      data-testid="input-distance-km"
                    />
                  </div>

                  <div>
                    <Label htmlFor="duree_minutes">Durée (min) *</Label>
                    <Input
                      id="duree_minutes"
                      name="duree_minutes"
                      type="number"
                      value={formData.duree_minutes}
                      onChange={handleChange}
                      required
                      placeholder="45"
                      data-testid="input-duree-minutes"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="prix_estime">Prix estimé (€) *</Label>
                    <Input
                      id="prix_estime"
                      name="prix_estime"
                      type="number"
                      step="0.01"
                      value={formData.prix_estime}
                      onChange={handleChange}
                      required
                      placeholder="65.00"
                      data-testid="input-prix-estime"
                    />
                  </div>

                  <div>
                    <Label htmlFor="nombre_passagers">Nombre de passagers *</Label>
                    <Input
                      id="nombre_passagers"
                      name="nombre_passagers"
                      type="number"
                      min="1"
                      max="8"
                      value={formData.nombre_passagers}
                      onChange={handleChange}
                      required
                      data-testid="input-nombre-passagers"
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={loading}
                data-testid="submit-reservation-button"
              >
                {loading ? 'Création en cours...' : 'Créer la réservation'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ReservationPage;
