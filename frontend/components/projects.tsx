import { ArrowUpRight } from "lucide-react"

const projects = [
  {
    title: "智慧金流",
    category: "金融科技平台",
    description: "整合即時分析與 AI 洞察的全方位財務管理平台，協助企業優化資金調度。",
    tags: ["Next.js", "PostgreSQL", "Stripe"],
    year: "2024",
  },
  {
    title: "醫聯網",
    category: "醫療健康 App",
    description: "連結病患與醫療專業人員的遠距醫療平台，提供便捷的線上問診服務。",
    tags: ["React Native", "Node.js", "WebRTC"],
    year: "2024",
  },
  {
    title: "碳追蹤",
    category: "永續 SaaS",
    description: "企業碳足跡追蹤與永續發展報告系統，協助達成 ESG 目標。",
    tags: ["React", "Python", "ML"],
    year: "2023",
  },
]

export function Projects() {
  return (
    <section id="projects" className="py-24 px-6">
      <div className="max-w-6xl">
        <div className="mb-16">
          <p className="font-mono text-sm text-accent mb-3">// 專案作品</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            近期作品
          </h2>
          <p className="text-muted-foreground max-w-2xl">
            精選我們為客戶打造的專案作品。
          </p>
        </div>

        <div className="space-y-6">
          {projects.map((project, index) => (
            <div
              key={project.title}
              className="group p-6 sm:p-8 rounded-xl border border-border bg-card hover:border-accent/50 transition-all duration-300"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="font-mono text-xs text-muted-foreground">0{index + 1}</span>
                    <span className="text-xs text-accent font-mono">{project.category}</span>
                    <span className="text-xs text-muted-foreground">{project.year}</span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold mb-3 group-hover:text-accent transition-colors flex items-center gap-2">
                    {project.title}
                    <ArrowUpRight className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </h3>
                  <p className="text-muted-foreground mb-4 leading-relaxed max-w-2xl">
                    {project.description}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {project.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 rounded-md bg-secondary text-xs font-mono text-muted-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
