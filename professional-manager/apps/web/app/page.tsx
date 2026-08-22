import { Dashboard } from "@/components/dashboard";

async function getHealth() {
  const apiUrl = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  try {
    const response = await fetch(`${apiUrl}/health`, { cache: "no-store", signal: AbortSignal.timeout(1500) });
    return response.ok ? await response.json() as { status: string; version: string } : null;
  } catch {
    return null;
  }
}

export default async function Home() {
  return <Dashboard health={await getHealth()} />;
}

