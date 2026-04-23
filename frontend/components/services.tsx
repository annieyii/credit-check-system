import { Globe, Smartphone, Cloud, Cpu, Database, Shield } from "lucide-react"

const services = [
  {
    icon: Globe,
    title: "網頁開發",
    description: "使用 React、Next.js 等現代框架打造高效能網頁應用程式。",
    tags: ["React", "Next.js", "TypeScript"],
  },
  {
    icon: Smartphone,
    title: "行動 App",
    description: "為 iOS 與 Android 開發原生及跨平台行動應用程式。",
    tags: ["React Native", "Swift", "Kotlin"],
  },
  {
    icon: Cloud,
    title: "雲端方案",
    description: "可擴展的雲端基礎設施與 DevOps 自動化部署。",
    tags: ["AWS", "Vercel", "Docker"],
  },
  {
    icon: Cpu,
    title: "AI 整合",
    description: "將最先進的 AI 與機器學習技術整合到您的產品中。",
    tags: ["OpenAI", "LangChain", "ML"],
  },
  {
    icon: Database,
    title: "後端系統",
    description: "穩健的 API 與資料庫架構，隨業務規模彈性擴展。",
    tags: ["Node.js", "PostgreSQL", "Redis"],
  },
  {
    icon: Shield,
    title: "資安服務",
    description: "企業級資安稽核與實作，確保應用程式安全無虞。",
    tags: ["驗證", "加密", "合規"],
  },
]

export function Services() {
  return (
    <section id="services" className="py-24 px-6">
      <div className="max-w-6xl">
        <div className="mb-16">
          <p className="font-mono text-sm text-accent mb-3">// 服務項目</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            我們的專業領域
          </h2>
          <p className="text-muted-foreground max-w-2xl">
            從概念到上線，提供端到端的開發服務，將您的想法化為現實。
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service) => (
            <div
              key={service.title}
              className="group p-6 rounded-xl border border-border bg-card hover:border-accent/50 transition-all duration-300"
            >
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <service.icon className="h-6 w-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{service.title}</h3>
              <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                {service.description}
              </p>
              <div className="flex flex-wrap gap-2">
                {service.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 rounded-md bg-secondary text-xs font-mono text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
