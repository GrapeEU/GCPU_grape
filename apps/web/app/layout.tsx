import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Roboto_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { ThemeProvider } from "@/contexts/ThemeContext";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Grape - Knowledge Graph Explorer",
  description: "AI-powered knowledge graph visualization and querying platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${robotoMono.variable} antialiased`}
      >
        <ThemeProvider>
          <div className="min-h-screen bg-[#FDFDFD] text-[#1C1C1C]">
            <header className="border-b border-[#E5E7EB] bg-white/70 backdrop-blur-sm">
              <nav className="mx-auto flex max-w-5xl items-center justify-center gap-8 px-6 py-4 text-sm font-medium text-[#4B5563]">
                <Link
                  href="/"
                  className="transition-colors hover:text-[#E57373]"
                >
                  Home
                </Link>
                <Link
                  href="/concept"
                  className="transition-colors hover:text-[#E57373]"
                >
                  Concept
                </Link>
                <Link
                  href="/how-it-works"
                  className="transition-colors hover:text-[#E57373]"
                >
                  How it works
                </Link>
                <Link
                  href="/thanks"
                  className="transition-colors hover:text-[#E57373]"
                >
                  Thanks
                </Link>
              </nav>
            </header>
            <main>{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
