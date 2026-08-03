export default async function handler(req, res) {
  // 공공기관 SSL 보안 인증서 에러 우회 설정
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

  const apiKey = process.env.YOUTH_CENTER_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "YOUTH_CENTER_API_KEY is not defined" });
  }

  const url = `https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey=${apiKey}&pageIndex=1&display=50`;

  try {
    // fetch 함수는 302 리다이렉트를 자동으로 추적하여 최종 XML 데이터를 가져옵니다.
    const apiRes = await fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
      }
    });

    const xmlText = await apiRes.text();

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'text/xml; charset=utf-8');
    return res.status(200).send(xmlText);
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
