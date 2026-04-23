const team = [
  {
    name: "陳柏翰",
    role: "創辦人 & 技術總監",
    bio: "10 年以上大型網頁應用開發經驗",
  },
  {
    name: "林雅婷",
    role: "設計總監",
    bio: "曾任知名科技公司設計主管",
  },
  {
    name: "王俊傑",
    role: "後端架構師",
    bio: "專精分散式系統架構設計",
  },
  {
    name: "張家瑜",
    role: "行動開發負責人",
    bio: "跨平台開發專家",
  },
]

export function Team() {
  return (
    <section id="team" className="py-24 px-6 border-t border-border">
      <div className="max-w-6xl">
        <div className="mb-16">
          <p className="font-mono text-sm text-accent mb-3">// 團隊成員</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            程式碼背後的人
          </h2>
          <p className="text-muted-foreground max-w-2xl">
            由經驗豐富的開發者與設計師組成的精實團隊，熱衷於打造優質產品。
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {team.map((member) => (
            <div
              key={member.name}
              className="group p-6 rounded-xl border border-border bg-card hover:border-accent/50 transition-all"
            >
              <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center mb-4">
                <span className="font-bold text-accent">
                  {member.name.charAt(0)}
                </span>
              </div>
              <h3 className="font-semibold mb-1">{member.name}</h3>
              <p className="text-sm text-accent font-mono mb-2">{member.role}</p>
              <p className="text-sm text-muted-foreground">{member.bio}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
