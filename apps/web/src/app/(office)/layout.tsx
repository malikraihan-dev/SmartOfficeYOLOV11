import { requireAdmin } from "@/lib/session";
import { OfficeProvider } from "@/components/office-provider";
import { OfficeShell } from "@/components/office-shell";

export default async function OfficeLayout({ children }: { children: React.ReactNode }) {
  const session = await requireAdmin();
  return <OfficeProvider><OfficeShell username={session.user!.username}>{children}</OfficeShell></OfficeProvider>;
}
