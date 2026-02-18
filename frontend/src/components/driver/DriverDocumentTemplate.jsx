/**
 * DriverDocumentTemplate - Unified document template for driver documents
 * 
 * Single source of truth for:
 * - Portail chauffeur (récapitulatif financier)
 * - Page token chauffeur (récapitulatif)
 * - PDF bon de commande (backend generation)
 * - PDF facture (backend generation)
 * 
 * IMPORTANT: All pricing now comes from backend via calculate_course_totals()
 * Commission = 10% of BASE PRICE only (not final total)
 * 
 * @module DriverDocumentTemplate
 */

import { Card, CardContent } from '@/components/ui/card';
import { Euro, MapPin, Clock, User, FileText, Building2 } from 'lucide-react';

/**
 * Calculate total with supplements (legacy fallback)
 * Prefer using course.totals from API when available
 */
export function calculateTotalWithSupplements(course) {
  if (!course) return 0;
  
  // Use API-calculated values if available (Single Source of Truth)
  if (course.totals?.final_total_eur !== undefined) {
    return course.totals.final_total_eur;
  }
  if (course.price_with_supplements !== undefined) {
    return course.price_with_supplements;
  }
  
  // Fallback calculation for old courses
  const basePrice = course.price_base || course.price_total || 0;
  const peage = course.supplement_peage || 0;
  const parking = course.supplement_parking || 0;
  const attente = course.supplement_attente_amount || course.waiting_fee_eur || course.waiting_price || 0;
  
  return basePrice + peage + parking + attente;
}

/**
 * Calculate driver net gain (total - commission)
 * IMPORTANT: Commission = 10% of BASE PRICE only
 */
export function calculateDriverNet(course) {
  // Use API-calculated values if available (Single Source of Truth)
  if (course?.totals?.net_driver_eur !== undefined) {
    return course.totals.net_driver_eur;
  }
  if (course?.net_driver !== undefined) {
    return course.net_driver;
  }
  
  // Fallback: commission on BASE price only
  const total = calculateTotalWithSupplements(course);
  const basePrice = course?.price_base || course?.price_total || 0;
  const commission = basePrice * 0.10; // 10% of BASE only
  return total - commission;
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { 
      weekday: 'short', 
      day: 'numeric', 
      month: 'short' 
    });
  } catch {
    return dateStr;
  }
}

/**
 * CourseFinancialSummary - Financial breakdown for a course
 * Used in both portail and token page
 * 
 * Uses pre-calculated values from API when available (Single Source of Truth)
 * COMMISSION = 10% of base price ONLY
 */
