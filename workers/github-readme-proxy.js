/**
 * GitHub README 代理 Worker
 * 用于解决跨域和网络墙问题
 *
 * 部署步骤：
 * 1. 登录 Cloudflare -> Workers & Pages
 * 2. Create application -> Create Worker
 * 3. 复制此代码到编辑器中
 * 4. Save and deploy
 *
 * 使用方式：
 * GET https://your-worker.workers.dev/?owner=vuejs&repo=core
 */

export default {
  async fetch(request, env, ctx) {
    // 处理 OPTIONS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    const url = new URL(request.url);
    const owner = url.searchParams.get('owner');
    const repo = url.searchParams.get('repo');
    const branch = url.searchParams.get('branch') || 'main';
    const file = url.searchParams.get('file') || 'README.md';

    // 根路径返回使用说明
    if (!owner && !repo) {
      return new Response(
        JSON.stringify({
          message: 'GitHub README Proxy',
          usage: '?owner=OWNER&repo=REPO',
          example: '?owner=vuejs&repo=core',
        }),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }

    // 参数校验
    if (!owner || !repo) {
      return new Response(
        JSON.stringify({ error: 'Missing required params: owner and repo' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }

    // 尝试不同分支
    const branches = branch === 'main' ? ['main', 'master'] : [branch];

    for (const b of branches) {
      const targetUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${b}/${file}`;

      try {
        const response = await fetch(targetUrl, {
          headers: {
            'User-Agent': 'GitHub-README-Proxy/1.0',
          },
        });

        if (response.ok) {
          const content = await response.text();

          return new Response(content, {
            status: 200,
            headers: {
              'Content-Type': 'text/plain; charset=utf-8',
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Methods': 'GET, OPTIONS',
              'Cache-Control': 'public, max-age=3600',
            },
          });
        }
      } catch (e) {
        // 继续尝试下一个分支
        continue;
      }
    }

    return new Response(
      JSON.stringify({ error: 'README not found', tried: branches }),
      {
        status: 404,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  },
};