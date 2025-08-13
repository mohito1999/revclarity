"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, FileText, Download, Copy, Check, Plus, Trash2, Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

// --- Types ---
// Updated to match the actual API response structure
interface SuggestedAction {
  type: 'DIAGNOSIS' | 'PRESCRIPTION' | 'PROCEDURE' | 'REFERRAL' | 'FOLLOW_UP';
  summary: string; // The summary field that exists in your data
  details: {
    // DIAGNOSIS fields
    diagnosis?: string;
    suggested_code?: string;
    icd10?: string;
    
    // PRESCRIPTION fields (medication)
    medication?: string;
    sig?: string;
    quantity?: number;
    refills?: number;
    instructions?: string;
    notes?: string;
    
    // PRESCRIPTION fields (DME/device)
    device?: string;
    indication?: string;
    
    // PROCEDURE fields
    procedure?: string;
    name?: string;
    site?: string;
    laterality?: string;
    description?: string;
    
    // REFERRAL fields
    service?: string;
    reason?: string;
    priority?: string;
    
    // FOLLOW_UP fields
    timeframe?: string;
    when?: string;
    contingency?: string;
    
    // Allow other properties for flexibility
    [key: string]: any;
  };
}

interface MeriplexDocument {
  id: string;
  file_name: string;
  extracted_data: {
    raw_text: string;
    suggested_actions?: SuggestedAction[];
    extracted_note?: any; // Add this if you need it
  } | null;
  classification: string;
}

const ActionIcon = ({ type }: { type: SuggestedAction['type'] }) => {
  switch (type) {
    case 'DIAGNOSIS': return <span className="text-blue-500">🩺</span>;
    case 'PRESCRIPTION': return <span className="text-purple-500">💊</span>;
    case 'PROCEDURE': return <span className="text-green-500">💉</span>;
    case 'FOLLOW_UP': return <span className="text-orange-500">🗓️</span>;
    case 'REFERRAL': return <span className="text-teal-500">🤝</span>
    default: return <span>-</span>;
  }
};

// ActionCardContent component with proper typing
const ActionCardContent = ({ action }: { action: SuggestedAction }) => {
    let summary = action.summary || "Unknown Action";
    let details = "";

    const d = action.details;

    switch (action.type) {
        case 'DIAGNOSIS':
            summary = `Add Diagnosis: ${d.diagnosis || 'Unknown'}`;
            details = `Code: ${d.suggested_code || d.icd10 || 'N/A'}`;
            break;
        case 'PRESCRIPTION':
            const item = d.medication || d.device || 'Unknown item';
            summary = `Prescribe: ${item}`;
            details = d.instructions || d.indication || d.sig || "Take as directed.";
            break;
        case 'PROCEDURE':
            summary = `Perform Procedure: ${d.procedure || d.name || 'Unknown procedure'}`;
            const detailParts = [];
            if (d.description) detailParts.push(d.description);
            if (d.laterality) detailParts.push(`Laterality: ${d.laterality}`);
            if (d.site) detailParts.push(`Site: ${d.site}`);
            details = detailParts.length > 0 ? detailParts.join(' • ') : "No details provided.";
            break;
        case 'REFERRAL':
            summary = `Refer to: ${d.service || 'Unknown service'}`;
            details = d.reason || "No reason provided.";
            break;
        case 'FOLLOW_UP':
            summary = `Schedule Follow-up: ${d.timeframe || d.when || 'Unknown time'}`;
            const followUpDetails = [];
            if (d.reason) followUpDetails.push(d.reason);
            if (d.contingency) followUpDetails.push(`Contingency: ${d.contingency}`);
            details = followUpDetails.length > 0 ? followUpDetails.join(' • ') : "No reason provided.";
            break;
        default:
            summary = action.summary || `${action.type}: Unknown action`;
            details = "See full payload for details";
    }

    return (
        <div>
            <p className="font-medium text-sm">{summary}</p>
            <p className="text-xs text-muted-foreground">{details}</p>
        </div>
    );
};

