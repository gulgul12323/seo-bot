import https from 'https';

export default async function handler(req, res) {
  const apiKey = process.env.YOUTH_CENTER_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "YOUTH_CENTER_API_KEY is not defined" });
  }

  const url = `https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey=${apiKey}&pageIndex=1&display=50`;

  return new Promise((resolve) => {
    // 공공기관 SSL 인증서 오류 무시 (rejectUnauthorized: false)
    const options = {
      rejectUnauthorized: false,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
      }
    };

    https.get(url, options, (apiRes) => {
      let data = '';
      
      apiRes.on('data', (chunk) => {
        data += chunk;
      });

      apiRes.on('end', () => {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Content-Type', 'text/xml; charset=utf-8');
        res.status(200).send(data);
        resolve();
      });
    }).on('error', (err) => {
      res.status(500).json({ error: err.message });
      resolve();
    });
  });
}
