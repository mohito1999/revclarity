"use client";

import * as React from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  SortingState,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Download, File, Loader2, ArrowUpDown } from "lucide-react";

// --- Types ---
// This interface now matches the comprehensive backend extraction
interface ExtractedReferralData {
  patient_name: string;
  patient_dob: string;
  patient_phone: string;
  patient_primary_insurance: string;
  patient_policy_id: string;
  reason_for_referral: string;
  referring_physician_name: string;
  referring_physician_phone: string;
  referral_date: string;
}

interface ReferralDocument {
  id: string;
  file_name: string;
  extracted_data: ExtractedReferralData | null;
}

// --- Main Component ---
export default function ReferralTaskListPage() {
  const [referrals, setReferrals] = React.useState<ReferralDocument[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: "referral_date", desc: true }, // Default sort by newest referral
  ]);

  React.useEffect(() => {
    async function fetchReferrals() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/orthopilot/documents?classification=REFERRAL_FAX`);
        if (!response.ok) throw new Error("Failed to fetch referral documents.");
        const data = await response.json();
        setReferrals(data);
      } catch (err: any) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchReferrals();
  }, []);

  // --- THE FIX: Expanded and reorganized columns for better utility ---
  const columns: ColumnDef<ReferralDocument>[] = [
    {
      accessorKey: "referral_date",
      header: ({ column }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Referral Date <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => row.original.extracted_data?.referral_date || "N/A",
    },
    {
      id: "patient_demographics",
      header: "Patient Demographics",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.extracted_data?.patient_name || "N/A"}</div>
          <div className="text-xs text-muted-foreground">{row.original.extracted_data?.patient_dob || "N/A"}</div>
          <div className="text-xs text-muted-foreground">{row.original.extracted_data?.patient_phone || "N/A"}</div>
        </div>
      ),
    },
    {
      id: "insurance",
      header: "Insurance",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.extracted_data?.patient_primary_insurance || "N/A"}</div>
          <div className="text-xs text-muted-foreground font-mono">{row.original.extracted_data?.patient_policy_id || "N/A"}</div>
        </div>
      ),
    },
    {
      accessorKey: "extracted_data.reason_for_referral",
      header: "Reason for Referral",
      cell: ({ row }) => <div className="max-w-xs whitespace-normal">{row.original.extracted_data?.reason_for_referral || "N/A"}</div>,
    },
    {
      id: "referring_physician",
      header: "Referring Provider",
       cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.extracted_data?.referring_physician_name || "N/A"}</div>
          <div className="text-xs text-muted-foreground">{row.original.extracted_data?.referring_physician_phone || "N/A"}</div>
        </div>
      ),
    },
    {
      id: "actions",
      header: "Original Fax",
      cell: ({ row }) => {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const downloadUrl = `${apiUrl}/orthopilot/documents/${row.original.id}/download`;
        return (
          <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className="block w-full text-center">
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              View PDF
            </Button>
          </a>
        );
      },
    },
  ];

  const table = useReactTable({
    data: referrals,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Referral Task List</h2>
          <p className="text-muted-foreground">Actionable list generated from incoming referral faxes.</p>
        </div>
        <Button disabled>
          <Download className="mr-2 h-4 w-4" />
          Export to Excel
        </Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="whitespace-nowrap">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={columns.length} className="h-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin" /></TableCell></TableRow>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="align-top py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No processed referrals found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}