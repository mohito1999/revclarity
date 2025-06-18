// We will make this a client component to fetch data.
"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Claim, ServiceLine } from "@/lib/types"; // Import our types
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Download, Edit, Save, Send, XCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

// Expanded schema for full editability
const claimFormSchema = z.object({
  payer_name: z.string().nullable(),
  total_charge_amount: z.coerce.number().nullable(),
  patient_responsibility_amount: z.coerce.number().nullable(),
  date_of_service: z.string().nullable(),
  insurance_type: z.string().nullable(),
  insured_id_number: z.string().nullable(),
  insured_name: z.string().nullable(),
  insured_address: z.string().nullable(),
  is_condition_related_to_employment: z.boolean().nullable(),
  is_condition_related_to_auto_accident: z.boolean().nullable(),
  is_condition_related_to_other_accident: z.boolean().nullable(),
  insured_policy_group_or_feca_number: z.string().nullable(),
  date_of_current_illness: z.string().nullable(),
  referring_provider_name: z.string().nullable(),
  referring_provider_npi: z.string().nullable(),
  prior_authorization_number: z.string().nullable(),
  federal_tax_id_number: z.string().nullable(),
  patient_account_no: z.string().nullable(),
  accept_assignment: z.boolean().nullable(),
  amount_paid_by_patient: z.coerce.number().nullable(),
  service_facility_location_info: z.string().nullable(),
  billing_provider_info: z.string().nullable(),
  billing_provider_npi: z.string().nullable(),
});

type ClaimFormData = z.infer<typeof claimFormSchema>;

