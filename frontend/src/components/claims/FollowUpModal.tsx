"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Phone, Loader, Bot, User, CheckCircle, AlertTriangle } from "lucide-react";
import { Progress } from "@/components/ui/progress";

type Stage = "idle" | "dialing" | "menu" | "hold" | "speaking" | "success" | "error";

const stageMessages: Record<Stage, { icon: React.ReactNode, title: string, message: string }> = {
  idle: { icon: <Phone />, title: "Ready to Call", message: "Start AI follow-up for this claim." },
  dialing: { icon: <Phone className="animate-pulse text-blue-500" />, title: "Dialing Payer...", message: "Connecting to HealthFirst Insurance..." },
  menu: { icon: <Bot className="text-blue-500" />, title: "Navigating IVR Menu", message: "AI is selecting: 'For Providers' -> 'Check Claim Status'." },
  hold: { icon: <Loader className="animate-spin text-amber-500" />, title: "On Hold", message: "Your estimated wait time is less than 2 minutes." },
  speaking: { icon: <User className="text-blue-500" />, title: "Speaking with Agent", message: "AI is verifying patient details and claim number with the live agent." },
  success: { icon: <CheckCircle className="text-green-500" />, title: "Success!", message: "Claim status retrieved. The claim has been adjudicated." },
  error: { icon: <AlertTriangle className="text-destructive" />, title: "Error", message: "Could not retrieve claim status." },
};

interface FollowUpModalProps {
  claimId: string | null;
  onOpenChange: (open: boolean) => void;
  onComplete: () => void;
}

export function FollowUpModal({ claimId, onOpenChange, onComplete }: FollowUpModalProps) {
  const [stage, setStage] = React.useState<Stage>("idle");
  const [progress, setProgress] = React.useState(0);

  React.useEffect(() => {
    // Reset the modal state when a new claim is selected or it's closed
    if (claimId) {
      setStage("idle");
      setProgress(0);
    }
  }, [claimId]);

  const runSimulation = async () => {
    if (!claimId) return;

    // Stage 1: Dialing
    setStage("dialing");
    await new Promise(res => setTimeout(res, 2000));

    // Stage 2: Navigating Menu
    setStage("menu");
    await new Promise(res => setTimeout(res, 3000));
    
    // Stage 3: On Hold
    setStage("hold");
    const holdInterval = setInterval(() => {
      setProgress(p => (p >= 90 ? 90 : p + 15));
    }, 1500);
    await new Promise(res => setTimeout(res, 10000));
    clearInterval(holdInterval);

    // Stage 4: Speaking
    setStage("speaking");
    setProgress(95);
    await new Promise(res => setTimeout(res, 4000));

    // Final Stage: Trigger real adjudication
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/claims/${claimId}/simulate-outcome`, { method: 'POST' });
      if (!response.ok) throw new Error("Adjudication failed");
      
      setStage("success");
      setProgress(100);
      await new Promise(res => setTimeout(res, 2000));
      onComplete();
    } catch (e) {
      setStage("error");
    }
  };

  const currentStage = stageMessages[stage];

  return (
    <Dialog open={!!claimId} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {currentStage.icon}
            {currentStage.title}
          </DialogTitle>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <p className="text-muted-foreground">{currentStage.message}</p>
          {(stage === 'hold' || stage === 'speaking') && <Progress value={progress} className="w-full" />}
          {stage === 'idle' && (
            <Button onClick={runSimulation} className="w-full">
              <Phone className="mr-2 h-4 w-4" /> Start AI Call
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}