export function CourseFinancialSummary({ course, showCommission = true, compact = false }) {
  if (!course) return null;
  
  // Use API-provided totals (Single Source of Truth) when available
  const totals = course.totals || {};
  
  const basePrice = totals.base_price_eur ?? course.price_base ?? course.price_total ?? 0;
  const peage = totals.extras_peage_eur ?? course.supplement_peage ?? 0;
  const parking = totals.extras_parking_eur ?? course.supplement_parking ?? 0;
  const attenteBillableMinutes = totals.waiting_billable_minutes ?? course.supplement_attente_minutes ?? 0;
  const attenteAmount = totals.waiting_fee_eur ?? course.supplement_attente_amount ?? course.waiting_price ?? 0;
  const total = totals.final_total_eur ?? course.price_with_supplements ?? calculateTotalWithSupplements(course);
  
  // COMMISSION: 10% of BASE price ONLY (never on final total)
  const commission = totals.commission_base_eur ?? course.commission_amount ?? (basePrice * 0.10);
  const driverNet = totals.net_driver_eur ?? course.net_driver ?? (total - commission);
  
  const hasSupplements = peage > 0 || parking > 0 || attenteBillableMinutes > 0;
  
  if (compact) {
    return (
      <div className="bg-slate-700/50 rounded-lg p-3">
        <div className="flex justify-between items-center text-sm">
          <span className="text-slate-400">Prix course</span>
          <span className="text-white">{basePrice.toFixed(2)}€</span>
        </div>
        {hasSupplements && (
          <>
            {peage > 0 && (
              <div className="flex justify-between items-center text-sm mt-1">
                <span className="text-slate-400">Péage</span>
                <span className="text-amber-400">+{peage.toFixed(2)}€</span>
              </div>
            )}
            {parking > 0 && (
              <div className="flex justify-between items-center text-sm mt-1">
                <span className="text-slate-400">Parking</span>
                <span className="text-amber-400">+{parking.toFixed(2)}€</span>
              </div>
            )}
            {attenteMinutes > 0 && (
              <div className="flex justify-between items-center text-sm mt-1">
                <span className="text-slate-400">Attente ({attenteMinutes}min)</span>
                <span className="text-amber-400">+{attenteAmount.toFixed(2)}€</span>
              </div>
            )}
          </>
        )}
        {showCommission && (
          <div className="flex justify-between items-center text-sm mt-2 pt-2 border-t border-slate-600">
            <span className="text-red-400">Commission payée</span>
            <span className="text-red-400">-{commission.toFixed(2)}€</span>
          </div>
        )}
        <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-600">
          <span className="text-white font-semibold">{showCommission ? 'Votre gain net' : 'Total'}</span>
          <span className="text-emerald-400 font-bold text-lg">{showCommission ? driverNet.toFixed(2) : total.toFixed(2)}€</span>
        </div>
      </div>
    );
  }
  
  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
            <Euro className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Récapitulatif financier</p>
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-400">Prix course</span>
            <span className="text-white">{basePrice.toFixed(2)}€</span>
          </div>
          
          {peage > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-400">Péage</span>
              <span className="text-amber-400">+{peage.toFixed(2)}€</span>
            </div>
          )}
          
          {parking > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-400">Parking</span>
              <span className="text-amber-400">+{parking.toFixed(2)}€</span>
            </div>
          )}
          
          {attenteMinutes > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-400">Attente ({attenteMinutes}min)</span>
              <span className="text-amber-400">+{attenteAmount.toFixed(2)}€</span>
            </div>
          )}
          
          {showCommission && (
            <div className="flex justify-between items-center text-sm pt-2 border-t border-gray-700">
              <span className="text-red-400">Commission payée</span>
              <span className="text-red-400">-{commission.toFixed(2)}€</span>
            </div>
          )}
          
          <div className="flex justify-between items-center pt-2 border-t border-gray-700">
            <span className="text-white font-semibold">{showCommission ? 'Votre gain net' : 'Total TTC'}</span>
            <span className="text-emerald-400 font-bold text-xl">{showCommission ? driverNet.toFixed(2) : total.toFixed(2)}€</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * CourseInfoCard - Course details card (pickup/dropoff/date)
 * Unified display for portail and token
 */
