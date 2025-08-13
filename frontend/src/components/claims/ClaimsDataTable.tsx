"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
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
import { Claim } from "@/lib/types"; // Make sure to update your Claim type
import { FollowUpModal } from "./FollowUpModal";
import { Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

// --- The Main Table Component ---
export function ClaimsDataTable() {
  const router = useRouter();
  const [data, setData] = React.useState<Claim[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [followUpClaimId, setFollowUpClaimId] = React.useState<string | null>(null);
  const [simulatingClaimId, setSimulatingClaimId] = React.useState<string | null>(null);

  const fetchClaims = React.useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await fetch(`${apiUrl}/claims`);
      if (!response.ok) {
        throw new Error(`Failed to fetch claims: ${response.statusText}`);
      }
      const claims: Claim[] = await response.json();
      setData(claims);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);
  
  // --- REFINED: Use polling instead of a fixed timeout for better UX ---
  const handleDirectSimulate = async (claimId: string) => {
    setSimulatingClaimId(claimId);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      await fetch(`${apiUrl}/claims/${claimId}/simulate-outcome`, { method: 'POST' });
      
      // Poll for status change
      const poll = setInterval(async () => {
        await fetchClaims(); // This will re-fetch all claims and update the table
      }, 2000); // Check every 2 seconds

      // Stop polling after 30 seconds or when status changes
      const timeout = setTimeout(() => {
        clearInterval(poll);
        setSimulatingClaimId(null);
      }, 30000);

      // Add a check inside the interval to clear it if status is no longer "submitted"
      const stopPollingCheck = setInterval(() => {
        const claim = data.find(c => c.id === claimId);
        if (claim && claim.status !== 'submitted') {
          clearInterval(poll);
          clearTimeout(timeout);
          clearInterval(stopPollingCheck);
          setSimulatingClaimId(null);
        }
      }, 500);

    } catch (err) {
      console.error("Direct simulation failed:", err);
      setSimulatingClaimId(null);
    }
  };

  // --- Column Definitions ---
  const columns: ColumnDef<Claim>[] = [
    {
      accessorKey: "id",
      header: "Claim ID",
      cell: ({ row }) => <div className="font-mono text-xs">{row.getValue("id").substring(0, 8)}...</div>,
    },
    // --- NEW: Patient Name Column ---
    {
      accessorKey: "patient",
      header: "Patient Name",
      cell: ({ row }) => {
        const patient = row.original.patient;
        const name = patient ? `${patient.first_name} ${patient.last_name}` : 'N/A';
        return <div className="font-medium">{name}</div>
      },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const status = row.getValue("status") as string;
        let variant: "default" | "secondary" | "destructive" | "outline" = "secondary";
        if (status === "approved" || status === "paid") variant = "default";
        else if (status === "denied") variant = "destructive";
        else if (status === "submitted") variant = "outline"; // Changed for better visibility
        
        return <Badge variant={variant} className="capitalize">{status.replace("_", " ")}</Badge>;
      },
    },
    {
      accessorKey: "payer_name",
      header: "Payer",
      cell: ({ row }) => row.getValue("payer_name") || "N/A",
    },
    {
      accessorKey: "total_charge_amount",
      header: () => <div className="text-right">Amount</div>,
      cell: ({ row }) => {
        const amount = parseFloat(row.getValue("total_charge_amount"));
        const formatted = new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
        }).format(amount || 0);
        return <div className="text-right font-medium">{formatted}</div>;
      },
    },
    {
      accessorKey: "date_of_service",
      header: "Date of Service",
      cell: ({ row }) => {
        const date = row.getValue("date_of_service");
        return date ? new Date(date as string).toLocaleDateString() : "N/A";
      },
    },
    {
      id: "actions",
      header: () => <div className="text-right">Actions</div>,
      cell: ({ row }) => {
        const claim = row.original;
        const isSimulating = simulatingClaimId === claim.id;
    
        // Actions for "Submitted" claims
        if (claim.status === "submitted") {
          return (
            <div className="flex justify-end gap-2">
              {/* Simulate Outcome Button */}
              <Button
                variant="secondary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDirectSimulate(claim.id);
                }}
                disabled={isSimulating || !!simulatingClaimId}
              >
                {isSimulating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Simulate Outcome"}
              </Button>
    
              {/* --- ADDED BACK: AI Follow Up Button --- */}
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation(); // Prevents the row's click event
                  setFollowUpClaimId(claim.id); // This opens the modal
                }}
                disabled={isSimulating || !!simulatingClaimId}
              >
                AI Follow Up
              </Button>
            </div>
          );
        }
    
        // Actions for "Denied" claims
        if (claim.status === 'denied') {
          return (
            <div className="flex justify-end gap-2">
              {/* Review Denial Button */}
              <Button 
                variant="secondary"
                size="sm"
                // The router.push is already on the row, but an explicit button can be good UX
                onClick={(e) => {
                  e.stopPropagation();
                  router.push(`/claim/${claim.id}`);
                }}
              >
                Review Denial
              </Button>
    
              {/* --- ADDED BACK: AI Follow Up Button --- */}
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setFollowUpClaimId(claim.id);
                }}
              >
                AI Follow Up
              </Button>
            </div>
          )
        }
    
        return null; // No actions for other statuses like 'draft', 'approved', etc.
      },
    },
  ];

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  });

  // --- REFINED: Better Loading and Error states ---
  if (loading) return <div className="flex items-center justify-center p-10"><Loader2 className="h-8 w-8 animate-spin text-gray-500" /> <span className="ml-2">Loading Claims...</span></div>;
  if (error) return (
      <Alert variant="destructive" className="m-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
      </Alert>
  );

  return (
    <>
      <div className="rounded-md border bg-white shadow-sm">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/claim/${row.original.id}`)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">No claims found.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* FollowUpModal seems to be for a different flow, leaving it as is */}
      <FollowUpModal
        claimId={followUpClaimId}
        onOpenChange={(open) => !open && setFollowUpClaimId(null)}
        onComplete={() => {
          setFollowUpClaimId(null);
          fetchClaims();
        }}
      />
    </>
  );
}