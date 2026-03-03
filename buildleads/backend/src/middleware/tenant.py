"""Tenant isolation middleware — ensures all DB queries are scoped to the current tenant.

Currently, tenant isolation is enforced at the service/router level
(user.tenant_id filtering). This middleware is reserved for future use
(e.g., PostgreSQL Row Level Security or session-level SET).
"""

# Placeholder — tenant isolation is handled in service functions via user.tenant_id.
# When RLS is enabled, this middleware will set the tenant context per request.
