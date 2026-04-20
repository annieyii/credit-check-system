export function TechStack() {
  const technologies = [
    { name: "React", category: "前端框架" },
    { name: "Next.js", category: "全端框架" },
    { name: "TypeScript", category: "程式語言" },
    { name: "Tailwind CSS", category: "樣式框架" },
    { name: "Node.js", category: "後端環境" },
    { name: "PostgreSQL", category: "資料庫" },
    { name: "Vercel", category: "部署平台" },
    { name: "AWS", category: "雲端服務" },
  ]

  return (
    <section id="stack" className="py-24 px-6 border-y border-border">
      <div className="max-w-6xl">
        <div className="mb-16">
          <p className="font-mono text-sm text-accent mb-3">// 技術堆疊</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            使用現代化工具開發
          </h2>
          <p className="text-muted-foreground max-w-2xl">
            我們採用業界領先的技術，確保您的產品快速、安全且具備良好的擴展性。
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {technologies.map((tech) => (
            <div
              key={tech.name}
              className="group p-4 rounded-lg border border-border bg-card hover:border-accent/50 transition-all"
            >
              <p className="font-mono text-xs text-muted-foreground mb-1">{tech.category}</p>
              <p className="font-semibold group-hover:text-accent transition-colors">{tech.name}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
