"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
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
import { Upload } from "lucide-react";

const uploadSchema = z.object({
  document_purpose: z.string().min(1, "Please select a document type."),
  file: z
    .custom<FileList>()
    .refine((files) => files?.length === 1, "A single file is required."),
});

interface DocumentUploaderProps {
  patientId: string;
  onUploadSuccess: () => void; // A function to call to refresh the page
}

export function DocumentUploader({ patientId, onUploadSuccess }: DocumentUploaderProps) {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const form = useForm<z.infer<typeof uploadSchema>>({
    resolver: zodResolver(uploadSchema),
  });

  async function onSubmit(values: z.infer<typeof uploadSchema>) {
    setIsSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("document_purpose", values.document_purpose);
    formData.append("file", values.file[0]);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/patients/${patientId}/documents`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("File upload failed.");
      }

      // Success! Reset form and trigger refresh
      form.reset();
      onUploadSuccess();
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 rounded-lg border bg-card p-4 text-card-foreground shadow-sm">
        <FormField
          control={form.control}
          name="document_purpose"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Document Type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select the type of document" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="POLICY_DOC">Policy / Insurance Card</SelectItem>
                  <SelectItem value="PATIENT_INTAKE">Patient Intake Form</SelectItem>
                  <SelectItem value="MEDICAL_HISTORY">Medical History</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="file"
          render={({ field }) => (
            <FormItem>
              <FormLabel>File</FormLabel>
              <FormControl>
                <Input type="file" onChange={(e) => field.onChange(e.target.files)} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm font-medium text-destructive">{error}</p>}
        <Button type="submit" disabled={isSubmitting} className="w-full">
          <Upload className="mr-2 h-4 w-4" />
          {isSubmitting ? "Uploading..." : "Upload Document"}
        </Button>
      </form>
    </Form>
  );
}