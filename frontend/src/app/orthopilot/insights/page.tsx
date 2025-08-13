"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Download, Send, User, Bot, Loader2 } from "lucide-react";

interface Message {
  sender: 'user' | 'ai';
  text: string;
}

export default function ClinicalInsightsPage() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages are added
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleExport = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    window.open(`${apiUrl}/orthopilot/modmed_notes/export`, "_blank");
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    const userMessage: Message = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/orthopilot/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: input }),
        });
        if (!response.ok) throw new Error("Failed to get a response from the AI.");
        const data = await response.json();
        const aiMessage: Message = { sender: 'ai', text: data.answer };
        setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
        const errorMessage: Message = { sender: 'ai', text: "Sorry, I encountered an error. Please try again." };
        setMessages(prev => [...prev, errorMessage]);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-h-[900px]">
      <div className="flex items-center justify-between p-6 flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Clinical Insights</h2>
          <p className="text-muted-foreground">Query your ModMed/EMA notes using natural language.</p>
        </div>
        <Button onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Export Extracted Data to Excel
        </Button>
      </div>

      <div className="flex-1 px-6 pb-6 min-h-0">
        <Card className="h-full flex flex-col">
          <CardContent className="flex-1 p-6 overflow-y-auto min-h-0">
            <div className="space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-muted-foreground h-full flex flex-col justify-center items-center min-h-[300px]">
                    <Bot className="h-12 w-12 mb-4"/>
                    <p className="font-semibold">Ask me anything about your ModMed documents.</p>
                    <p className="text-sm">e.g., "Summarize the visit for Patient TEST12" or "How many patients had a BMI over 30?"</p>
                </div>
              )}
              {messages.map((msg, index) => (
                <div key={index} className={`flex items-start gap-3 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                  {msg.sender === 'ai' && <Bot className="h-6 w-6 text-primary flex-shrink-0" />}
                  <div className={`rounded-lg p-3 max-w-lg break-words ${msg.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                    <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                  </div>
                  {msg.sender === 'user' && <User className="h-6 w-6 flex-shrink-0" />}
                </div>
              ))}
               {loading && (
                <div className="flex items-start gap-3">
                  <Bot className="h-6 w-6 text-primary flex-shrink-0" />
                  <div className="rounded-lg p-3 bg-muted flex items-center">
                    <Loader2 className="h-5 w-5 animate-spin"/>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </CardContent>
          <div className="p-4 border-t flex-shrink-0">
            <div className="flex items-center gap-2">
              <Input 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask a question about your documents..."
                disabled={loading}
              />
              <Button onClick={handleSendMessage} disabled={loading}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}