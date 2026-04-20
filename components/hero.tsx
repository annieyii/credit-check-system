import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"

export function Hero() {
  return (
    <section className="min-h-screen flex flex-col justify-center py-20 px-6">
      <div className="max-w-4xl">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-secondary/50 mb-8">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="text-xs text-muted-foreground">目前可接受新專案</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6 text-balance">
          打造卓越的
          <br />
          <span className="text-accent">數位產品</span>
        </h1>

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed">
          專業軟體開發工作室，專注於高效能網頁應用程式、行動 App 與客製化數位解決方案，
          為新創公司與企業提供最佳技術服務。
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          <Button size="lg" className="bg-accent hover:bg-accent/90 text-accent-foreground group">
            查看作品集
            <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Button>
          <Button variant="outline" size="lg" className="border-border hover:bg-secondary">
            預約諮詢
          </Button>
        </div>

        <div className="mt-20 grid grid-cols-2 sm:grid-cols-4 gap-8">
          {[
            { value: "50+", label: "完成專案" },
            { value: "8+", label: "年經驗" },
            { value: "99%", label: "客戶滿意度" },
            { value: "24/7", label: "技術支援" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-accent">{stat.value}</div>
              <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