export function CourseInfoCard({ course, showClientContact = false }) {
  if (!course) return null;
  
  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4">
        {/* Addresses */}
        <div className="space-y-4 mb-4">
          <div className="flex items-start gap-3">
            <div className="w-3 h-3 bg-green-500 rounded-full ring-4 ring-green-500/20 mt-1.5"></div>
            <div className="flex-1">
              <p className="text-gray-500 text-xs uppercase tracking-wider">Départ</p>
              <p className="text-white text-sm">{course.pickup_address || '-'}</p>
            </div>
          </div>
          
          {/* Connector line */}
          <div className="ml-1.5 pl-0 border-l-2 border-dashed border-gray-700 h-4"></div>
          
          <div className="flex items-start gap-3">
            <div className="w-3 h-3 bg-red-500 rounded-full ring-4 ring-red-500/20 mt-1.5"></div>
            <div className="flex-1">
              <p className="text-gray-500 text-xs uppercase tracking-wider">Arrivée</p>
              <p className="text-white text-sm">{course.dropoff_address || '-'}</p>
            </div>
          </div>
        </div>
        
        {/* Date/Time */}
        <div className="flex items-center gap-2 text-gray-400 text-sm pt-3 border-t border-gray-800">
          <Clock className="w-4 h-4" />
          <span>{formatDate(course.date)} à {course.time || '-'}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * DriverInfoCard - Driver/prestataire info
 */
export function DriverInfoCard({ driver }) {
  if (!driver) return null;
  
  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-sky-500/20 rounded-xl flex items-center justify-center">
            <Building2 className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <p className="text-gray-400 text-xs">Prestataire VTC</p>
            <p className="text-white font-medium">{driver.name || driver.company_name || 'N/A'}</p>
          </div>
        </div>
        
        <div className="space-y-1 text-sm text-gray-400">
          {driver.company_name && driver.company_name !== driver.name && (
            <p>{driver.company_name}</p>
          )}
          {driver.siret && <p>SIRET: {driver.siret}</p>}
          {driver.address && <p>{driver.address}</p>}
          {driver.phone && <p>Tél: {driver.phone}</p>}
          {driver.email && <p>{driver.email}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * ClientInfoCard - Client info display
 */
export function ClientInfoCard({ course }) {
  if (!course) return null;
  
  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center">
            <User className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-gray-400 text-xs">Client</p>
            <p className="text-white font-medium">{course.client_name || 'N/A'}</p>
            {course.client_phone && (
              <p className="text-gray-400 text-xs">{course.client_phone}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * LogoHeader - Centered logo for documents
 */
export function LogoHeader() {
  return (
    <div className="text-center mb-6 pb-4 border-b border-gray-700">
      <img 
        src="/jabadriver_logo.png" 
        alt="JABADRIVER" 
        className="mx-auto"
        style={{ maxWidth: '240px', height: 'auto' }}
      />
    </div>
  );
}

/**
 * DocumentHeader - Header for documents (bon de commande / facture)
 */
export function DocumentHeader({ 
  type = 'bon', // 'bon' | 'facture' | 'facture_finale'
  courseId, 
  invoiceNumber,
  date,
  showLogo = true
}) {
  const titles = {
    bon: 'BON DE COMMANDE VTC',
    factura: 'FACTURE',
    facture: 'FACTURE',
    facture_finale: 'FACTURE'
  };
  
  const shortId = courseId?.slice(0, 8).toUpperCase() || 'N/A';
  const docNumber = type === 'facture_finale' && invoiceNumber 
    ? invoiceNumber 
    : `${type === 'bon' ? 'BC' : 'F'}-${shortId}`;
  
  return (
    <>
      {showLogo && <LogoHeader />}
      <div className="flex justify-between items-start mb-6 pb-4 border-b border-gray-700">
        <div>
          <h2 className="text-xl font-bold text-white">{titles[type] || titles.factura}</h2>
          <p className="text-gray-400 text-sm mt-1">N° {docNumber}</p>
        </div>
        <div className="text-right text-gray-400 text-sm">
          <p>Date: {date || formatDate(new Date().toISOString())}</p>
          <p className="text-xs mt-1">Réf: #{shortId}</p>
        </div>
      </div>
    </>
  );
}

/**
 * LegalMentions - Legal footer for documents
 */
export function LegalMentions({ type = 'facture' }) {
  return (
    <div className="mt-6 pt-4 border-t border-gray-700">
      <div className="text-gray-500 text-xs space-y-1">
        {type === 'facture' && (
          <p>TVA non applicable - Article 293B du CGI</p>
        )}
        <p>JABADRIVER - Service VTC Premium Île-de-France</p>
        <p>Contact: contact@jabadriver.fr | WhatsApp disponible</p>
      </div>
    </div>
  );
}

/**
 * FullDocumentPreview - Complete document preview (for modal or full page)
 * Can be used for both bon de commande and facture preview
 */
export function FullDocumentPreview({ 
  course, 
  driver, 
  type = 'bon', // 'bon' | 'facture' | 'facture_finale'
  showCommission = true 
}) {
  if (!course) return null;
  
  return (
    <div className="bg-gray-900 rounded-lg p-6 max-w-2xl mx-auto">
      <DocumentHeader 
        type={type}
        courseId={course.id}
        invoiceNumber={course.invoice_number}
        date={course.date}
      />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <DriverInfoCard driver={driver} />
        <ClientInfoCard course={course} />
      </div>
      
      <CourseInfoCard course={course} />
      
      <div className="mt-4">
        <CourseFinancialSummary 
          course={course} 
          showCommission={type === 'facture_finale' ? false : showCommission}
        />
      </div>
      
      <LegalMentions type={type} />
    </div>
  );
}

export default {
  LogoHeader,
  CourseFinancialSummary,
  CourseInfoCard,
  DriverInfoCard,
  ClientInfoCard,
  DocumentHeader,
  LegalMentions,
  FullDocumentPreview,
  calculateTotalWithSupplements,
  calculateDriverNet
};
