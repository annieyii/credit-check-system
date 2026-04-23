"use client"

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { 
  Code2, 
  Layers, 
  Users, 
  Briefcase, 
  MessageSquare, 
  Menu,
  X,
  Gavel
} from "lucide-react"

const navItems = [
  { icon: Code2, label: "服務項目", href: "#services" },
  { icon: Layers, label: "技術堆疊", href: "#stack" },
  { icon: Briefcase, label: "專案作品", href: "#projects" },
  { icon: Users, label: "團隊成員", href: "#team" },
  { icon: MessageSquare, label: "聯絡我們", href: "#contact" },
]

export function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-sidebar border-b border-sidebar-border">
        <div className="flex items-center justify-between px-4 h-14">
          <Link href="/" className="flex items-center gap-2">
            <Gavel className="h-5 w-5 text-accent" />
            <span className="font-bold text-sm">畢業審判官</span>
          </Link>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-2 text-muted-foreground hover:text-foreground"
            aria-label="開啟選單"
          >
            {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background/95 backdrop-blur-sm pt-14">
          <nav className="flex flex-col p-4 gap-2">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
              >
                <item.icon className="h-5 w-5" />
                <span className="text-sm">{item.label}</span>
              </Link>
            ))}
            <div className="mt-4 pt-4 border-t border-border">
              <Button className="w-full bg-accent hover:bg-accent/90 text-accent-foreground">
                開始專案
              </Button>
            </div>
          </nav>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex fixed left-0 top-0 bottom-0 w-64 flex-col bg-sidebar border-r border-sidebar-border z-50">
        <div className="p-6">
          <Link href="/" className="flex items-center gap-2">
            <Gavel className="h-6 w-6 text-accent" />
            <span className="font-bold">畢業審判官</span>
          </Link>
        </div>

        <nav className="flex-1 px-3">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors group"
                >
                  <item.icon className="h-4 w-4 group-hover:text-accent transition-colors" />
                  <span className="text-sm">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="p-4 border-t border-sidebar-border">
          <Button className="w-full bg-accent hover:bg-accent/90 text-accent-foreground text-sm">
            開始專案
          </Button>
          <p className="text-xs text-muted-foreground text-center mt-3">
            hello@judge.studio
          </p>
        </div>
      </aside>
    </>
  )
}
