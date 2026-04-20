"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"
import { ArrowRight, Mail, MapPin, Clock } from "lucide-react"

export function Contact() {
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email && message) {
      setIsSubmitted(true)
      setEmail("")
      setMessage("")
    }
  }

  return (
    <section id="contact" className="py-24 px-6">
      <div className="max-w-6xl">
        <div className="grid lg:grid-cols-2 gap-16">
          <div>
            <p className="font-mono text-sm text-accent mb-3">// 聯絡我們</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
              一起打造精彩作品
            </h2>
            <p className="text-muted-foreground mb-8 leading-relaxed">
              有專案想法嗎？我們很樂意聽取您的需求。
              留下訊息，我們會在 24 小時內回覆您。
            </p>

            <div className="space-y-4">
              <div className="flex items-center gap-3 text-sm">
                <Mail className="h-4 w-4 text-accent" />
                <span className="font-mono">hello@judge.studio</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <MapPin className="h-4 w-4 text-accent" />
                <span>台北市信義區</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-accent" />
                <span>週一至週五，9:00 - 18:00</span>
              </div>
            </div>
          </div>

          <div>
            {isSubmitted ? (
              <div className="p-8 rounded-xl border border-accent/30 bg-accent/5">
                <p className="text-lg font-semibold mb-2">訊息已送出！</p>
                <p className="text-muted-foreground">
                  感謝您的來信，我們會盡快與您聯繫。
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-mono mb-2 text-muted-foreground">
                    電子郵件
                  </label>
                  <Input
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-card border-border font-mono"
                  />
                </div>
                <div>
                  <label className="block text-sm font-mono mb-2 text-muted-foreground">
                    訊息內容
                  </label>
                  <textarea
                    placeholder="請描述您的專案需求..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    required
                    rows={5}
                    className="w-full px-3 py-2 rounded-md bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none text-sm"
                  />
                </div>
                <Button 
                  type="submit" 
                  className="w-full bg-accent hover:bg-accent/90 text-accent-foreground group"
                >
                  送出訊息
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
