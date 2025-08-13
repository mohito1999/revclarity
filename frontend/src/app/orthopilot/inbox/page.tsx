"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Upload, FileText, Loader2, AlertCircle, RefreshCw } from "lucide-react";

// --- Types ---
type DocumentStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "ERROR";
type DocumentClassification = "UNCLASSIFIED" | "REFERRAL_FAX" | "DICTATED_NOTE" | "MODMED_NOTE" | "NON_REFERRAL";

interface MeriplexDocument {
  id: string;
  file_name: string;
  status: DocumentStatus;
  classification: DocumentClassification;
  created_at: string;
  processing_error: string | null;
}

// --- Main Component ---
export default function DocumentInboxPage() {
  const [documents, setDocuments] = React.useState<MeriplexDocument[]>([]);
  const [initialLoading, setInitialLoading] = React.useState(true); // For the first load
  const [polling, setPolling] = React.useState(false); // For background refreshes
  const [error, setError] = React.useState<string | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // --- THE FIX: Modified fetchDocuments to handle background refreshes silently ---
  const fetchDocuments = React.useCallback(async (isSilent = false) => {
    if (!isSilent) {
      setInitialLoading(true);
    } else {
      setPolling(true); // Indicate a background poll is happening
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/orthopilot/documents`);
      if (!response.ok) throw new Error("Failed to fetch documents.");
      const data = await response.json();
      setDocuments(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      if (!isSilent) setInitialLoading(false);
      setPolling(false); // Always turn off polling indicator
    }
  }, []);

  React.useEffect(() => {
    fetchDocuments(false); // Initial, non-silent fetch
    const interval = setInterval(() => {
      fetchDocuments(true); // Subsequent silent fetches
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchDocuments]);
  // --- END FIX ---

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    Array.from(files).forEach(file => formData.append("files", file));

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/orthopilot/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Upload failed");
      }
      // Immediately trigger a silent refresh after upload
      await fetchDocuments(true);
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };
  
  const columns: ColumnDef<MeriplexDocument>[] = [
    { accessorKey: "file_name", header: "File Name" },
    { 
      accessorKey: "status", 
      header: "Processing Status",
      cell: ({ row }) => {
        const status = row.original.status;
        let variant: "default" | "secondary" | "destructive" | "outline" = "secondary";
        if (status === "COMPLETED") variant = "default";
        if (status === "ERROR") variant = "destructive";
        if (status === "PROCESSING") variant = "outline";
        return <Badge variant={variant} className="capitalize">{status}</Badge>;
      }
    },
    { 
      accessorKey: "classification", 
      header: "AI Classification",
      cell: ({ row }) => {
        const classification = row.original.classification;
        return <Badge variant="secondary" className="capitalize">{classification.replace(/_/g, ' ')}</Badge>;
      }
    },
    { 
      accessorKey: "created_at", 
      header: "Upload Time",
      cell: ({ row }) => new Date(row.original.created_at).toLocaleString()
    },
  ];

  const table = useReactTable({
    data: documents,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Document Inbox</h2>
          <p className="text-muted-foreground">Upload and track documents for AI processing.</p>
        </div>
        <div className="flex items-center gap-2">
            {/* --- THE FIX: Refresh button now shows polling state --- */}
            <Button variant="outline" size="sm" onClick={() => fetchDocuments(false)} disabled={initialLoading || polling}>
                <RefreshCw className={`h-4 w-4 ${polling || initialLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
            Upload Documents
            </Button>
            <Input
            type="file"
            ref={fileInputRef}
            onChange={handleUpload}
            className="hidden"
            multiple
            accept=".pdf"
            />
        </div>
      </div>

      {uploadError && (
         <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Upload Failed</AlertTitle>
            <AlertDescription>{uploadError}</AlertDescription>
        </Alert>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {/* --- THE FIX: Only show full-table loading on initial load --- */}
            {initialLoading ? (
                <TableRow><TableCell colSpan={columns.length} className="h-24 text-center">Loading documents...</TableCell></TableRow>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No documents found. Upload some to get started.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}