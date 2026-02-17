/**
 * Authentication Redirect Utilities
 * 
 * Single source of truth for redirect logic after driver login.
 * Avoids double-encoding issues and ensures consistent behavior.
 */

const REDIRECT_STORAGE_KEY = 'post_login_redirect';

/**
 * Build login URL with redirect parameter
 * @param {string} targetPath - Path to redirect to after login (e.g., "/claim/xxx")
 * @returns {string} Login URL with properly encoded redirect
 */
export function buildLoginRedirectUrl(targetPath) {
  // Ensure we only encode once
  const cleanPath = targetPath.startsWith('/') ? targetPath : `/${targetPath}`;
  return `/driver/login?redirect=${encodeURIComponent(cleanPath)}`;
}

/**
 * Store redirect target for after login
 * Called when redirecting to login from a protected page
 * @param {string} targetPath - Path to redirect to after login
 */
export function storeRedirectTarget(targetPath) {
  if (targetPath && !targetPath.includes('/driver/login')) {
    sessionStorage.setItem(REDIRECT_STORAGE_KEY, targetPath);
    console.log('[AUTH-REDIRECT] Stored redirect target:', targetPath);
  }
}

/**
 * Get and clear stored redirect target
 * Called after successful login to get the redirect destination
 * @returns {string|null} Stored redirect path or null
 */
export function getAndClearRedirectTarget() {
  const stored = sessionStorage.getItem(REDIRECT_STORAGE_KEY);
  if (stored) {
    sessionStorage.removeItem(REDIRECT_STORAGE_KEY);
    console.log('[AUTH-REDIRECT] Retrieved and cleared redirect target:', stored);
  }
  return stored;
}

/**
 * Extract redirect target from URL search params
 * Decodes the redirect param properly (handles single encoding)
 * @param {URLSearchParams} searchParams - URL search params
 * @returns {string|null} Decoded redirect path or null
 */
export function getRedirectFromParams(searchParams) {
  const redirectParam = searchParams.get('redirect');
  if (!redirectParam) return null;
  
  try {
    // Decode once - the param was encoded once when building the URL
    const decoded = decodeURIComponent(redirectParam);
    console.log('[AUTH-REDIRECT] Decoded redirect param:', decoded);
    return decoded;
  } catch (e) {
    console.error('[AUTH-REDIRECT] Failed to decode redirect param:', e);
    return redirectParam; // Return as-is if decoding fails
  }
}

/**
 * Get final redirect destination after login
 * Priority: 1) URL param, 2) sessionStorage, 3) default
 * @param {URLSearchParams} searchParams - URL search params
 * @param {string} defaultPath - Default path if no redirect found
 * @returns {string} Final redirect destination
 */
export function getPostLoginRedirect(searchParams, defaultPath = '/driver/courses') {
  // First check URL params (in case of direct link to login with redirect)
  const fromParams = getRedirectFromParams(searchParams);
  if (fromParams) {
    // Also clear any stored redirect to avoid confusion
    sessionStorage.removeItem(REDIRECT_STORAGE_KEY);
    return fromParams;
  }
  
  // Then check sessionStorage (set by pages that redirected to login)
  const fromStorage = getAndClearRedirectTarget();
  if (fromStorage) {
    return fromStorage;
  }
  
  // Default fallback
  return defaultPath;
}
