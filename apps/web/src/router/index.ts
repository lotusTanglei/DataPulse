import type { Pinia } from "pinia";
import {
  createRouter,
  createWebHistory,
  type Router,
  type RouterHistory,
} from "vue-router";

import LoginView from "../features/auth/LoginView.vue";
import SetupView from "../features/auth/SetupView.vue";
import DatasetListView from "../features/datasets/DatasetListView.vue";
import DatasourceDetailView from "../features/datasources/DatasourceDetailView.vue";
import DatasourceFormView from "../features/datasources/DatasourceFormView.vue";
import DatasourceListView from "../features/datasources/DatasourceListView.vue";
import HomeView from "../features/home/HomeView.vue";
import PlayerView from "../features/player/PlayerView.vue";
import ScreenEditorView from "../features/screens/ScreenEditorView.vue";
import ScreenListView from "../features/screens/ScreenListView.vue";
import { useAuthStore } from "../stores/auth";
import StudioShell from "../ui/StudioShell.vue";

interface StudioRouterOptions {
  pinia: Pinia;
  history?: RouterHistory;
}

export function createStudioRouter(options: StudioRouterOptions): Router {
  const router = createRouter({
    history: options.history ?? createWebHistory(),
    routes: [
      { path: "/", redirect: "/studio" },
      {
        path: "/studio/setup",
        name: "setup",
        component: SetupView,
        meta: { public: true, title: "初始化" },
      },
      {
        path: "/studio/login",
        name: "login",
        component: LoginView,
        meta: { public: true, title: "登录" },
      },
      {
        path: "/studio/screens/:id/preview",
        name: "screen-preview",
        component: PlayerView,
        props: { mode: "preview" },
        meta: { title: "大屏草稿预览" },
      },
      {
        path: "/play/:screenId",
        name: "screen-standalone",
        component: PlayerView,
        props: (route) => ({
          mode: "standalone",
          screenId: String(route.params.screenId),
        }),
        meta: { publicPlayer: true, title: "大屏播放" },
      },
      {
        path: "/studio",
        component: StudioShell,
        children: [
          { path: "", redirect: "/studio/datasources" },
          {
            path: "overview",
            name: "overview",
            component: HomeView,
            meta: {
              title: "概览",
              description: "查看工作区中的数据资产与最近活动。",
            },
          },
          {
            path: "datasources",
            name: "datasources",
            component: DatasourceListView,
            meta: {
              title: "数据源",
              description: "连接并管理用于分析的数据库。",
            },
          },
          {
            path: "datasources/new",
            name: "datasource-new",
            component: DatasourceFormView,
            meta: {
              title: "新建数据源",
              description: "配置一个新的数据库连接。",
            },
          },
          {
            path: "datasources/:id/edit",
            name: "datasource-edit",
            component: DatasourceFormView,
            meta: {
              title: "编辑数据源",
              description: "更新数据库连接配置。",
            },
          },
          {
            path: "datasources/:id",
            name: "datasource-detail",
            component: DatasourceDetailView,
            meta: {
              title: "数据源详情",
              description: "查看连接信息、浏览 Schema 并调试查询。",
            },
          },
          {
            path: "datasets",
            name: "datasets",
            component: DatasetListView,
            meta: {
              title: "数据集",
              description: "沉淀可复用的查询与字段定义。",
            },
          },
          {
            path: "datasets/:id",
            name: "dataset-detail",
            component: () =>
              import("../features/datasets/DatasetDetailView.vue"),
            meta: {
              title: "数据集详情",
              description: "编辑查询定义、参数并预览结果。",
            },
          },
          {
            path: "screens",
            name: "screens",
            component: ScreenListView,
            meta: {
              title: "大屏",
              description: "创建、调试并发布可嵌入的数据大屏。",
            },
          },
          {
            path: "screens/:id/edit",
            name: "screen-edit",
            component: ScreenEditorView,
            meta: {
              title: "大屏编辑器",
              description: "编辑大屏草稿并预览最终效果。",
            },
          },
          {
            path: "settings",
            name: "settings",
            component: HomeView,
            meta: {
              title: "系统设置",
              description: "管理管理员账号与系统运行配置。",
            },
          },
        ],
      },
    ],
  });

  router.beforeEach(async (to) => {
    if (to.meta.publicPlayer === true) {
      return true;
    }
    const auth = useAuthStore(options.pinia);
    const state = await auth.resolve();
    if (state.status === "setup-required") {
      return to.name === "setup" ? true : { name: "setup" };
    }
    if (state.status === "anonymous") {
      return to.name === "login" ? true : { name: "login" };
    }
    if (
      state.status === "authenticated" &&
      (to.name === "setup" || to.name === "login")
    ) {
      return { name: "datasources" };
    }
    return true;
  });

  return router;
}
