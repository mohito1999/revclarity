// We will make this a client component to fetch data.
"use client"; 

import * as React from "react";
import { useParams } from "next/navigation";
import { Claim } from "@/lib/types"; // Import our types
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Download, Send } from "lucide-react";

// A small component for displaying key-value pairs
const InfoItem = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div>
    <p className="text-sm font-medium text-muted-foreground">{label}</p>
    <p className="text-base font-semibold">{value || "N/A"}</p>
  </div>
);

export default function ClaimWorkspacePage() {
  const params = useParams();
  const claimId = params.claimId as string;

  const [claim, setClaim] = React.useState<Claim | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false); // For button feedback

  React.useEffect(() => {
    if (!claimId) return;

    async function fetchClaimDetails() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/claims/${claimId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch claim details: ${response.statusText}`);
        }
        const claimData: Claim = await response.json();
        setClaim(claimData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchClaimDetails();
  }, [claimId]);

  // --- ACTION HANDLERS ---
  const handleSimulateOutcome = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/claims/${claimId}/simulate-outcome`, {
        method: 'POST',
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to simulate outcome.");
      }
      const updatedClaim = await response.json();
      setClaim(updatedClaim); // Update the UI with the new claim state
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExportPdf = () => {
    // Open the PDF export endpoint in a new tab
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    window.open(`${apiUrl}/claims/${claimId}/export/cms1500`, '_blank');
  };

  if (loading) return <div className="p-8">Loading claim workspace...</div>;
  if (error) return <div className="p-8 text-red-500">Error: {error}</div>;
  if (!claim) return <div className="p-8">Claim not found.</div>;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Claim Workspace</h1>
          <p className="text-muted-foreground font-mono text-sm">{claim.id}</p>
        </div>
        <Badge 
          className="text-lg capitalize"
          variant={claim.status === 'denied' ? 'destructive' : claim.status === 'approved' || claim.status === 'paid' ? 'default' : 'secondary'}
        >
          {claim.status}
        </Badge>
      </div>

      {/* Action Toolbar */}
      <div className="flex items-center space-x-2">
        <Button onClick={handleSimulateOutcome} disabled={isSubmitting || claim.status !== 'draft'}>
          <Send className="mr-2 h-4 w-4" />
          {isSubmitting ? "Submitting..." : "Submit & Simulate Outcome"}
        </Button>
        <Button variant="outline" onClick={handleExportPdf}>
          <Download className="mr-2 h-4 w-4" />
          Export PDF
        </Button>
      </div>

      {/* Main Grid Layout */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        
        {/* Claim Overview Card */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Claim Overview</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <InfoItem label="Payer Name" value={claim.payer_name} />
            <InfoItem label="Total Charge" value={`$${claim.total_charge_amount?.toFixed(2)}`} />
            <InfoItem label="Patient Responsibility" value={`$${claim.patient_responsibility_amount?.toFixed(2)}`} />
            <InfoItem label="Payer Paid Amount" value={`$${claim.payer_paid_amount?.toFixed(2)}`} />
            <InfoItem label="Date of Service" value={claim.date_of_service ? new Date(claim.date_of_service as string).toLocaleDateString() : 'N/A'} />
            <InfoItem label="Submission Date" value={claim.submission_date ? new Date(claim.submission_date).toLocaleDateString() : 'N/A'} />
            <InfoItem label="Adjudication Date" value={claim.adjudication_date ? new Date(claim.adjudication_date).toLocaleDateString() : 'N/A'} />
          </CardContent>
        </Card>

        {/* AI Co-Pilot Analysis Card */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>AI Co-Pilot Analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <InfoItem label="Eligibility Status" value={<Badge>{claim.eligibility_status}</Badge>} />
            <div>
              <p className="text-sm font-medium text-muted-foreground">Compliance Flags</p>
              {claim.compliance_flags && claim.compliance_flags.length > 0 ? (
                <ul className="list-disc pl-5 mt-1 space-y-1 text-sm">
                  {claim.compliance_flags.map((flag: any, index: number) => (
                    <li key={index} className={flag.level === 'error' ? 'text-destructive' : 'text-amber-600'}>
                      <span className="font-semibold">[{flag.level?.toUpperCase()}]</span> {flag.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground mt-1">No compliance issues found.</p>
              )}
            </div>
          </CardContent>
        </Card>
        
        {/* Denial Information Card (Conditional) */}
        {claim.status === 'denied' && (
           <Card className="lg:col-span-3 border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Denial Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <InfoItem label="Denial Reason" value={claim.denial_reason} />
              <InfoItem label="AI Root Cause Analysis" value={claim.denial_root_cause} />
              <InfoItem label="AI Recommended Action" value={claim.denial_recommended_action} />
            </CardContent>
          </Card>
        )}

        {/* Service Lines Card */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Service Lines</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>CPT Code</TableHead>
                  <TableHead>ICD-10 Codes</TableHead>
                  <TableHead>Diag. Ptr.</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead className="text-right">Charge</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {claim.service_lines?.length > 0 ? (
                  claim.service_lines.map((line) => (
                    <TableRow key={line.id}>
                      <TableCell className="font-medium">{line.cpt_code}</TableCell>
                      <TableCell>{line.icd10_codes.join(", ")}</TableCell>
                      <TableCell>{line.diagnosis_pointer}</TableCell>
                      <TableCell>{line.code_confidence_score ? `${(line.code_confidence_score * 100).toFixed(0)}%` : 'N/A'}</TableCell>
                      <TableCell className="text-right">${line.charge?.toFixed(2)}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="h-24 text-center">
                      No service lines found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}