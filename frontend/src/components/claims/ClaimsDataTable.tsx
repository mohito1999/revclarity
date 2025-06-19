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
import { Claim } from "@/lib/types";
import { FollowUpModal } from "./FollowUpModal";
import { Loader2 } from "lucide-react"; // --- NEW: Import a loading spinner icon ---

// --- The Main Table Component ---
export function ClaimsDataTable() {
  const router = useRouter();
  const [data, setData] = React.useState<Claim[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [followUpClaimId, setFollowUpClaimId] = React.useState<string | null>(null);
  
  // --- NEW: State to track which claim is being directly simulated ---
  const [simulatingClaimId, setSimulatingClaimId] = React.useState<string | null>(null);

  // --- Data Fetching ---
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
  
  // --- NEW: Handler for the direct "Simulate Outcome" button ---
  const handleDirectSimulate = async (claimId: string) => {
    setSimulatingClaimId(claimId);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
      await fetch(`${apiUrl}/claims/${claimId}/simulate-outcome`, { method: 'POST' });
      
      // Give the background task a moment to complete before refreshing the UI
      setTimeout(() => {
        fetchClaims();
        setSimulatingClaimId(null);
      }, 5000); // 5-second delay to simulate processing

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
      cell: ({ row }) => <div className="font-mono">{row.getValue("id").substring(0, 8)}...</div>,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const status = row.getValue("status") as string;
        let variant: "default" | "secondary" | "destructive" | "outline" = "secondary";
        if (status === "approved" || status === "paid") variant = "default";
        else if (status === "denied") variant = "destructive";
        else if (status === "draft") variant = "outline";
        
        return <Badge variant={variant} className="capitalize">{status}</Badge>;
      },
    },
    {
      accessorKey: "payer_name",
      header: "Payer",
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
    // --- MODIFIED: The Actions column now shows two buttons ---
    {
      id: "actions",
      header: () => <div className="text-right">Actions</div>,
      cell: ({ row }) => {
        const claim = row.original;
        const isSimulating = simulatingClaimId === claim.id;

        if (claim.status === "submitted") {
          return (
            <div className="flex justify-end gap-2">
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
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setFollowUpClaimId(claim.id);
                }}
                disabled={isSimulating || !!simulatingClaimId}
              >
                AI Follow Up
              </Button>
            </div>
          );
        }
        return null;
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

  if (loading) return <div>Loading claims...</div>;
  if (error) return <div className="text-red-500">Error: {error}</div>;

  return (
    <>
      <div className="rounded-md border">
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
                  className="cursor-pointer"
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
      
      <FollowUpModal
        claimId={followUpClaimId}
        onOpenChange={(open) => {
          if (!open) {
            setFollowUpClaimId(null);
          }
        }}
        onComplete={() => {
          setFollowUpClaimId(null);
          fetchClaims(); // Refresh the table data after simulation
        }}
      />
    </>
  );
}