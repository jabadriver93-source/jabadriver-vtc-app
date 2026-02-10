import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { 
  Search, Calendar, Phone, MapPin, Users, Briefcase, 
  MessageSquare, Download, LogOut, Loader2, Clock, RefreshCw,
  ExternalLink, Euro, Route, FileText, FileCheck
} from "lucide-react";
import axios from "axios";
import InvoiceModal from "@/components/InvoiceModal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "/logo.png";

const STATUS_OPTIONS = [
  { value: "nouvelle", label: "Nouvelle", bgColor: "bg-[#7dd3fc]", textColor: "text-[#0a0a0a]" },
  { value: "confirmée", label: "Confirmée", bgColor: "bg-emerald-500", textColor: "text-white" },
  { value: "effectuée", label: "Effectuée", bgColor: "bg-slate-500", textColor: "text-white" },
  { value: "annulée", label: "Annulée", bgColor: "bg-red-500", textColor: "text-white" }
];

const getStatusStyle = (status) => {
  const found = STATUS_OPTIONS.find(s => s.value === status);
  return found ? `${found.bgColor} ${found.textColor}` : "bg-slate-500 text-white";
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  const [invoiceModalReservation, setInvoiceModalReservation] = useState(null);

  useEffect(() => {
    const auth = sessionStorage.getItem("adminAuth");
    if (!auth) {
      navigate("/admin");
    }
  }, [navigate]);

  const fetchReservations = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (dateFilter) params.append("date", dateFilter);
      if (statusFilter) params.append("status", statusFilter);
      
      const response = await axios.get(`${API}/reservations?${params.toString()}`);
      setReservations(response.data);
    } catch (error) {
      console.error("Error fetching reservations:", error);
      toast.error("Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  }, [search, dateFilter, statusFilter]);

  useEffect(() => {
    fetchReservations();
  }, [fetchReservations]);

  const handleStatusChange = async (id, newStatus) => {
    setUpdatingId(id);
    try {
      await axios.patch(`${API}/reservations/${id}/status`, { status: newStatus });
      setReservations(prev => 
        prev.map(r => r.id === id ? { ...r, status: newStatus } : r)
      );
      toast.success("Statut mis à jour");
    } catch (error) {
      console.error("Error updating status:", error);
      toast.error("Erreur");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleExport = () => {
    const params = new URLSearchParams();
    if (dateFilter) params.append("date", dateFilter);
    if (statusFilter) params.append("status", statusFilter);
    
    window.open(`${API}/reservations/export/csv?${params.toString()}`, '_blank');
    toast.success("Export CSV lancé");
  };

  const handleLogout = () => {
    sessionStorage.removeItem("adminAuth");
    navigate("/admin");
  };

  const openGoogleMaps = (pickup, dropoff) => {
    const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(pickup)}&destination=${encodeURIComponent(dropoff)}`;
    window.open(url, '_blank');
  };

  const handleInvoiceGenerated = (reservationId, invoiceData) => {
    setReservations(prev =>
      prev.map(r => r.id === reservationId ? { ...r, ...invoiceData } : r)
    );
    setInvoiceModalReservation(prev => prev ? { ...prev, ...invoiceData } : null);
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const formatCreatedAt = (isoStr) => {
    const date = new Date(isoStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  const totalRevenue = reservations
    .filter(r => r.status !== "annulée" && (r.final_price || r.estimated_price))
    .reduce((sum, r) => sum + (r.final_price || r.estimated_price || 0), 0);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="px-5 py-4 border-b border-white/10 sticky top-0 z-40 bg-[#0a0a0a]">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={LOGO_URL} alt="JABA DRIVER" className="h-9 w-auto" />
            <span className="text-lg font-bold text-white tracking-tight hidden sm:block" style={{ fontFamily: 'Manrope, sans-serif' }}>
              JABA DRIVER
            </span>
            <span className="text-xs text-[#7dd3fc] font-medium ml-1 hidden sm:block">Admin</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={fetchReservations}
              className="p-2.5 text-white/50 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button 
              onClick={handleLogout}
              className="inline-flex items-center gap-2 px-3 py-2 text-white/50 hover:text-white hover:bg-white/5 rounded-lg transition-colors text-sm font-medium"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Déconnexion</span>
            </button>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="px-5 py-4 border-b border-white/10 sticky top-[65px] z-30 bg-[#0a0a0a]/95 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              <input
                type="text"
                placeholder="Rechercher nom ou téléphone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="search-input-admin"
                data-testid="search-input"
              />
            </div>
            
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="filter-input-admin w-full sm:w-auto"
              data-testid="date-filter"
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-input-admin w-full sm:w-auto"
              data-testid="status-filter"
            >
              <option value="">Tous statuts</option>
              {STATUS_OPTIONS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>

            <button
              onClick={handleExport}
              className="export-btn"
              data-testid="export-btn"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Export CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="px-5 py-6">
        <div className="max-w-6xl mx-auto">
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Total</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-total">
                {reservations.length}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Nouvelles</p>
              <p className="text-2xl font-bold text-[#7dd3fc]" data-testid="stat-new">
                {reservations.filter(r => r.status === "nouvelle").length}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Confirmées</p>
              <p className="text-2xl font-bold text-emerald-500" data-testid="stat-confirmed">
                {reservations.filter(r => r.status === "confirmée").length}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Effectuées</p>
              <p className="text-2xl font-bold text-slate-400" data-testid="stat-done">
                {reservations.filter(r => r.status === "effectuée").length}
              </p>
            </div>
            <div className="card-dark p-4 col-span-2 sm:col-span-1 bg-gradient-to-br from-[#7dd3fc]/20 to-transparent">
              <p className="text-xs text-[#7dd3fc]/70 mb-1 uppercase tracking-wider">CA Estimé</p>
              <p className="text-2xl font-bold text-[#7dd3fc]" data-testid="stat-revenue">
                {Math.round(totalRevenue)}€
              </p>
            </div>
          </div>

          {/* Reservations List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-[#7dd3fc] spinner" />
            </div>
          ) : reservations.length === 0 ? (
            <div className="text-center py-20 card-dark">
              <Calendar className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/40">Aucune réservation trouvée</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="reservations-list">
              {reservations.map((reservation, index) => (
                <div 
                  key={reservation.id} 
                  className="reservation-row animate-fadeIn"
                  style={{ animationDelay: `${index * 50}ms` }}
                  data-testid={`reservation-${reservation.id}`}
                >
                  {/* Header */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-4">
                      <div>
                        <h3 className="text-lg font-bold text-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {reservation.name}
                        </h3>
                        <p className="text-sm text-white/40 flex items-center gap-2 mt-1">
                          <Clock className="w-4 h-4" />
                          Créé le {formatCreatedAt(reservation.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Invoice Badge */}
                      {reservation.invoice_generated && (
                        <div className="bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {reservation.invoice_number}
                        </div>
                      )}
                      {/* Price Badge */}
                      {(reservation.final_price || reservation.estimated_price) && (
                        <div className="bg-[#7dd3fc] text-[#0a0a0a] font-bold px-4 py-1.5 rounded-full text-sm" data-testid={`price-${reservation.id}`}>
                          {Math.round(reservation.final_price || reservation.estimated_price)}€
                        </div>
                      )}
                      {/* Status Badge */}
                      <span className={`${getStatusStyle(reservation.status)} text-xs font-semibold px-3 py-1.5 rounded-full`}>
                        {reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
                      </span>
                    </div>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[#7dd3fc]/20 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Calendar className="w-5 h-5 text-[#7dd3fc]" />
                      </div>
                      <div>
                        <p className="text-xs text-white/40">Date & Heure</p>
                        <p className="font-semibold text-white">{formatDate(reservation.date)} à {reservation.time}</p>
                      </div>
                    </div>

                    {(reservation.distance_km || reservation.duration_min) && (
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center flex-shrink-0">
                          <Route className="w-5 h-5 text-white/60" />
                        </div>
                        <div>
                          <p className="text-xs text-white/40">Distance / Durée</p>
                          <p className="font-semibold text-white">
                            {reservation.distance_km ? `${reservation.distance_km} km` : '-'} 
                            {' • '}
                            {reservation.duration_min ? `${Math.round(reservation.duration_min)} min` : '-'}
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center flex-shrink-0">
                        <Users className="w-5 h-5 text-white/60" />
                      </div>
                      <div>
                        <p className="text-xs text-white/40">Passagers</p>
                        <p className="font-semibold text-white">{reservation.passengers}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-5 h-5 text-emerald-500" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-white/40">Départ</p>
                        <p className="font-medium text-white truncate">{reservation.pickup_address}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-5 h-5 text-red-500" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-white/40">Arrivée</p>
                        <p className="font-medium text-white truncate">{reservation.dropoff_address}</p>
                      </div>
                    </div>
                  </div>

                  {(reservation.luggage || reservation.notes) && (
                    <div className="flex flex-wrap gap-4 pt-4 border-t border-white/10">
                      {reservation.luggage && (
                        <div className="flex items-center gap-2 text-sm text-white/50">
                          <Briefcase className="w-4 h-4" />
                          {reservation.luggage}
                        </div>
                      )}
                      {reservation.notes && (
                        <div className="flex items-center gap-2 text-sm text-white/50">
                          <MessageSquare className="w-4 h-4" />
                          {reservation.notes}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-white/10">
                    <select
                      value={reservation.status}
                      onChange={(e) => handleStatusChange(reservation.id, e.target.value)}
                      disabled={updatingId === reservation.id}
                      className="status-select-admin"
                      data-testid={`status-select-${reservation.id}`}
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>

                    <a
                      href={`tel:${reservation.phone}`}
                      className="action-btn bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                      data-testid={`call-btn-${reservation.id}`}
                    >
                      <Phone className="w-4 h-4" />
                      {reservation.phone}
                    </a>

                    <button
                      onClick={() => openGoogleMaps(reservation.pickup_address, reservation.dropoff_address)}
                      className="action-btn bg-[#7dd3fc]/20 text-[#7dd3fc] hover:bg-[#7dd3fc]/30"
                      data-testid={`maps-btn-${reservation.id}`}
                    >
                      <ExternalLink className="w-4 h-4" />
                      Itinéraire
                    </button>

                    {/* Invoice Button */}
                    <button
                      onClick={() => setInvoiceModalReservation(reservation)}
                      className={`action-btn ${
                        reservation.invoice_generated 
                          ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' 
                          : 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                      }`}
                      data-testid={`invoice-btn-${reservation.id}`}
                    >
                      <FileText className="w-4 h-4" />
                      {reservation.invoice_generated ? 'Voir facture' : 'Facture'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Invoice Modal */}
      {invoiceModalReservation && (
        <InvoiceModal
          reservation={invoiceModalReservation}
          onClose={() => setInvoiceModalReservation(null)}
          onInvoiceGenerated={handleInvoiceGenerated}
        />
      )}
    </div>
  );
}
