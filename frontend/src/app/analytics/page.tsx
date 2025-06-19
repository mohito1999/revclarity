"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DollarSign, FileText, CheckCircle2, XCircle, Loader } from "lucide-react";

interface AnalyticsSummary {
  total_claims: number;
  status_counts: { [key: string]: number };
  total_charge_amount: number;
  total_paid_amount: number;
  total_patient_responsibility: number;
}

const StatCard = ({ title, value, icon, description }: { title: string, value: string, icon: React.ReactNode, description: string }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </CardContent>
  </Card>
);

export default function AnalyticsPage() {
  const [data, setData] = React.useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    async function fetchAnalytics() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
        const response = await fetch(`${apiUrl}/analytics/summary`);
        if (!response.ok) throw new Error("Failed to fetch analytics data.");
        const summary: AnalyticsSummary = await response.json();
        setData(summary);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, []);

  if (loading) return <div>Loading analytics...</div>;
  if (error) return <div className="text-red-500">Error: {error}</div>;
  if (!data) return <div>No analytics data available.</div>;

  const formatCurrency = (amount: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-4">
      <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatCard title="Total Claims" value={data.total_claims.toString()} icon={<FileText className="h-4 w-4 text-muted-foreground" />} description="All claims created in the system" />
        <StatCard title="Approved" value={(data.status_counts.approved || 0).toString()} icon={<CheckCircle2 className="h-4 w-4 text-green-500" />} description="Claims approved by payers" />
        <StatCard title="Denied" value={(data.status_counts.denied || 0).toString()} icon={<XCircle className="h-4 w-4 text-destructive" />} description="Claims denied by payers" />
        <StatCard title="Total Billed" value={formatCurrency(data.total_charge_amount)} icon={<DollarSign className="h-4 w-4 text-muted-foreground" />} description="Total amount billed to payers" />
        <StatCard title="Total Collected" value={formatCurrency(data.total_paid_amount)} icon={<DollarSign className="h-4 w-4 text-green-500" />} description="Total amount paid by payers" />
        <StatCard title="In Process" value={(data.status_counts.processing || 0).toString()} icon={<Loader className="h-4 w-4 text-muted-foreground animate-spin" />} description="Claims currently being processed by AI" />
      </div>
    </div>
  );
}