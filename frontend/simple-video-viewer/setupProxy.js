const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // HTTP API 프록시
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  // WebSocket 프록시
  app.use(
    '/ws',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      ws: true,
      changeOrigin: true,
    })
  );
};
