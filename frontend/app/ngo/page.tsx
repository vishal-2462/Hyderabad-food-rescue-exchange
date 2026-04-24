import { NgoWorkbench } from "@/app/_components/ngo-workbench";
import { getDashboardBundle } from "@/app/_lib/api";
import { requireAuth } from "@/app/_lib/auth-server";

export default async function NgoPage() {
  const currentUser = await requireAuth("ngo");

  const { ngos, requests, donations } = await getDashboardBundle();
  const scopedNgos = ngos.filter((ngo) => ngo.id === currentUser.profile_id);
  const scopedRequests = requests.filter((request) => request.ngo_id === currentUser.profile_id);
  return <NgoWorkbench ngos={scopedNgos} requests={scopedRequests} donations={donations} />;
}
