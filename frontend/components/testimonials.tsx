import { Card, CardContent } from "@/components/ui/card"

export function Testimonials() {
  const testimonials = [
    {
      quote: "Pulse has transformed how our team works. We&apos;ve cut our meeting time in half and ship features twice as fast.",
      author: "Sarah Chen",
      role: "VP of Engineering",
      company: "TechFlow",
    },
    {
      quote: "The best investment we&apos;ve made for our remote team. Communication is seamless and everyone stays aligned.",
      author: "Marcus Johnson",
      role: "CEO",
      company: "StartupX",
    },
    {
      quote: "Finally, a tool that actually helps us collaborate instead of getting in the way. Our productivity is through the roof.",
      author: "Emily Rodriguez",
      role: "Product Manager",
      company: "InnovateCo",
    },
  ]

  return (
    <section id="testimonials" className="py-24 px-4 sm:px-6 lg:px-8 bg-muted/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-sm font-medium text-accent mb-4">Testimonials</p>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4 text-balance">
            Loved by teams worldwide
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            See what our customers have to say about their experience with Pulse.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <Card key={index} className="border-border">
              <CardContent className="p-6">
                <blockquote className="text-foreground mb-6 leading-relaxed">
                  &quot;{testimonial.quote}&quot;
                </blockquote>
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
                    <span className="text-sm font-medium text-accent">
                      {testimonial.author.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <div className="font-medium text-sm">{testimonial.author}</div>
                    <div className="text-sm text-muted-foreground">
                      {testimonial.role}, {testimonial.company}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
