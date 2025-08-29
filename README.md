<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>P2Engine: A Multi-Agent System Framework</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle {
            text-align: center;
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        
        .description {
            text-align: center;
            font-style: italic;
            margin-bottom: 20px;
        }
        
        .nav-links {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .nav-links a {
            color: #0366d6;
            text-decoration: none;
            margin: 0 5px;
        }
        
        .nav-links a:hover {
            text-decoration: underline;
        }
        
        .gallery {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 30px 0;
        }
        
        .gallery-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: #f8f9fa;
        }
        
        .gallery-item h3 {
            margin: 0;
            padding: 15px;
            background: #fff;
            border-bottom: 1px solid #ddd;
            text-align: center;
            font-size: 1.1em;
        }
        
        .gallery-item .image-container {
            width: 100%;
            height: 200px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .divider {
            text-align: center;
            margin: 40px 0;
            font-size: 2em;
            color: #666;
        }
        
        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 40px 0;
        }
        
        .section {
            margin: 30px 0;
        }
        
        .section h2 {
            font-size: 1.8em;
            margin-bottom: 15px;
        }
        
        .links {
            margin: 10px 0;
        }
        
        .links a {
            color: #0366d6;
            text-decoration: none;
        }
        
        .links a:hover {
            text-decoration: underline;
        }
        
        ul {
            padding-left: 20px;
        }
        
        li {
            margin-bottom: 8px;
        }
        
        em {
            font-style: italic;
        }
        
        strong {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <!-- Hero -->
    <h1>P2Engine: A Multi-Agent System Framework</h1>
    <p class="subtitle">
        A framework + runtime to build, run, and evaluate multi-agent systems. Extended with the Canton Network to enable monetary incentives, payments, and audits.
    </p>
    <p class="description">
        Orchestrate many AI agents with <em>observable</em> workflows, 
        <em>adaptive</em> evaluation loops, and an <em>auditable</em> trail.
    </p>
    <p class="nav-links">
        <a href="/p2engine/">Try it Out</a> •
        <a href="#primer">Demos</a> •
        <a href="#quicklinks">Article</a> •
        <a href="#roadmap">Hello</a> •
        <a href="#future">Future</a>
    </p>

    <div class="gallery">
        <div class="gallery-item">
            <h3>E1 — Orchestration</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>E2 — Observability</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>E3 — Adaptation Loops</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>E4 — Audit Layer</h3>
            <div class="image-container">Mock Image</div>
        </div>
    </div>

    <div class="divider">•</div>

    <div class="gallery">
        <div class="gallery-item">
            <h3>F1 — Integration</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>F2 — Scalability</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>F3 — Performance</h3>
            <div class="image-container">Mock Image</div>
        </div>
        <div class="gallery-item">
            <h3>F4 — Analytics</h3>
            <div class="image-container">Mock Image</div>
        </div>
    </div>

    <hr>

    <div class="section">
        <h2>Hello</h2>
        <div class="links">
            <strong><a href="REPO_URL">Test the framework on GitHub</a></strong> —
        </div>
        <p>P2Engine is a framework + runtime for multi-agent orchestration. Wire up LLM, rule-based, and human-in-loop agents; execute conversations through an auditable interaction stack; capture tool calls and results as artifacts; run judge/eval rollouts; and (optionally) settle incentives on a Canton ledger.</p>
        
        <ul>
            <li><strong>Test it now:</strong> <a href="REPO_URL">GitHub Repo</a> · Examples in <a href="demos/"><code>demos/</code></a></li>
            <li><strong>Docs (stubs):</strong> <a href="docs/"><code>docs/</code></a></li>
            <li><strong>Ledger guide:</strong> <a href="ledger.md"><code>ledger.md</code></a></li>
            <li><strong>Contact:</strong> adam.sioud@protonmail.com · surya.b.kathayat@ntnu.no</li>
            <li><strong>Agentic workflows</strong> without rigid pipelines.</li>
            <li><strong>Transparency</strong> — full runs are observable and auditable.</li>
            <li><strong>Self-improvement</strong> via judge/rollout-driven adaptation loops.</li>
            <li><strong>Incentives</strong> — balances, transfers, and rewards via Canton.</li>
        </ul>
        
        <p>P2Engine explores how multiple AI agents can coordinate, critique, and improve each other in open-ended tasks.<br>
        Think of it as a <em>framework</em> for multi-agent systems — but still evolving and work-in-progress.</p>
        
        <p>The framework emphasizes four pillars: <strong>orchestration</strong>, <strong>observability</strong>, <strong>adaptation</strong>, and <strong>auditability</strong>.<br>
        Agents collaborate through flexible workflows, log everything for inspection, learn via judge/rollout loops, and leave a tamper-evident trail for accountability. A DAML/Canton ledger integration enables balances, transfers, rewards, and an auditable payment trail between agents.</p>
    </div>

    <hr>

    <div class="section">
        <h2>Future</h2>
        <blockquote>
            <p>Have a little future ramble here</p>
        </blockquote>
    </div>
</body>
</html>
