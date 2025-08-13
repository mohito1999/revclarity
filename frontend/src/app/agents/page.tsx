"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ArrowRight, Bot } from "lucide-react";

const agents = [
  {
    title: "Insurance Claims Follow-up",
    description: "An AI agent that follows up with insurance carriers to check the status of a submitted claim.",
    href: "/agents/claims-follow-up",
  },
  {
    title: "Patient Intake",
    description: "An AI agent that assists with the patient intake process, gathering necessary information.",
    href: "/agents/patient-intake",
  },
  {
    title: "Prior Authorization",
    description: "An AI agent that handles the prior authorization process with payers.",
    href: "/agents/prior-authorization",
  },
];

export default function VoiceAgentsSelectionPage() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4">
      <div className="flex items-center gap-4">
        <Bot className="h-8 w-8 text-primary" />
        <div>
            <h1 className="text-2xl font-bold tracking-tight">Voice Agent Demos</h1>
            <p className="text-muted-foreground">
                Select an agent to start a demonstration.
            </p>
        </div>
      </div>
      <div className="grid gap-6 pt-4 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent) => (
          <Link href={agent.href} key={agent.title} className="group">
            <Card className="h-full transition-all group-hover:border-primary group-hover:shadow-md">
              <CardHeader>
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle>{agent.title}</CardTitle>
                        <CardDescription className="pt-2">{agent.description}</CardDescription>
                    </div>
                    <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
