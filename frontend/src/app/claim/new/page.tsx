"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload } from "lucide-react";

// Define the type for a patient (for our dropdown)
interface Patient {
  id: string;
  first_name: string;
  last_name: string;
}

// Define the schema for our form validation
const formSchema = z.object({
  patientId: z.string().uuid({ message: "Please select a patient." }),
  files: z
    .custom<FileList>()
    .refine((files) => files?.length > 0, "At least one file is required.")
    .refine(
      (files) => Array.from(files).every((file) => file.size < 5 * 1024 * 1024), // 5MB limit
      "Each file must be less than 5MB."
    ),
});

export default function NewClaimPage() {
  const router = useRouter();
  const [patients, setPatients] = React.useState<Patient[]>([]);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch the list of patients for the dropdown
  React.useEffect(() => {
    async function fetchPatients() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/patients`);
        if (!response.ok) throw new Error("Failed to fetch patients.");
        const data = await response.json();
        setPatients(data);
      } catch (err) {
        setError("Could not load patient list. Please try again later.");
      }
    }
    fetchPatients();
  }, []);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("patient_id", values.patientId);
    Array.from(values.files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/claims/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create claim.");
      }
      
      const newClaim = await response.json();
      // On success, redirect to the new claim's workspace
      router.push(`/claim/${newClaim.id}`);

    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4">
      <h1 className="text-2xl font-bold tracking-tight">Create New Claim</h1>
      <Card>
        <CardHeader>
          <CardTitle>Claim Submission</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
              <FormField
                control={form.control}
                name="patientId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Patient</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a patient to create a claim for" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {patients.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.first_name} {p.last_name} (ID: ...{p.id.slice(-6)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Select the patient this claim belongs to.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="files"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Claim Documents</FormLabel>
                    <FormControl>
                      <Input
                        type="file"
                        multiple
                        onChange={(e) => field.onChange(e.target.files)}
                      />
                    </FormControl>
                    <FormDescription>
                      Upload all relevant documents (Intake, Encounter Note, etc.). The AI will synthesize them.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              {error && <p className="text-sm font-medium text-destructive">{error}</p>}
              
              <Button type="submit" disabled={isSubmitting}>
                <Upload className="mr-2 h-4 w-4" />
                {isSubmitting ? "Processing..." : "Create Claim & Process with AI"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}