const InfoItem = ({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) => (
  <div>
    <p className="text-sm font-medium text-muted-foreground">{label}</p>
    <p className="text-base font-semibold">{value || "N/A"}</p>
  </div>
);

// Helper to format dates for input type="date"
const formatDateForInput = (dateString: string | null | undefined) => {
  if (!dateString) return "";
  try {
    // Handle potential timezone issues by parsing as UTC
    const date = new Date(dateString);
    const utcDate = new Date(date.getTime() + date.getTimezoneOffset() * 60000);
    return utcDate.toISOString().split("T")[0];
  } catch (e) {
    return "";
  }
};

export default function ClaimWorkspacePage() {
  const params = useParams();
  const claimId = params.claimId as string;

  const [claim, setClaim] = React.useState<Claim | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);

  const form = useForm<ClaimFormData>({
    resolver: zodResolver(claimFormSchema),
  });

  const resetFormWithClaimData = React.useCallback(
    (claimData: Claim) => {
      form.reset({
        payer_name: claimData.payer_name,
        total_charge_amount: claimData.total_charge_amount,
        patient_responsibility_amount: claimData.patient_responsibility_amount,
        date_of_service: formatDateForInput(claimData.date_of_service),
        insurance_type: claimData.insurance_type,
        insured_id_number: claimData.insured_id_number,
        insured_name: claimData.insured_name,
        insured_address: claimData.insured_address,
        is_condition_related_to_employment:
          claimData.is_condition_related_to_employment,
        is_condition_related_to_auto_accident:
          claimData.is_condition_related_to_auto_accident,
        is_condition_related_to_other_accident:
          claimData.is_condition_related_to_other_accident,
        insured_policy_group_or_feca_number:
          claimData.insured_policy_group_or_feca_number,
        date_of_current_illness: formatDateForInput(
          claimData.date_of_current_illness
        ),
        referring_provider_name: claimData.referring_provider_name,
        referring_provider_npi: claimData.referring_provider_npi,
        prior_authorization_number: claimData.prior_authorization_number,
        federal_tax_id_number: claimData.federal_tax_id_number,
        patient_account_no: claimData.patient_account_no,
        accept_assignment: claimData.accept_assignment,
        amount_paid_by_patient: claimData.amount_paid_by_patient,
        service_facility_location_info: claimData.service_facility_location_info,
        billing_provider_info: claimData.billing_provider_info,
        billing_provider_npi: claimData.billing_provider_npi,
      });
    },
    [form]
  );

  const fetchClaimDetails = React.useCallback(
    async (isSilent = false) => {
      if (!claimId) return;
      if (!isSilent) setLoading(true);
      setError(null);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/claims/${claimId}`);
        if (!response.ok) {
          throw new Error(
            `Failed to fetch claim details: ${response.statusText}`
          );
        }
        const claimData: Claim = await response.json();
        setClaim(claimData);
        resetFormWithClaimData(claimData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        if (!isSilent) setLoading(false);
      }
    },
    [claimId, resetFormWithClaimData]
  );

  React.useEffect(() => {
    if (claimId) {
      fetchClaimDetails();
    }
  }, [claimId, fetchClaimDetails]);

  // --- ACTION HANDLERS ---
  const handleSimulateOutcome = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(
        `${apiUrl}/claims/${claimId}/simulate-outcome`,
        {
          method: "POST",
        }
      );
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to simulate outcome.");
      }
      const updatedClaim = await response.json();
      setClaim(updatedClaim);
      resetFormWithClaimData(updatedClaim);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExportPdf = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    window.open(`${apiUrl}/claims/${claimId}/export/cms1500`, "_blank");
  };

  const handleSaveChanges = async (values: ClaimFormData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/claims/${claimId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        throw new Error(
          (await response.json()).detail || "Failed to save changes."
        );
      }

      const updatedClaim = await response.json();
      setClaim(updatedClaim);
      resetFormWithClaimData(updatedClaim);
      setIsEditing(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-8">Loading claim workspace...</div>;
  if (error && !claim) return <div className="p-8 text-red-500">Error: {error}</div>;
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
          variant={
            claim.status === "denied"
              ? "destructive"
              : claim.status === "approved" || claim.status === "paid"
              ? "default"
              : "secondary"
          }
        >
          {claim.status}
        </Badge>
      </div>

      {/* Action Toolbar (Outside Form) */}
      <div className="flex items-center space-x-2">
        {!isEditing ? (
          <>
            <Button type="button" onClick={() => setIsEditing(true)}>
              <Edit className="mr-2 h-4 w-4" /> Edit Claim
            </Button>
            <Button
              type="button"
              onClick={handleSimulateOutcome}
              disabled={isSubmitting || !["draft", "denied"].includes(claim.status)}
            >
              <Send className="mr-2 h-4 w-4" />
              {isSubmitting ? "Submitting..." : "Submit & Simulate Outcome"}
            </Button>
            <Button type="button" variant="outline" onClick={handleExportPdf}>
              <Download className="mr-2 h-4 w-4" />
              Export PDF
            </Button>
          </>
        ) : (
          <>
            <Button
              type="button"
              onClick={form.handleSubmit(handleSaveChanges)}
              disabled={isSubmitting}
            >
              <Save className="mr-2 h-4 w-4" />
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setIsEditing(false);
                resetFormWithClaimData(claim);
              }}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          </>
        )}
      </div>

      {error && (
        <p className="text-sm font-medium text-destructive bg-destructive/10 p-3 rounded-md">
          {error}
        </p>
      )}

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(handleSaveChanges)}
          className="space-y-6"
        >
          <Card>
            <CardHeader>
              <CardTitle>Claim Overview</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {isEditing ? (
                <>
                  <FormField
                    control={form.control}
                    name="payer_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Payer Name</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="total_charge_amount"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Total Charge</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.01"
                            {...field}
                            value={field.value ?? ""}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="patient_responsibility_amount"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Patient Responsibility</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.01"
                            {...field}
                            value={field.value ?? ""}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <InfoItem
                    label="Payer Paid Amount"
                    value={`$${claim.payer_paid_amount?.toFixed(2) ?? '0.00'}`}
                  />
                  <FormField
                    control={form.control}
                    name="date_of_service"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Date of Service</FormLabel>
                        <FormControl>
                          <Input
                            type="date"
                            {...field}
                            value={field.value ?? ""}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              ) : (
                <>
                  <InfoItem label="Payer Name" value={claim.payer_name} />
                  <InfoItem
                    label="Total Charge"
                    value={`$${claim.total_charge_amount?.toFixed(2)}`}
                  />
                  <InfoItem
                    label="Patient Responsibility"
                    value={`$${claim.patient_responsibility_amount?.toFixed(2)}`}
                  />
                  <InfoItem
                    label="Payer Paid Amount"
                    value={`$${claim.payer_paid_amount?.toFixed(2)}`}
                  />
                  <InfoItem
                    label="Date of Service"
                    value={
                      claim.date_of_service
                        ? new Date(claim.date_of_service).toLocaleDateString()
                        : "N/A"
                    }
                  />
                </>
              )}
              <InfoItem
                label="Submission Date"
                value={
                  claim.submission_date
                    ? new Date(claim.submission_date).toLocaleDateString()
                    : "N/A"
                }
              />
              <InfoItem
                label="Adjudication Date"
                value={
                  claim.adjudication_date
                    ? new Date(claim.adjudication_date).toLocaleDateString()
                    : "N/A"
                }
              />
            </CardContent>
          </Card>

          {isEditing && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Patient & Insured Details</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <FormField
                    control={form.control}
                    name="insurance_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Insurance Type</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="insured_id_number"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Insured's ID</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="insured_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Insured's Name</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="insured_policy_group_or_feca_number"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Policy/Group #</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="insured_address"
                    render={({ field }) => (
                      <FormItem className="col-span-2 md:col-span-4">
                        <FormLabel>Insured's Address</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Health & Condition Details</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                  <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-8">
                    <FormField
                      control={form.control}
                      name="date_of_current_illness"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Date of Illness</FormLabel>
                          <FormControl>
                            <Input
                              type="date"
                              {...field}
                              value={field.value ?? ""}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="prior_authorization_number"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Prior Auth #</FormLabel>
                          <FormControl>
                            <Input {...field} value={field.value ?? ""} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="referring_provider_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Referring Provider</FormLabel>
                          <FormControl>
                            <Input {...field} value={field.value ?? ""} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="referring_provider_npi"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Referring NPI</FormLabel>
                          <FormControl>
                            <Input {...field} value={field.value ?? ""} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                  <div className="space-y-4 pt-4 border-t md:col-span-2">
                     <p className="text-sm font-medium">Condition Related To:</p>
                      <FormField
                          control={form.control}
                          name="is_condition_related_to_employment"
                          render={({ field }) => (
                              <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                  <FormControl>
                                      <Checkbox
                                          checked={!!field.value}
                                          onCheckedChange={field.onChange}
                                      />
                                  </FormControl>
                                  <FormLabel>Employment</FormLabel>
                              </FormItem>
                          )}
                      />
                      <FormField
                          control={form.control}
                          name="is_condition_related_to_auto_accident"
                          render={({ field }) => (
                              <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                  <FormControl>
                                      <Checkbox
                                          checked={!!field.value}
                                          onCheckedChange={field.onChange}
                                      />
                                  </FormControl>
                                  <FormLabel>Auto Accident</FormLabel>
                              </FormItem>
                          )}
                      />
                      <FormField
                          control={form.control}
                          name="is_condition_related_to_other_accident"
                          render={({ field }) => (
                              <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                                  <FormControl>
                                      <Checkbox
                                          checked={!!field.value}
                                          onCheckedChange={field.onChange}
                                      />
                                  </FormControl>
                                  <FormLabel>Other Accident</FormLabel>
                              </FormItem>
                          )}
                      />
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          <Card>
            <CardHeader>
              <CardTitle>AI Co-Pilot Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <InfoItem
                label="Eligibility Status"
                value={<Badge>{claim.eligibility_status}</Badge>}
              />
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Compliance Flags
                </p>
                {claim.compliance_flags && claim.compliance_flags.length > 0 ? (
                  <ul className="list-disc pl-5 mt-1 space-y-1 text-sm">
                    {claim.compliance_flags.map((flag: any, index: number) => (
                      <li
                        key={index}
                        className={
                          flag.level === "error"
                            ? "text-destructive"
                            : "text-amber-600"
                        }
                      >
                        <span className="font-semibold">
                          [{flag.level?.toUpperCase()}]
                        </span>{" "}
                        {flag.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground mt-1">
                    No compliance issues found.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {claim.status === "denied" && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-destructive">
                  Denial Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoItem label="Denial Reason" value={claim.denial_reason} />
                <InfoItem
                  label="AI Root Cause Analysis"
                  value={claim.denial_root_cause}
                />
                <InfoItem
                  label="AI Recommended Action"
                  value={claim.denial_recommended_action}
                />
              </CardContent>
            </Card>
          )}

          <Card>
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
                    claim.service_lines.map((line: ServiceLine) => (
                      <TableRow key={line.id}>
                        <TableCell className="font-medium">
                          {line.cpt_code}
                        </TableCell>
                        <TableCell>{line.icd10_codes.join(", ")}</TableCell>
                        <TableCell>{line.diagnosis_pointer}</TableCell>
                        <TableCell>
                          {line.code_confidence_score
                            ? `${(line.code_confidence_score * 100).toFixed(
                                0
                              )}%`
                            : "N/A"}
                        </TableCell>
                        <TableCell className="text-right">
                          ${line.charge?.toFixed(2)}
                        </TableCell>
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
        </form>
      </Form>
    </div>
  );
}