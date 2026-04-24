const jwt = require('jsonwebtoken');

// W1 POC: single-tenant. contextToAppId intentionally omitted — multitenancy
// without driverFactory/scheduledRefreshContexts triggered silent empty /meta
// (see docs/status.md Cube P0 fix). Re-add with full multitenancy wiring if
// per-user data sources become a W2 requirement.
module.exports = {
  checkAuth: (req, auth) => {
    if (!auth) throw new Error('No auth token');
    try {
      req.securityContext = jwt.verify(auth, process.env.CUBEJS_API_SECRET, { algorithms: ['HS256'] });
    } catch (e) {
      throw new Error(`JWT invalid: ${e.message}`);
    }
  },
};
