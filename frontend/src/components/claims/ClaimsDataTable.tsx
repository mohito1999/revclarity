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
import { FollowUpModal } from "./FollowUpModal"; // <-- Import the new modal

// --- The Main Table Component ---
export function ClaimsDataTable() {
  const router = useRouter();
  const [data, setData] = React.useState<Claim[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [followUpClaimId, setFollowUpClaimId] = React.useState<string | null>(null);

  // --- Data Fetching ---
  const fetchClaims = React.useCallback(async () => {
    // No need to set loading to true on auto-refresh
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
        }).format(amount);
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
    // --- THIS IS THE NEW ACTIONS COLUMN ---
    {
      id: "actions",
      header: () => <div className="text-right">Actions</div>,
      cell: ({ row }) => {
        const claim = row.original;
        if (claim.status === "submitted") {
          return (
            <div className="text-right">
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation(); // Prevent row click from firing
                  setFollowUpClaimId(claim.id); // This opens the modal
                }}
              >
                Follow Up
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
      
      {/* --- RENDER THE MODAL HERE --- */}
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