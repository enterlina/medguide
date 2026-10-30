"use client";

import { BookOpenText, Combine, Menu, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type NavigationItem = { label: string; href: string; icon?: LucideIcon };

const navigation: NavigationItem[] = [
  { label: "Taking & Combining", href: "/interactions", icon: Combine },
  { label: "What Studies Say", href: "/evidence-lens", icon: BookOpenText },
];

const coordinatorNavigation: NavigationItem[] = [
  { label: "Participants", href: "/coordinator-dashboard" },
  { label: "Studies", href: "/coordinator-dashboard#studies" },
  { label: "Protocol Rules", href: "/coordinator-dashboard#protocol-rules" },
  { label: "Reports", href: "/coordinator-dashboard#reports" },
  { label: "Settings", href: "/coordinator-dashboard#settings" },
];

export function AppNavigation() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const coordinatorMode = pathname.startsWith("/coordinator-dashboard");
  const currentNavigation = coordinatorMode
    ? coordinatorNavigation
    : navigation;

  return (
    <header className="sticky top-0 z-40 h-[77px] border-b border-border bg-white">
      <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-5 sm:px-8 lg:px-10">
        <Link
          href="/interactions"
          className="flex items-center rounded-[8px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy"
        >
          <span className="text-[20px] font-extrabold tracking-[-0.045em] text-brand-navy">
            Med<span className="text-brand-coral">Guide</span>
          </span>
        </Link>

        <nav
          aria-label="Primary navigation"
          className="absolute left-1/2 hidden -translate-x-1/2 items-center rounded-pill bg-surface-muted p-1 lg:flex"
        >
          {currentNavigation.map(({ label, href, icon: Icon }, index) => {
            const active = coordinatorMode
              ? index === 0
              : href === "/"
                ? pathname === "/" || pathname === "/clinical-trial-mode"
                : pathname.startsWith(href);
            return (
              <Link
                key={label}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`inline-flex min-w-[80px] items-center justify-center gap-2 rounded-pill px-4 py-2.5 text-center text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy ${
                  active
                    ? "bg-brand-navy text-white shadow-sm"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {Icon && <Icon size={15} />}
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((value) => !value)}
            className="grid size-10 place-items-center rounded-[12px] bg-surface-muted text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-navy lg:hidden"
          >
            {mobileOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav
          aria-label="Mobile navigation"
          className="absolute inset-x-0 top-[76px] grid gap-1 border-b border-border bg-white p-4 shadow-card lg:hidden"
        >
          {currentNavigation.map(({ label, href, icon: Icon }, index) => {
            const active = coordinatorMode
              ? index === 0
              : href === "/"
                ? pathname === "/" || pathname === "/clinical-trial-mode"
                : pathname.startsWith(href);
            return (
              <Link
                key={label}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2 rounded-[12px] px-4 py-3 text-[13px] font-semibold ${
                  active
                    ? "bg-brand-navy text-white"
                    : "text-text-secondary hover:bg-surface-muted"
                }`}
              >
                {Icon && <Icon size={16} />}
                {label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
