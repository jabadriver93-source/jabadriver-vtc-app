import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Send, MapPin, Clock, Euro, User, ChevronRight } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DriverCoursesPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [driverInfo, setDriverInfo] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('driver_token');
    const info = localStorage.getItem('driver_info');
    
    if (!token) {
      navigate('/driver/login');
      return;
    }
    
    if (info) {
      setDriverInfo(JSON.parse(info));
    }
    
    fetchCourses(token);
  }, [navigate]);

  const fetchCourses = async (token) => {
    try {
      const res = await fetch(`${API_URL}/api/driver/courses`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('driver_token');
        localStorage.removeItem('driver_info');
        navigate('/driver/login');
        return;
      }
      
      const data = await res.json();
      setCourses(data);
    } catch (err) {
      toast.error('Erreur chargement courses');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('driver_token');
    localStorage.removeItem('driver_info');
    navigate('/driver/login');
  };

  const downloadPDF = async (courseId, type) => {
    const token = localStorage.getItem('driver_token');
    try {
      const endpoint = type === 'bon' 
        ? `${API_URL}/api/driver/courses/${courseId}/bon-commande-pdf`
        : `${API_URL}/api/driver/courses/${courseId}/invoice-pdf`;
      
      const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Erreur téléchargement');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = type === 'bon' ? `bon_commande_${courseId.slice(0,8)}.pdf` : `facture_${courseId.slice(0,8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('PDF téléchargé');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const sendInvoice = async (courseId) => {
    const token = localStorage.getItem('driver_token');
    try {
      const res = await fetch(`${API_URL}/api/driver/courses/${courseId}/send-invoice`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Erreur envoi');
      
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ASSIGNED': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'DONE': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'CANCELLED': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'ASSIGNED': return 'Attribuée';
      case 'DONE': return 'Terminée';
      case 'CANCELLED': return 'Annulée';
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Mes Courses</h1>
            {driverInfo && (
              <p className="text-slate-400">{driverInfo.company_name}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => navigate('/driver/profile')}
              className="border-slate-600 text-slate-300"
            >
              Mon Profil
            </Button>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleLogout}
              className="text-slate-400 hover:text-white"
            >
              Déconnexion
            </Button>
          </div>
        </div>

        {/* Courses List */}
        {courses.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="py-12 text-center">
              <p className="text-slate-400">Aucune course attribuée pour le moment.</p>
              <p className="text-slate-500 text-sm mt-2">
                Les courses vous seront attribuées après paiement de la commission.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {courses.map((course) => (
              <Card key={course.id} className="bg-slate-800/50 border-slate-700" data-testid={`course-card-${course.id}`}>
                <CardContent className="p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-slate-400" />
                      <span className="text-white font-medium">{course.client_name}</span>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(course.status)}`}>
                      {getStatusLabel(course.status)}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-green-400 mt-0.5" />
                      <div>
                        <p className="text-xs text-slate-500">Départ</p>
                        <p className="text-slate-300 text-sm">{course.pickup_address}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-red-400 mt-0.5" />
                      <div>
                        <p className="text-xs text-slate-500">Arrivée</p>
                        <p className="text-slate-300 text-sm">{course.dropoff_address}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 mb-4 text-sm">
                    <div className="flex items-center gap-1 text-slate-400">
                      <Clock className="w-4 h-4" />
                      {course.date} à {course.time}
                    </div>
                    <div className="flex items-center gap-1 text-sky-400 font-medium">
                      <Euro className="w-4 h-4" />
                      {course.price_total?.toFixed(2)} €
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-700">
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                      onClick={() => downloadPDF(course.id, 'bon')}
                      data-testid={`download-bon-${course.id}`}
                    >
                      <FileText className="w-4 h-4 mr-1" />
                      Bon de commande
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                      onClick={() => downloadPDF(course.id, 'facture')}
                      data-testid={`download-invoice-${course.id}`}
                    >
                      <FileText className="w-4 h-4 mr-1" />
                      Facture
                    </Button>
                    <Button
                      size="sm"
                      className="bg-sky-600 hover:bg-sky-700"
                      onClick={() => sendInvoice(course.id)}
                      data-testid={`send-invoice-${course.id}`}
                    >
                      <Send className="w-4 h-4 mr-1" />
                      Envoyer facture
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
