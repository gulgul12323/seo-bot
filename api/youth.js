export default async function handler(req, res) {
  const apiKey = process.env.YOUTH_CENTER_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "YOUTH_CENTER_API_KEY is not defined" });
  }

  const url = `https://www.youthcenter.go.kr/opi/empSprtList.do?openApiVkey=${apiKey}&pageIndex=1&display=50`;

  try {
    const apiRes = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
      }
    });

    const xmlText = await apiRes.text();

    // CORS 허용 및 XML 헤더 전달
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'text/xml; charset=utf-8');
    return res.status(200).send(xmlText);
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
