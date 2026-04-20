"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"

export function CTA() {
  const [email, setEmail] = useState("")
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email) {
      setIsSubmitted(true)
      setEmail("")
    }
  }

  return (
    <section id="pricing" className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4 text-balance">
          Ready to transform your workflow?
        </h2>
        <p className="text-lg text-muted-foreground mb-8">
          Join thousands of teams already using Pulse. Start your free trial today.
        </p>

        {isSubmitted ? (
          <div className="bg-accent/10 border border-accent/30 rounded-lg p-6">
            <p className="text-foreground font-medium">Thanks for signing up!</p>
            <p className="text-sm text-muted-foreground mt-1">
              We&apos;ll be in touch soon with your access details.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <Input
              type="email"
              placeholder="Enter your work email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="flex-1"
            />
            <Button type="submit" className="bg-accent hover:bg-accent/90 text-foreground">
              Get Started
            </Button>
          </form>
        )}

        <p className="text-xs text-muted-foreground mt-4">
          Free 14-day trial. No credit card required.
        </p>
      </div>
    </section>
  )
}
