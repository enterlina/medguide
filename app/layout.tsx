import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppNavigation } from "@/components/app-navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedGuide — Your medication companion",
  description:
    "Understand medication interactions, timing, food instructions, and side effects in one clear view.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AppNavigation />
        {children}
      </body>
    </html>
  );
}
