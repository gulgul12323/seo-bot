import https from 'https';
import http from 'http';
import { URL } from 'url';

// 302 리다이렉트 자동 추적 + SSL 보안 검사 우회 함수
function fetchWithRedirects(targetUrl, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects < 0) {
      return reject(new Error('Too many redirects from target server'));
    }

    const parsedUrl = new URL(targetUrl);
    const protocol = parsedUrl.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.pathname + parsedUrl.search,
      method: 'GET',
      rejectUnauthorized: false, // SSL 인증서 에러 무시
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
      }
    };

    const req = protocol.request(options, (res) => {
      // 301, 302 등 리다이렉트 응답 시 새 위치로 재요청
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        let redirectUrl = res.headers.location;
        if (!redirectUrl.startsWith('http')) {
          redirectUrl = new URL(redirectUrl, targetUrl).href;
        }
        return fetchWithRedirects(redirectUrl, maxRedirects - 1).then(resolve).catch(reject);
      }

      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => resolve(data));
    });

    req.on('error', (err) => reject(err));
    req.end();
  });
}

export default async function handler(req, res) {
  const apiKey = process.env.YOUTH_CENTER_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "YOUTH_CENTER_API_KEY is not defined" });
  }

  const url = `https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey=${apiKey}&pageIndex=1&display=50`;

  try {
    const xmlData = await fetchWithRedirects(url);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'text/xml; charset=utf-8');
    return res.status(200).send(xmlData);
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
