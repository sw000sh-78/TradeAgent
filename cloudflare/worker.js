// Cloudflare Worker: proxy TradingView -> compute HMAC header -> forward to app
// Deploy with `wrangler publish` and set secrets `SECRET_KEY` and `FORWARD_URL`.

export default {
  async fetch(request, env) {
    try {
      const forwardUrl = env.FORWARD_URL || env.WEBHOOK_URL;
      if (!forwardUrl) {
        return new Response('FORWARD_URL not configured', { status: 500 });
      }

      // Read raw request body as ArrayBuffer to compute HMAC over exact bytes
      const body = await request.arrayBuffer();

      // Compute HMAC-SHA256 hex using Web Crypto
      const secret = env.SECRET_KEY || env.WEBHOOK_SECRET || '';
      if (!secret) {
        return new Response('SECRET_KEY not configured', { status: 500 });
      }

      const signature = await computeHmacHex(secret, body);

      // Forward original body to target, preserving Content-Type
      const headers = new Headers();
      const contentType = request.headers.get('content-type') || 'application/json';
      headers.set('content-type', contentType);
      headers.set('x-signature', signature);

      // You can copy other headers as needed, e.g. user-agent
      const resp = await fetch(forwardUrl, { method: 'POST', headers, body });
      // Mirror response
      const respBody = await resp.arrayBuffer();
      const respHeaders = new Headers(resp.headers);
      return new Response(respBody, { status: resp.status, headers: respHeaders });
    } catch (err) {
      return new Response(String(err), { status: 500 });
    }
  }
};

async function computeHmacHex(secret, data) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, data);
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}
