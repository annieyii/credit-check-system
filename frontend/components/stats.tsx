export function Stats() {
  const stats = [
    { value: "20 days", label: "saved on average per quarter" },
    { value: "98%", label: "faster time to market" },
    { value: "300%", label: "increase in team productivity" },
    { value: "6x", label: "faster to deploy changes" },
  ]

  return (
    <section className="py-16 border-y border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-0 lg:divide-x divide-border">
          {stats.map((stat, index) => (
            <div key={index} className="text-center lg:px-8">
              <div className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
                {stat.value}
              </div>
              <div className="text-sm text-muted-foreground">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
