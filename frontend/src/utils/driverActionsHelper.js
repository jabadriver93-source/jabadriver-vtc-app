/**
 * Unified Driver Actions Helper
 * 
 * Centralized logic for determining which actions a driver can perform on a course.
 * Used by both DriverCoursesPage (session auth) and DriverRidePage (token auth).
 * 
 * @module driverActionsHelper
 */

// Valid statuses for driver workflow
export const DRIVER_STATUSES = {
  ASSIGNED: 'ASSIGNED',
  IN_PROGRESS: 'IN_PROGRESS',
  DRIVER_COMPLETED: 'DRIVER_COMPLETED',
  DONE: 'DONE'
};

/**
 * Determine all available actions for a course based on its state.
 * 
 * @param {Object} course - The course object from backend
 * @param {string} course.status - Current status (ASSIGNED, IN_PROGRESS, DRIVER_COMPLETED, DONE)
 * @param {boolean} course.invoice_finalized - True if final invoice has been generated
 * @param {boolean} course.client_confirmed - True if client has confirmed the ride
 * @param {string} course.invoice_status - Invoice status (DRAFT, PREVIEW, ISSUED)
 * @returns {Object} Object with boolean flags for each action
 */
export function getDriverActions(course) {
  if (!course) {
    return {
      canStartRide: false,
      canEndRide: false,
      canAddSupplements: false,
      canGenerateInvoicePreview: false,
      canGenerateFinalInvoice: false,
      canDownloadBonCommande: false,
      canDownloadInvoice: false,
      isLocked: true,
      lockReason: 'Course non trouvée'
    };
  }

  const status = course.status || 'UNKNOWN';
  const invoiceFinalized = course.invoice_finalized === true || course.invoice_status === 'ISSUED';
  const clientConfirmed = course.client_confirmed === true || status === 'DONE';
  
  // Base conditions
  const isAssigned = status === DRIVER_STATUSES.ASSIGNED;
  const isInProgress = status === DRIVER_STATUSES.IN_PROGRESS;
  const isDriverCompleted = status === DRIVER_STATUSES.DRIVER_COMPLETED;
  const isDone = status === DRIVER_STATUSES.DONE;
  
  // Active ride states (can still modify)
  const isActiveRide = isAssigned || isInProgress || isDriverCompleted;
  
  // Locked states
  const isLocked = invoiceFinalized || clientConfirmed || isDone;
  
  // Actions
  const canStartRide = isAssigned && !isLocked;
  const canEndRide = isInProgress && !isLocked;
  
  // Supplements: Available from ASSIGNED through DRIVER_COMPLETED, unless locked
  // Rule: visible if status in [ASSIGNED, IN_PROGRESS, DRIVER_COMPLETED] 
  //       AND invoice_finalized=false AND client_confirmed=false
  const canAddSupplements = isActiveRide && !invoiceFinalized && !clientConfirmed;
  
  // Invoice preview: Available anytime for active rides
  const canGenerateInvoicePreview = isActiveRide || isDone;
  
  // Final invoice: Only available at DRIVER_COMPLETED, before client confirmation
  const canGenerateFinalInvoice = isDriverCompleted && !invoiceFinalized && !clientConfirmed;
  
  // Downloads: Always available (read-only)
  const canDownloadBonCommande = true;
  const canDownloadInvoice = true;
  
  // Lock reason for UI feedback
  let lockReason = null;
  if (invoiceFinalized) {
    lockReason = 'Facture finale générée';
  } else if (clientConfirmed || isDone) {
    lockReason = 'Confirmée par le client';
  }

  return {
    canStartRide,
    canEndRide,
    canAddSupplements,
    canGenerateInvoicePreview,
    canGenerateFinalInvoice,
    canDownloadBonCommande,
    canDownloadInvoice,
    isLocked,
    lockReason,
    // Additional metadata
    status,
    invoiceFinalized,
    clientConfirmed
  };
}

/**
 * Log driver actions state for debugging
 * 
 * @param {string} courseId - Course ID for logging
 * @param {Object} actions - Result from getDriverActions
 * @param {string} authMethod - Authentication method ('session' or 'token')
 */
export function logDriverActions(courseId, actions, authMethod = 'unknown') {
  const shortId = courseId?.slice(0, 8) || 'N/A';
  console.log(`[DRIVER-ACTIONS] course=${shortId} | status=${actions.status} | invoice_finalized=${actions.invoiceFinalized} | client_confirmed=${actions.clientConfirmed} | auth=${authMethod}`);
  console.log(`[DRIVER-ACTIONS] course=${shortId} | canStart=${actions.canStartRide} | canEnd=${actions.canEndRide} | canSupplements=${actions.canAddSupplements} | canFinalInvoice=${actions.canGenerateFinalInvoice} | locked=${actions.isLocked}`);
}

export default {
  getDriverActions,
  logDriverActions,
  DRIVER_STATUSES
};
