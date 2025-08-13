"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Inbox, ListTodo, MessageSquare, BrainCircuit } from "lucide-react";

const navigation = [
  { name: "Document Inbox", href: "/orthopilot/inbox", icon: Inbox },
  { name: "Referral Task List", href: "/orthopilot/referrals", icon: ListTodo },
  { name: "Clinical Insights", href: "/orthopilot/insights", icon: BrainCircuit },
];

export default function OrthoPilotLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full">
      <div className="border-b">
        <div className="flex h-16 items-center px-4 sm:px-6 lg:px-8">
          <h1 className="text-xl font-bold tracking-tight">OrthoPilot POC</h1>
          <nav className="ml-10 flex items-center space-x-4 lg:space-x-6">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-primary",
                  pathname === item.href
                    ? "text-primary"
                    : "text-muted-foreground"
                )}
              >
                <item.icon className="mr-2 inline-block h-4 w-4" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>
      <div className="flex-1 p-4 sm:p-6 lg:p-8">{children}</div>
    </div>
  );
}