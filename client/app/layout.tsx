import "./globals.css";
import { ReactNode } from "react";
import type { Metadata } from "next";
import Sidebar from "../components/Sidebar";
import { ThemeProvider } from "../components/theme-provider";
import { Inter } from "next/font/google";
import AuthProvider from "../components/AuthProvider";

export const metadata: Metadata = {
  title: "PolyChat AI",
};

// Opt out of static prerendering. This app uses auth/session and client-only behavior.
export const dynamic = "force-dynamic";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className="no-scrollbar">
      <body className={`${inter.className} min-h-screen selection:bg-primary selection:text-primary-foreground bg-hero-gradient bg-fixed text-foreground no-scrollbar`}>
        <AuthProvider>
          <ThemeProvider>
            {/* Background noise overlay */}
            <div className="absolute inset-0 bg-noise" aria-hidden />

            {/* Sidebar */}
            <Sidebar />

            {/* Main content area (account for sidebar width on md+) */}
            <div className="min-h-screen md:pl-64">
              <main className="pt-6 pb-10">
                {children}
              </main>
            </div>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}


