export default async function handler(req, res) {
  // Support both GET and POST for convenience
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const token = process.env.GH_PAT;
  const repo = process.env.GH_REPO;

  if (!token || !repo) {
    return res.status(500).json({
      status: "error",
      message: "Server environment misconfigured: missing GH_PAT or GH_REPO."
    });
  }

  try {
    const url = `https://api.github.com/repos/${repo}/actions/workflows/refresh-news.yml/dispatches`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'NR-Times-Vercel-Refresher'
      },
      body: JSON.stringify({
        ref: 'main'
      })
    });

    if (response.status === 204) {
      return res.status(200).json({
        status: "ok",
        message: "Workflow dispatch triggered successfully."
      });
    } else {
      const errorText = await response.text();
      return res.status(response.status).json({
        status: "error",
        message: `GitHub API returned status ${response.status}: ${errorText}`
      });
    }
  } catch (error) {
    return res.status(500).json({
      status: "error",
      message: error.message
    });
  }
}
