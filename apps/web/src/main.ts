import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { AUTH_EXPIRED_EVENT } from "./lib/api";
import { createStudioRouter } from "./router";
import { useAuthStore } from "./stores/auth";
import "./styles/base.css";

const pinia = createPinia();
const router = createStudioRouter({ pinia });
const auth = useAuthStore(pinia);

window.addEventListener(AUTH_EXPIRED_EVENT, () => {
  auth.expire();
  if (router.currentRoute.value.path !== "/studio/login") {
    void router.replace("/studio/login");
  }
});

createApp(App).use(pinia).use(router).mount("#app");
