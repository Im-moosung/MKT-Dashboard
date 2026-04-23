const jwt = require('jsonwebtoken');

module.exports = {
  checkAuth: (req, auth) => {
    if (!auth) throw new Error('No auth token');
    try {
      req.securityContext = jwt.verify(auth, process.env.CUBEJS_API_SECRET, { algorithms: ['HS256'] });
    } catch (e) {
      throw new Error(`JWT invalid: ${e.message}`);
    }
  },
  contextToAppId: ({ securityContext }) => `app_${securityContext?.user_id || 'anon'}`,
};
