"use client";

import { AddPatientDialog } from "@/components/patients/AddPatientDialog";
import { PatientsDataTable } from "@/components/patients/PatientsDataTable"; // <-- Import the new table

export default function PatientsPage() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Patients</h1>
        <AddPatientDialog />
      </div>
      <p className="text-muted-foreground">
        Manage patient records and associated documents.
      </p>

      {/* --- Render the Patient Data Table Here --- */}
      <PatientsDataTable />
    </div>
  );
}