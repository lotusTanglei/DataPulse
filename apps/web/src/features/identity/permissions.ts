import { computed } from "vue";
import { useAuthStore } from "../../stores/auth";
import { getResourceAccess, type ResourceType } from "./api";

/** UI affordances only; every mutation is still authorized by the server. */
export function useStudioPermissions() {
  const auth = useAuthStore();
  const isAdmin = computed(() => auth.state.status === "authenticated" && auth.state.role === "admin");
  const canCreate = computed(() => auth.state.status === "authenticated" && (auth.state.role === "admin" || auth.state.role === "editor"));

  async function canWriteResource(kind: ResourceType, id: string): Promise<boolean> {
    if (isAdmin.value) return true;
    if (!canCreate.value) return false;
    const access = await getResourceAccess(kind, id).catch(() => null);
    return access?.write === true;
  }

  return { isAdmin, canCreate, canWriteResource };
}
