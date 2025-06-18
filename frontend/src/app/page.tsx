import { ClaimsDataTable } from "@/components/claims/ClaimsDataTable";

export default function DashboardPage() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Claims Dashboard</h1>
      </div>
      <p className="text-muted-foreground">
        An overview of all processed claims.
      </p>
      
      {/* --- Render the Data Table Component Here --- */}
      <ClaimsDataTable />
    </div>
  );
}