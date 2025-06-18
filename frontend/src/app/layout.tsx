import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  FilePlus2,
  Users,
  Settings,
  Bot,
} from "lucide-react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/ThemeToggle";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RevClarity",
  description: "Your RCM Co-Pilot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen w-full bg-background font-sans antialiased",
          inter.className
        )}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="flex min-h-screen w-full flex-col">
            <div className="flex flex-1">
              {/* Sidebar */}
              <aside className="hidden w-64 flex-col border-r bg-background sm:flex">
                <nav className="flex flex-col gap-2 p-4">
                  <div className="mb-4 flex h-14 items-center gap-2 px-2">
                    <Bot className="h-8 w-8 text-primary" />
                    <h1 className="text-xl font-bold">RevClarity</h1>
                  </div>

                  <Button variant="ghost" className="w-full justify-start gap-2" asChild>
                    <Link href="/">
                      <LayoutDashboard className="h-4 w-4" />
                      Dashboard
                    </Link>
                  </Button>
                  <Button variant="ghost" className="w-full justify-start gap-2" asChild>
                    <Link href="/claim/new">
                      <FilePlus2 className="h-4 w-4" />
                      New Claim
                    </Link>
                  </Button>
                  <Button variant="ghost" className="w-full justify-start gap-2" asChild>
                    <Link href="/patients">
                      <Users className="h-4 w-4" />
                      Patients
                    </Link>
                  </Button>
                </nav>
                <div className="mt-auto p-4">
                  <Button variant="ghost" className="w-full justify-start gap-2" asChild>
                    <Link href="/settings">
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                  </Button>
                </div>
              </aside>

              {/* Main Content Area with Header */}
              <div className="flex flex-1 flex-col">
                <header className="flex h-14 items-center gap-4 border-b bg-background px-4 sm:px-6">
                  <div className="flex-1">
                    {/* Header content like a search bar can go here */}
                  </div>
                  <ThemeToggle />
                </header>
                <main className="flex-1 p-4 sm:p-6">
                  {children}
                </main>
              </div>
            </div>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}