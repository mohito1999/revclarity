"use client";

import * as React from "react";
import Script from "next/script";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

// Updated declaration to include all widget props
declare global {
  namespace JSX {
    interface IntrinsicElements {
      "vapi-widget": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        "public-key"?: string;
        "assistant-id"?: string;
        "mode"?: string;
        "theme"?: string;
        "base-bg-color"?: string;
        "accent-color"?: string;
        "cta-button-color"?: string;
        "cta-button-text-color"?: string;
        "border-radius"?: string;
        "size"?: string;
        "position"?: string;
        "title"?: string;
        "start-button-text"?: string;
        "end-button-text"?: string;
        "chat-first-message"?: string;
        "chat-placeholder"?: string;
        "voice-show-transcript"?: string;
        "consent-required"?: string;
        "consent-title"?: string;
        "consent-content"?: string;
        "consent-storage-key"?: string;
      };
    }
  }
}

export default function PriorAuthAgentPage() {
  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <Button asChild variant="outline">
          <Link href="/agents">
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Agents
          </Link>
        </Button>
      </div>
      <div className="flex flex-col items-center justify-center flex-grow">
        <div className="text-center mb-8">
            <h1 className="text-2xl font-bold">Prior Authorization Agent</h1>
            <p className="text-muted-foreground">The AI agent widget is active below.</p>
        </div>
        <vapi-widget
            public-key="5c118499-8f05-4e3b-984e-915364c68cc4"
            assistant-id="5fba58b7-5e82-480b-b7ed-64b77876802c"
            mode="voice"
            theme="dark"
            base-bg-color="#000000"
            accent-color="#14B8A6"
            cta-button-color="#000000"
            cta-button-text-color="#ffffff"
            border-radius="large"
            title="TALK WITH AI"
            start-button-text="Start"
            end-button-text="End Call"
            chat-first-message="Hey, How can I help you today?"
            chat-placeholder="Type your message..."
            voice-show-transcript="true"
            consent-required="true"
            consent-title="Terms and conditions"
            consent-content="By clicking 'Agree,' and each time I interact with this AI agent, I consent to the recording, storage, and sharing of my communications with third-party service providers, and as otherwise described in our Terms of Service."
            consent-storage-key="vapi_widget_consent"
        ></vapi-widget>
      </div>
      <Script
        src="https://unpkg.com/@vapi-ai/client-sdk-react/dist/embed/widget.umd.js"
        strategy="afterInteractive"
        async
      />
    </div>
  );
}