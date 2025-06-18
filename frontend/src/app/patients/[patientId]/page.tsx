"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Upload } from "lucide-react";
import { DocumentUploader } from "@/components/patients/DocumentUploader";

// Define our types for this page
interface Document {
  id: string;
  file_name: string;
  document_purpose: string | null;
  uploaded_at: string;
}

interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  documents: Document[];
}

const InfoItem = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div>
    <p className="text-sm font-medium text-muted-foreground">{label}</p>
    <p className="text-base font-semibold">{value || "N/A"}</p>
  </div>
);

export default function PatientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const patientId = params.patientId as string;

  const [patient, setPatient] = React.useState<Patient | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const handleUploadSuccess = () => {
    // A simple way to refresh data is to refetch it.
    // For a better UX, we could just update the state, but this is robust.
    setLoading(true);
    fetchPatientDetails();
  };

  // Function to fetch patient data
  const fetchPatientDetails = React.useCallback(async () => {
    if (!patientId) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/patients/${patientId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch patient details.");
      }
      const data: Patient = await response.json();
      setPatient(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  React.useEffect(() => {
    fetchPatientDetails();
  }, [fetchPatientDetails]);
  
  // We'll create the file upload logic in the next step

  if (loading) return <div className="p-8">Loading patient details...</div>;
  if (error) return <div className="p-8 text-red-500">Error: {error}</div>;
  if (!patient) return <div className="p-8">Patient not found.</div>;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{patient.first_name} {patient.last_name}</h1>
        <p className="text-muted-foreground font-mono text-sm">{patient.id}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Column for Details */}
        <div className="md:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Patient Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <InfoItem label="First Name" value={patient.first_name} />
              <InfoItem label="Last Name" value={patient.last_name} />
              <InfoItem label="Date of Birth" value={new Date(patient.date_of_birth).toLocaleDateString()} />
            </CardContent>
          </Card>
        </div>

        {/* Right Column for Documents */}
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Patient Documents</CardTitle>
            </CardHeader>
            <CardContent>
              {patient.documents.length > 0 ? (
                <ul className="space-y-2">
                  {patient.documents.map((doc) => (
                    <li key={doc.id} className="flex items-center justify-between rounded-md border p-3">
                       <div className="flex items-center gap-3">
                         <FileText className="h-5 w-5 text-muted-foreground" />
                         <div>
                            <p className="font-medium">{doc.file_name}</p>
                            <p className="text-sm text-muted-foreground">Uploaded on {new Date(doc.uploaded_at).toLocaleDateString()}</p>
                         </div>
                       </div>
                       <Badge variant="outline">{doc.document_purpose || "General"}</Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No documents uploaded for this patient yet.</p>
              )}

              {/* We will add the upload form here */}
              <div className="mt-6">
                <h3 className="font-semibold mb-2">Upload New Document</h3>
                <DocumentUploader patientId={patient.id} onUploadSuccess={handleUploadSuccess} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}