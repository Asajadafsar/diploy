// fcm-worker.js - کد کامل و درست

export default {
  async fetch(request, env) {
    // فقط درخواست‌های POST
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    try {
      const body = await request.json();
      const { title, body: messageBody, data, topic, token, image_url } = body;

      if (!title || !messageBody) {
        return new Response(JSON.stringify({ error: 'title and body are required' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // دریافت Access Token از Firebase
      const accessToken = await getAccessToken(env);

      // ساخت پیام
      const message = {
        message: {
          notification: {
            title: title,
            body: messageBody,
          },
          data: data || {},
        }
      };

      if (image_url) {
        message.message.notification.image = image_url;
      }

      if (topic) {
        message.message.topic = topic;
      } else if (token) {
        message.message.token = token;
      } else {
        return new Response(JSON.stringify({ error: 'topic or token is required' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // ارسال به Firebase
      const response = await fetch(
        `https://fcm.googleapis.com/v1/projects/${env.FIREBASE_PROJECT_ID}/messages:send`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(message),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error?.message || 'Unknown error');
      }

      return new Response(JSON.stringify({
        success: true,
        message: 'Notification sent successfully',
        response: result,
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      console.error('Error:', error);
      return new Response(JSON.stringify({
        success: false,
        error: error.message,
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};

// دریافت Access Token از Firebase
async function getAccessToken(env) {
  // ✅ درست: از متغیر محیطی بخوان
  const serviceAccount = JSON.parse(env.FIREBASE_SERVICE_ACCOUNT);
  
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: serviceAccount.client_email,
    sub: serviceAccount.client_email,
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  };

  const header = { alg: 'RS256', typ: 'JWT' };
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const signatureInput = `${encodedHeader}.${encodedPayload}`;

  const encoder = new TextEncoder();
  const keyData = encoder.encode(serviceAccount.private_key);
  const key = await crypto.subtle.importKey(
    'pkcs8',
    keyData,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign(
    { name: 'RSASSA-PKCS1-v1_5' },
    key,
    encoder.encode(signatureInput)
  );

  const encodedSignature = btoa(String.fromCharCode(...new Uint8Array(signature)));
  const jwt = `${signatureInput}.${encodedSignature}`;

  const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: jwt,
    }),
  });

  const tokenData = await tokenResponse.json();

  if (!tokenResponse.ok) {
    throw new Error(tokenData.error_description || 'Failed to get access token');
  }

  return tokenData.access_token;
}