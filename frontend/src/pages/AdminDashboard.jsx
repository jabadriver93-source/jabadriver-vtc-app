import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { 
  Search, Calendar, Phone, MapPin, Users, Briefcase, 
  MessageSquare, Download, LogOut, Loader2, Clock, RefreshCw,
  ExternalLink, Euro, Route, FileText, FileCheck, Truck, FlaskConical, AlertTriangle
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

const SUBCONTRACTING_STATUS = {
  OPEN: { label: "Disponible", color: "bg-sky-500/20 text-sky-400 border-sky-500/30" },
  RESERVED: { label: "Réservée", color: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
  ASSIGNED: { label: "Attribuée", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  DONE: { label: "Terminée", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  CANCELLED: { label: "Annulée", color: "bg-red-500/20 text-red-400 border-red-500/30" }
};

const getStatusStyle = (status) => {
  const found = STATUS_OPTIONS.find(s => s.value === status);
  return found ? `${found.bgColor} ${found.textColor}` : "bg-slate-500 text-white";
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [subcontractingCourses, setSubcontractingCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [courseDateFilter, setCourseDateFilter] = useState("");
  const [createdDateFilter, setCreatedDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [courseTypeFilter, setCourseTypeFilter] = useState(""); // New filter: "" = all, "subcontracted" = sous-traitées, "direct" = non sous-traitées
  const [updatingId, setUpdatingId] = useState(null);
  const [invoiceModalReservation, setInvoiceModalReservation] = useState(null);
  const [showTestReservations, setShowTestReservations] = useState(false); // Filter: false = show normal, true = show ONLY test

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
      if (courseDateFilter) params.append("date", courseDateFilter);
      if (createdDateFilter) params.append("created_date", createdDateFilter);
      if (statusFilter) params.append("status", statusFilter);
      
      // Fetch reservations and subcontracting courses in parallel
      const [reservationsRes, coursesRes] = await Promise.all([
        axios.get(`${API}/reservations?${params.toString()}`),
        axios.get(`${API}/admin/subcontracting/courses`).catch(() => ({ data: [] }))
      ]);
      
      setReservations(reservationsRes.data);
      setSubcontractingCourses(coursesRes.data);
    } catch (error) {
      console.error("Error fetching reservations:", error);
      toast.error("Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  }, [search, courseDateFilter, createdDateFilter, statusFilter]);

  // Helper to find subcontracting info for a reservation
  const getSubcontractingInfo = (reservation) => {
    // Match by subcontracting_course_id or by client_name + date
    if (reservation.subcontracting_course_id) {
      return subcontractingCourses.find(c => c.id === reservation.subcontracting_course_id);
    }
    // Fallback: match by name and date
    return subcontractingCourses.find(c => 
      c.client_name === reservation.name && 
      c.date === reservation.date
    );
  };

  /**
   * Calculate financial data for a reservation
   * Uses pre-calculated financial_data from API if available (Single Source of Truth)
   * Returns: is_subcontracted, final_price_eur, base_price_eur, supplements_eur, commission_eur, driver_revenue_eur
   */
  const getFinancialData = (reservation) => {
    // Priority 1: Use API-provided financial_data (Single Source of Truth)
    if (reservation.financial_data) {
      return {
        is_subcontracted: reservation.is_subcontracted,
        base_price_eur: reservation.financial_data.base_price_eur,
        supplements_eur: reservation.financial_data.supplements_eur,
        final_price_eur: reservation.financial_data.final_price_eur,
        commission_eur: reservation.financial_data.commission_eur,
        driver_revenue_eur: reservation.financial_data.driver_revenue_eur,
        subInfo: getSubcontractingInfo(reservation)
      };
    }
    
    // Priority 2: Calculate from subcontracting course data
    const subInfo = getSubcontractingInfo(reservation);
    const totals = subInfo?.totals || {};
    
    // Determine if subcontracted
    const isSubcontracted = reservation.is_subcontracted || !!(subInfo?.assigned_driver_id || reservation.subcontracting_course_id);
    
    // Calculate prices
    let basePriceEur = totals.base_price_eur ?? reservation.base_price ?? reservation.estimated_price ?? 0;
    let supplementsEur = (totals.waiting_fee_eur ?? 0) + (totals.extras_total_eur ?? 0);
    
    // If no totals from subcontracting, check if reservation has airport surcharge
    if (!subInfo && reservation.airport_surcharge) {
      supplementsEur += reservation.airport_surcharge;
    }
    
    let finalPriceEur = totals.final_total_eur ?? reservation.final_price ?? (basePriceEur + supplementsEur);
    
    // Commission = 10% of BASE price only (never on supplements)
    const commissionEur = totals.commission_base_eur ?? (basePriceEur * 0.10);
    
    // Driver revenue = final price - commission
    const driverRevenueEur = totals.net_driver_eur ?? (finalPriceEur - commissionEur);
    
    return {
      is_subcontracted: isSubcontracted,
      base_price_eur: basePriceEur,
      supplements_eur: supplementsEur,
      final_price_eur: finalPriceEur,
      commission_eur: commissionEur,
      driver_revenue_eur: driverRevenueEur,
      subInfo
    };
  };

  // Filter reservations by course type
  const filteredReservations = reservations.filter(r => {
    // First apply test filter - same logic as Subcontracting page
    // showTestReservations=false: show only normal (is_test=false)
    // showTestReservations=true: show only test (is_test=true)
    if (showTestReservations ? !r.is_test : r.is_test) return false;
    
    // Then apply course type filter
    if (courseTypeFilter) {
      const { is_subcontracted } = getFinancialData(r);
      if (courseTypeFilter === "subcontracted" && !is_subcontracted) return false;
      if (courseTypeFilter === "direct" && is_subcontracted) return false;
    }
    
    return true;
  });

  // Calculate summary stats from filtered reservations
  const summaryStats = {
    total: filteredReservations.length,
    nouvelles: filteredReservations.filter(r => r.status === "nouvelle").length,
    confirmees: filteredReservations.filter(r => r.status === "confirmée").length,
    effectuees: filteredReservations.filter(r => r.status === "effectuée").length,
    totalRevenue: filteredReservations.reduce((sum, r) => {
      const { final_price_eur } = getFinancialData(r);
      return sum + (final_price_eur || 0);
    }, 0),
    directRevenue: filteredReservations.filter(r => !getFinancialData(r).is_subcontracted)
      .reduce((sum, r) => sum + (getFinancialData(r).final_price_eur || 0), 0),
    subcontractedRevenue: filteredReservations.filter(r => getFinancialData(r).is_subcontracted)
      .reduce((sum, r) => sum + (getFinancialData(r).final_price_eur || 0), 0)
  };

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
    if (courseDateFilter) params.append("date", courseDateFilter);
    if (createdDateFilter) params.append("created_date", createdDateFilter);
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

  const toggleTestReservation = async (reservationId, currentIsTest) => {
    try {
      const res = await fetch(`${API}/reservations/${reservationId}/toggle-test`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      
      // Update local state
      setReservations(prev => prev.map(r => 
        r.id === reservationId ? { ...r, is_test: data.is_test } : r
      ));
      
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const formatCreatedAt = (isoStr) => {
    const date = new Date(isoStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  // Count test reservations (for badge)
  const testReservationsCount = reservations.filter(r => r.is_test).length;

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
              onClick={() => navigate('/admin/subcontracting')}
              className="inline-flex items-center gap-2 px-3 py-2 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors text-sm font-medium"
              data-testid="subcontracting-btn"
            >
              <Briefcase className="w-4 h-4" />
              <span className="hidden sm:inline">Sous-traitance</span>
            </button>
            <button 
              onClick={() => navigate('/admin/danger')}
              className="inline-flex items-center gap-1.5 px-2.5 py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg transition-colors text-sm font-medium"
              data-testid="danger-zone-btn"
              title="Danger Zone - Reset données test"
            >
              <AlertTriangle className="w-4 h-4" />
              <span className="hidden lg:inline">Danger</span>
            </button>
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
            
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wide">Date création</span>
              <input
                type="date"
                value={createdDateFilter}
                onChange={(e) => setCreatedDateFilter(e.target.value)}
                className="filter-input-admin w-full sm:w-auto"
                data-testid="created-date-filter"
                title="Filtrer par date de création"
              />
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-slate-400 uppercase tracking-wide">Date course</span>
              <input
                type="date"
                value={courseDateFilter}
                onChange={(e) => setCourseDateFilter(e.target.value)}
                className="filter-input-admin w-full sm:w-auto"
                data-testid="course-date-filter"
                title="Filtrer par date de la course"
              />
            </div>

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

            {/* Course Type Filter - Subcontracted vs Direct */}
            <select
              value={courseTypeFilter}
              onChange={(e) => setCourseTypeFilter(e.target.value)}
              className="filter-input-admin w-full sm:w-auto"
              data-testid="course-type-filter"
            >
              <option value="">Type de course</option>
              <option value="direct">🏠 Mes courses</option>
              <option value="subcontracted">🚚 Sous-traitées</option>
            </select>

            <button
              onClick={handleExport}
              className="export-btn"
              data-testid="export-btn"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Export CSV</span>
            </button>
            
            {/* Test Reservations Filter Toggle */}
            <button
              onClick={() => setShowTestReservations(!showTestReservations)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                showTestReservations 
                  ? "bg-orange-500/20 text-orange-400 border border-orange-500/30 hover:bg-orange-500/30" 
                  : "bg-white/5 text-white/50 border border-white/10 hover:bg-white/10 hover:text-white/70"
              }`}
              data-testid="toggle-show-test-reservations"
              title={showTestReservations ? "Masquer les réservations test" : "Afficher les réservations test"}
            >
              <FlaskConical className="w-4 h-4" />
              <span className="hidden sm:inline">{showTestReservations ? 'Masquer tests' : 'Afficher tests'}</span>
              {testReservationsCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-xs bg-orange-500/30 text-orange-300">
                  {testReservationsCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="px-5 py-6">
        <div className="max-w-6xl mx-auto">
          {/* Stats - Using calculated summaryStats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Total</p>
              <p className="text-2xl font-bold text-white" data-testid="stat-total">
                {summaryStats.total}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Nouvelles</p>
              <p className="text-2xl font-bold text-[#7dd3fc]" data-testid="stat-new">
                {summaryStats.nouvelles}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Confirmées</p>
              <p className="text-2xl font-bold text-emerald-500" data-testid="stat-confirmed">
                {summaryStats.confirmees}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Effectuées</p>
              <p className="text-2xl font-bold text-slate-400" data-testid="stat-done">
                {summaryStats.effectuees}
              </p>
            </div>
            {/* CA Total with breakdown */}
            <div className="card-dark p-4 col-span-2 bg-gradient-to-br from-[#7dd3fc]/20 to-transparent">
              <p className="text-xs text-[#7dd3fc]/70 mb-1 uppercase tracking-wider">CA Total</p>
              <p className="text-2xl font-bold text-[#7dd3fc]" data-testid="stat-revenue">
                {Math.round(summaryStats.totalRevenue)}€
              </p>
              {/* Revenue breakdown */}
              <div className="flex gap-3 mt-2 text-[10px]">
                <span className="text-emerald-400" title="Mes courses directes">
                  🏠 {Math.round(summaryStats.directRevenue)}€
                </span>
                <span className="text-amber-400" title="Courses sous-traitées">
                  🚚 {Math.round(summaryStats.subcontractedRevenue)}€
                </span>
              </div>
            </div>
          </div>

          {/* Reservations List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-[#7dd3fc] spinner" />
            </div>
          ) : filteredReservations.length === 0 ? (
            <div className="text-center py-20 card-dark">
              <Calendar className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/40">
                {reservations.length === 0 
                  ? "Aucune réservation trouvée" 
                  : showTestReservations
                    ? "Aucune réservation test trouvée"
                    : courseTypeFilter 
                      ? `Aucune course ${courseTypeFilter === 'subcontracted' ? 'sous-traitée' : 'directe'} trouvée`
                      : "Aucune réservation normale à afficher"
                }
              </p>
              {!showTestReservations && testReservationsCount > 0 && (
                <button
                  onClick={() => setShowTestReservations(true)}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded-lg hover:bg-orange-500/30 transition-colors"
                >
                  <FlaskConical className="w-4 h-4" />
                  Afficher les {testReservationsCount} réservation(s) test
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4" data-testid="reservations-list">
              {filteredReservations.map((reservation, index) => (
                <div 
                  key={reservation.id} 
                  className={`reservation-row animate-fadeIn ${reservation.is_test ? 'ring-2 ring-orange-500/40' : ''}`}
                  style={{ animationDelay: `${index * 50}ms` }}
                  data-testid={`reservation-${reservation.id}`}
                >
                  {/* Header */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-4">
                      <div>
                        <h3 className="text-lg font-bold text-white flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {reservation.name}
                          {reservation.is_test && (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-500/20 text-orange-400 border border-orange-500/30 flex items-center gap-1" data-testid={`test-badge-${reservation.id}`}>
                              <FlaskConical className="w-3 h-3" />
                              TEST
                            </span>
                          )}
                        </h3>
                        <p className="text-sm text-white/40 flex items-center gap-2 mt-1">
                          <Clock className="w-4 h-4" />
                          Créé le {formatCreatedAt(reservation.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Subcontracting Badge */}
                      {(() => {
                        const subInfo = getSubcontractingInfo(reservation);
                        if (subInfo) {
                          const statusInfo = SUBCONTRACTING_STATUS[subInfo.status] || SUBCONTRACTING_STATUS.OPEN;
                          return (
                            <div className={`${statusInfo.color} border text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1`}>
                              <Truck className="w-3 h-3" />
                              {statusInfo.label}
                              {subInfo.assigned_driver && (
                                <span className="ml-1 opacity-70">• {subInfo.assigned_driver.company_name?.slice(0, 10)}</span>
                              )}
                            </div>
                          );
                        }
                        return null;
                      })()}
                      {/* Invoice Badge */}
                      {reservation.invoice_generated && (
                        <div className="bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {reservation.invoice_number}
                        </div>
                      )}
                      {/* Price Badge - Using getFinancialData for consistent pricing */}
                      {(() => {
                        const { final_price_eur, base_price_eur, supplements_eur, is_subcontracted } = getFinancialData(reservation);
                        const hasSupplements = supplements_eur > 0;
                        
                        return (
                          <div 
                            className={`font-bold px-4 py-1.5 rounded-full text-sm flex items-center gap-1.5 ${
                              is_subcontracted 
                                ? 'bg-amber-400 text-[#0a0a0a]' 
                                : 'bg-[#7dd3fc] text-[#0a0a0a]'
                            }`}
                            data-testid={`price-${reservation.id}`}
                            title={hasSupplements 
                              ? `Base: ${base_price_eur?.toFixed(2)}€ + Suppléments: ${supplements_eur?.toFixed(2)}€` 
                              : `Prix: ${final_price_eur?.toFixed(2)}€`
                            }
                          >
                            <span>{Math.round(final_price_eur || 0)}€</span>
                            {hasSupplements && <span className="text-[10px] ml-1 opacity-70">+sup.</span>}
                            {is_subcontracted && <span className="text-[10px] ml-1">🚚</span>}
                          </div>
                        );
                      })()}
                      {/* Status Badge */}
                      <span className={`${getStatusStyle(reservation.status)} text-xs font-semibold px-3 py-1.5 rounded-full`}>
                        {reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
                      </span>
                    </div>
                  </div>
                  
                  {/* Subcontracting Info Row - Show price breakdown */}
                  {(() => {
                    const subInfo = getSubcontractingInfo(reservation);
                    if (subInfo && (subInfo.status === 'ASSIGNED' || subInfo.commission_paid || subInfo.assigned_driver_id)) {
                      const totals = subInfo.totals || {};
                      const hasExtras = (totals.waiting_fee_eur > 0) || (totals.extras_total_eur > 0);
                      
                      return (
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-4 text-sm">
                              <span className="text-amber-400 font-medium flex items-center gap-1">
                                <Truck className="w-4 h-4" />
                                Sous-traitée
                              </span>
                              {subInfo.assigned_driver && (
                                <span className="text-white/70">
                                  → {subInfo.assigned_driver.company_name} ({subInfo.assigned_driver.name})
                                </span>
                              )}
                              {subInfo.commission_paid && (
                                <span className="text-green-400 text-xs">
                                  ✓ Commission {(totals.commission_base_eur || subInfo.commission_amount)?.toFixed(2)}€ payée
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {/* Price breakdown for subcontracted course */}
                          {totals.base_price_eur !== undefined && (
                            <div className="mt-2 pt-2 border-t border-amber-500/20 flex flex-wrap items-center gap-4 text-xs">
                              <span className="text-white/60">
                                Base: <span className="text-white font-medium">{totals.base_price_eur?.toFixed(2)}€</span>
                              </span>
                              {hasExtras && (
                                <>
                                  {totals.waiting_fee_eur > 0 && (
                                    <span className="text-amber-400">
                                      + Attente ({totals.waiting_billable_minutes}min): {totals.waiting_fee_eur?.toFixed(2)}€
                                    </span>
                                  )}
                                  {totals.extras_peage_eur > 0 && (
                                    <span className="text-amber-400">
                                      + Péage: {totals.extras_peage_eur?.toFixed(2)}€
                                    </span>
                                  )}
                                  {totals.extras_parking_eur > 0 && (
                                    <span className="text-amber-400">
                                      + Parking: {totals.extras_parking_eur?.toFixed(2)}€
                                    </span>
                                  )}
                                </>
                              )}
                              <span className="text-sky-400 font-semibold">
                                = Total: {totals.final_total_eur?.toFixed(2)}€
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  })()}

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

                    {/* Bon de commande Button - Different endpoint for subcontracted courses */}
                    {(() => {
                      const subInfo = getSubcontractingInfo(reservation);
                      const isSubcontracted = subInfo?.assigned_driver_id;
                      
                      if (isSubcontracted) {
                        // Subcontracted: Use admin driver document endpoint (driver -> client)
                        return (
                          <button
                            onClick={() => window.open(`${API}/admin/subcontracting/courses/${subInfo.id}/driver-bon-commande-pdf`, '_blank')}
                            className="action-btn bg-purple-500/20 text-purple-400 hover:bg-purple-500/30"
                            data-testid={`bon-commande-btn-${reservation.id}`}
                            title="Document au nom du chauffeur"
                          >
                            <FileCheck className="w-4 h-4" />
                            BDC (chauffeur)
                          </button>
                        );
                      }
                      // Not subcontracted: Use Jabadriver document
                      return (
                        <button
                          onClick={() => window.open(`${API}/reservations/${reservation.id}/bon-commande-pdf`, '_blank')}
                          className="action-btn bg-purple-500/20 text-purple-400 hover:bg-purple-500/30"
                          data-testid={`bon-commande-btn-${reservation.id}`}
                        >
                          <FileCheck className="w-4 h-4" />
                          Bon de commande
                        </button>
                      );
                    })()}

                    {/* Invoice Button - Different endpoint for subcontracted courses */}
                    {(() => {
                      const subInfo = getSubcontractingInfo(reservation);
                      const isSubcontracted = subInfo?.assigned_driver_id;
                      
                      if (isSubcontracted) {
                        // Subcontracted: Use admin driver invoice endpoint (driver -> client)
                        return (
                          <button
                            onClick={() => window.open(`${API}/admin/subcontracting/courses/${subInfo.id}/driver-invoice-pdf`, '_blank')}
                            className="action-btn bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                            data-testid={`invoice-btn-${reservation.id}`}
                            title="Facture au nom du chauffeur"
                          >
                            <FileText className="w-4 h-4" />
                            Facture (chauffeur)
                          </button>
                        );
                      }
                      // Not subcontracted: Use Jabadriver invoice modal
                      return (
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
                      );
                    })()}
                    
                    {/* Test Toggle Button */}
                    <button
                      onClick={() => toggleTestReservation(reservation.id, reservation.is_test)}
                      className={`action-btn ${
                        reservation.is_test 
                          ? 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30' 
                          : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white/60'
                      }`}
                      data-testid={`toggle-test-btn-${reservation.id}`}
                      title={reservation.is_test ? "Retirer du mode test" : "Marquer comme test"}
                    >
                      <FlaskConical className="w-4 h-4" />
                      <span className="hidden sm:inline">{reservation.is_test ? 'Mode Test' : 'Test'}</span>
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
