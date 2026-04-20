import { Zap, Users, BarChart3, Shield, Clock, Globe } from "lucide-react"

export function Features() {
  const features = [
    {
      icon: Zap,
      title: "Lightning Fast",
      description: "Real-time collaboration that keeps pace with your team. No lag, no delays.",
    },
    {
      icon: Users,
      title: "Team Workspaces",
      description: "Organize projects, share files, and communicate seamlessly in one place.",
    },
    {
      icon: BarChart3,
      title: "Smart Analytics",
      description: "Get insights into team performance and project progress with detailed reports.",
    },
    {
      icon: Shield,
      title: "Enterprise Security",
      description: "Bank-level encryption and compliance certifications to keep your data safe.",
    },
    {
      icon: Clock,
      title: "Time Tracking",
      description: "Automatic time tracking and timesheets for better project management.",
    },
    {
      icon: Globe,
      title: "Global Access",
      description: "Work from anywhere with cloud-based tools and mobile apps for iOS and Android.",
    },
  ]

  return (
    <section id="features" className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-sm font-medium text-accent mb-4">Features</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4 text-balance">
            Everything you need to ship faster
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Powerful tools designed to help your team focus on what matters most.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-6 rounded-xl border border-border bg-card hover:border-accent/50 hover:shadow-lg transition-all duration-300"
            >
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <feature.icon className="h-6 w-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