// --- Main Component ---
export default function DocumentActionCenterPage() {
  const params = useParams();
  const docId = params.docId as string;
  const [doc, setDoc] = React.useState<MeriplexDocument | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [stagedActions, setStagedActions] = React.useState<SuggestedAction[]>([]);

  React.useEffect(() => {
    if (!docId) return;
    async function fetchDocument() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/orthopilot/documents/${docId}`);
        if (!response.ok) throw new Error("Failed to fetch document details.");
        const data = await response.json();
        setDoc(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchDocument();
  }, [docId]);

  const handleStageAction = (action: SuggestedAction) => {
    setStagedActions(prev => [...prev, action]);
  };

  const handleUnstageAction = (index: number) => {
    setStagedActions(prev => prev.filter((_, i) => i !== index));
  };
  
  const isActionStaged = (action: SuggestedAction) => {
    return stagedActions.some(staged => JSON.stringify(staged) === JSON.stringify(action));
  };

  if (loading) {
    return <div className="flex justify-center items-center h-full"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  }
  if (error || !doc) {
    return <div className="text-destructive">Error: {error || "Document not found."}</div>;
  }

  const data = doc.extracted_data;
  const suggestedActions = data?.suggested_actions || [];

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Action Center</h1>
        <p className="text-muted-foreground flex items-center gap-2">
          <FileText className="h-4 w-4" /> {doc.file_name}
          <Badge variant="outline">{doc.classification.replace(/_/g, ' ')}</Badge>
        </p>
      </div>

      {/* Main Two-Panel Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
        
        {/* Left Panel: Raw Text */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Original Document Text</CardTitle>
            <CardDescription>OCR output.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap font-sans text-muted-foreground">
              {data?.raw_text || "No text extracted."}
            </pre>
          </CardContent>
        </Card>

        {/* Right Panel: AI Actions & Staging */}
        <div className="space-y-6 flex flex-col">
          
          {/* AI Suggested Actions */}
          <Card className="flex-1 flex flex-col">
            <CardHeader>
              <CardTitle>AI Suggested Actions</CardTitle>
              <CardDescription>Review and stage actions for the EMR.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 overflow-y-auto">
              {suggestedActions.length > 0 ? (
                suggestedActions.map((action, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <ActionIcon type={action.type} />
                      <ActionCardContent action={action} />
                    </div>
                    <Button 
                      size="sm" 
                      variant={isActionStaged(action) ? "secondary" : "outline"}
                      onClick={() => handleStageAction(action)}
                      disabled={isActionStaged(action)}
                    >
                      {isActionStaged(action) ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                    </Button>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No specific actions suggested by AI for this document type.</p>
              )}
            </CardContent>
          </Card>

          {/* Staged EMR Payload */}
          <Card>
            <CardHeader>
              <CardTitle>Staged EMR Payload</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stagedActions.length > 0 ? (
                stagedActions.map((action, index) => (
                  <div key={index} className="flex items-center justify-between text-sm bg-secondary/50 p-2 rounded-md">
                     <div className="text-secondary-foreground"><ActionCardContent action={action} /></div>
                    <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => handleUnstageAction(index)}>
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground text-center py-2">No actions staged yet.</p>
              )}
            </CardContent>
            <div className="p-4 border-t">
                <Dialog>
                    <DialogTrigger asChild>
                        <Button className="w-full" disabled={stagedActions.length === 0}>
                            <Send className="mr-2 h-4 w-4" /> Generate EMR Payload
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Simulated EMR API Payload</DialogTitle>
                        </DialogHeader>
                        <div className="mt-4 bg-gray-100 dark:bg-gray-800 p-4 rounded-md overflow-x-auto">
                            <pre className="text-xs">
                                {JSON.stringify({ actions: stagedActions }, null, 2)}
                            </pre>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
}