<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError } from "../../lib/api";
import FormField from "../../ui/FormField.vue";
import InlineNotice from "../../ui/InlineNotice.vue";
import { createDatasource, getDatasource, updateDatasource } from "./api";
import type {
  ConnectorType,
  Datasource,
  DatasourceConfig,
  MySQLConfig,
  PostgreSQLConfig,
  SQLiteConfig,
  HttpApiConfig,
} from "./types";

interface SQLiteForm {
  type: "sqlite";
  name: string;
  path: string;
}

interface PostgreSQLForm {
  type: "postgresql";
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode: PostgreSQLConfig["ssl_mode"];
  clear_password: boolean;
}

interface MySQLForm {
  type: "mysql";
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode: MySQLConfig["ssl_mode"];
  clear_password: boolean;
}

interface HttpApiForm {
  type: "http_api";
  name: string;
  base_url: string;
  auth_type: HttpApiConfig["auth_type"];
  api_key_header: string;
  username: string;
  password: string;
  clear_password: boolean;
}

type DatasourceForm = SQLiteForm | PostgreSQLForm | MySQLForm | HttpApiForm;

const route = useRoute();
const router = useRouter();
const isEdit = computed(() => route.name === "datasource-edit");
const datasourceId = computed(() => String(route.params.id ?? ""));
const loading = ref(isEdit.value);
const submitting = ref(false);
const notice = ref("");
const requestId = ref("");
const clientFields = ref<Record<string, string>>({});
const serverFields = ref<Record<string, string>>({});
const model = ref<DatasourceForm>(blankForm("sqlite"));

const connectorType = computed<ConnectorType>({
  get: () => model.value.type,
  set: (type) => {
    model.value = blankForm(type, model.value.name);
    clientFields.value = {};
    serverFields.value = {};
  },
});

function blankForm(type: ConnectorType, name = ""): DatasourceForm {
  if (type === "sqlite") {
    return { type, name, path: "" };
  }
  if (type === "postgresql") {
    return {
      type,
      name,
      host: "",
      port: 5432,
      database: "",
      username: "",
      password: "",
      ssl_mode: "prefer",
      clear_password: false,
    };
  }
  if (type === "http_api") {
    return {
      type,
      name,
      base_url: "",
      auth_type: "none",
      api_key_header: "X-API-Key",
      username: "",
      password: "",
      clear_password: false,
    };
  }
  return {
    type,
    name,
    host: "",
    port: 3306,
    database: "",
    username: "",
    password: "",
    ssl_mode: "preferred",
    clear_password: false,
  };
}

function formFromDatasource(datasource: Datasource): DatasourceForm {
  if (datasource.config.type === "sqlite") {
    return {
      type: "sqlite",
      name: datasource.name,
      path: datasource.config.path,
    };
  }
  if (datasource.config.type === "http_api") {
    return {
      ...datasource.config,
      name: datasource.name,
      username: datasource.config.username ?? "",
      password: "",
      clear_password: false,
    };
  }
  return {
    ...datasource.config,
    name: datasource.name,
    password: "",
    clear_password: false,
  };
}

function fieldError(name: string): string | undefined {
  return clientFields.value[name] ?? serverFields.value[name];
}

function validate(): boolean {
  const errors: Record<string, string> = {};
  const current = model.value;
  if (current.name.trim() === "") {
    errors.name = "请输入数据源名称";
  }
  if (current.type === "sqlite") {
    const path = current.path.trim();
    if (/^(?:\/|[A-Za-z]:[\\/])/.test(path) || path.includes("\\")) {
      errors.path = "请输入 sources 目录内的相对路径";
    } else if (path.split("/").includes("..")) {
      errors.path = "路径不能包含上级目录";
    } else if (path === "" || path === ".") {
      errors.path = "请输入 SQLite 文件路径";
    }
  } else if (current.type === "http_api") {
    if (current.base_url.trim() === "") {
      errors.base_url = "请输入 API 基础地址";
    } else {
      try {
        const parsed = new URL(current.base_url.trim());
        if (!['http:', 'https:'].includes(parsed.protocol)) {
          errors.base_url = "仅支持 HTTP 或 HTTPS 地址";
        }
      } catch {
        errors.base_url = "请输入有效的 API 地址";
      }
    }
    if (current.auth_type === "api_key" && current.api_key_header.trim() === "") {
      errors.api_key_header = "请输入 API Key 请求头名称";
    }
    if (current.auth_type === "basic" && current.username.trim() === "") {
      errors.username = "Basic 认证需要用户名";
    }
    if (isEdit.value && current.password !== "" && current.clear_password) {
      errors.password = "新凭据与清除凭据不能同时设置";
      errors.clear_password = "新凭据与清除凭据不能同时设置";
    }
  } else {
    if (current.host.trim() === "") {
      errors.host = "请输入主机地址";
    }
    if (
      !Number.isInteger(Number(current.port)) ||
      Number(current.port) < 1 ||
      Number(current.port) > 65535
    ) {
      errors.port = "端口必须在 1 到 65535 之间";
    }
    if (current.database.trim() === "") {
      errors.database = "请输入数据库名称";
    }
    if (current.username.trim() === "") {
      errors.username = "请输入用户名";
    }
    if (isEdit.value && current.password !== "" && current.clear_password) {
      errors.password = "新密码与清除密码不能同时设置";
      errors.clear_password = "新密码与清除密码不能同时设置";
    }
  }
  clientFields.value = errors;
  return Object.keys(errors).length === 0;
}

function configFromForm(current: DatasourceForm): DatasourceConfig {
  if (current.type === "sqlite") {
    const config: SQLiteConfig = {
      type: "sqlite",
      path: current.path.trim(),
    };
    return config;
  }
  if (current.type === "postgresql") {
    const config: PostgreSQLConfig = {
      type: "postgresql",
      host: current.host.trim(),
      port: Number(current.port),
      database: current.database.trim(),
      username: current.username.trim(),
      ssl_mode: current.ssl_mode,
    };
    return config;
  }
  if (current.type === "http_api") {
    const config: HttpApiConfig = {
      type: "http_api",
      base_url: current.base_url.trim(),
      auth_type: current.auth_type,
      api_key_header: current.api_key_header.trim() || "X-API-Key",
      username: current.auth_type === "basic" ? current.username.trim() : null,
    };
    return config;
  }
  const config: MySQLConfig = {
    type: "mysql",
    host: current.host.trim(),
    port: Number(current.port),
    database: current.database.trim(),
    username: current.username.trim(),
    ssl_mode: current.ssl_mode,
  };
  return config;
}

function mapServerFields(error: ApiError): Record<string, string> {
  return Object.fromEntries(
    error.fieldErrors.map((item) => {
      const segments = item.field.split(".");
      return [segments.at(-1) ?? item.field, item.message];
    }),
  );
}

async function loadDatasource(): Promise<void> {
  if (!isEdit.value) {
    return;
  }
  loading.value = true;
  try {
    model.value = formFromDatasource(await getDatasource(datasourceId.value));
  } catch (reason) {
    if (reason instanceof ApiError) {
      notice.value = reason.message;
      requestId.value = reason.requestId;
    } else {
      notice.value = "暂时无法加载数据源。";
    }
  } finally {
    loading.value = false;
  }
}

async function submit(): Promise<void> {
  notice.value = "";
  requestId.value = "";
  serverFields.value = {};
  if (!validate()) {
    return;
  }
  submitting.value = true;
  const current = model.value;
  const config = configFromForm(current);
  try {
    let saved: Datasource;
    if (isEdit.value) {
      saved = await updateDatasource(datasourceId.value, {
        name: current.name.trim(),
        config,
        ...(current.type !== "sqlite" && current.password !== ""
          ? { password: current.password }
          : {}),
        ...(current.type !== "sqlite" && current.clear_password
          ? { clear_password: true }
          : {}),
      });
    } else {
      saved = await createDatasource({
        name: current.name.trim(),
        config,
        ...(current.type !== "sqlite" && current.password !== ""
          ? { password: current.password }
          : {}),
      });
    }
    await router.replace(`/studio/datasources/${saved.id}`);
  } catch (reason) {
    if (reason instanceof ApiError) {
      notice.value = reason.message;
      requestId.value = reason.requestId;
      serverFields.value = mapServerFields(reason);
    } else {
      notice.value = "保存失败，请稍后重试。";
    }
  } finally {
    submitting.value = false;
  }
}

onMounted(loadDatasource);
</script>

<template>
  <section class="page-column datasource-form-page" aria-labelledby="datasource-form-title">
    <div class="page-heading-row">
      <div>
        <p class="page-eyebrow">Datasource</p>
        <h1 id="datasource-form-title">{{ isEdit ? "编辑数据源" : "新建数据源" }}</h1>
        <p class="page-description">
          {{ isEdit ? "更新连接配置；密码不会回显。" : "添加一个可用于分析的数据连接。" }}
        </p>
      </div>
      <RouterLink class="secondary-button" to="/studio/datasources">返回列表</RouterLink>
    </div>

    <p v-if="loading" class="loading-copy" role="status">正在加载连接配置…</p>

    <template v-else>
      <InlineNotice v-if="notice" tone="error">
        <p>{{ notice }}</p>
        <code v-if="requestId">{{ requestId }}</code>
      </InlineNotice>

      <form class="datasource-form" autocomplete="off" @submit.prevent="submit">
        <div class="form-section">
          <div class="form-section__heading">
            <h2>基本信息</h2>
            <p>名称仅用于 DataPulse 工作区内识别。</p>
          </div>
          <div class="form-grid">
            <FormField
              label="数据源名称"
              name="name"
              :error="fieldError('name')"
              required
              data-field="name"
            >
              <input id="name" v-model="model.name" name="name" autocomplete="off" />
            </FormField>
            <FormField label="连接器" name="connectorType" required>
              <select id="connectorType" v-model="connectorType" name="connectorType">
                <option value="sqlite">SQLite</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL / MariaDB</option>
                <option value="http_api">HTTP API</option>
              </select>
            </FormField>
          </div>
        </div>

        <div class="form-section">
          <div class="form-section__heading">
            <h2>连接配置</h2>
            <p>只保存必要信息，地址不会包含密码。</p>
          </div>

          <div v-if="model.type === 'sqlite'" class="form-grid form-grid--single">
            <FormField
              label="相对路径"
              name="path"
              hint="相对于 sources 目录，例如 sales/warehouse.db"
              :error="fieldError('path')"
              required
              data-field="path"
            >
              <input
                id="path"
                v-model="model.path"
                name="path"
                placeholder="sales.db"
                autocomplete="off"
              />
            </FormField>
          </div>

          <div v-else-if="model.type === 'http_api'" class="form-grid">
            <FormField
              label="API 基础地址"
              name="base_url"
              hint="例如 https://api.example.com/v1"
              :error="fieldError('base_url')"
              required
              data-field="base_url"
            >
              <input
                id="base_url"
                v-model="model.base_url"
                name="base_url"
                type="url"
                autocomplete="off"
                placeholder="https://api.example.com/v1"
              />
            </FormField>
            <FormField label="认证方式" name="auth_type" required>
              <select id="auth_type" v-model="model.auth_type" name="auth_type">
                <option value="none">无认证</option>
                <option value="bearer">Bearer Token</option>
                <option value="api_key">API Key</option>
                <option value="basic">Basic Auth</option>
              </select>
            </FormField>
            <FormField
              v-if="model.auth_type === 'api_key'"
              label="API Key 请求头"
              name="api_key_header"
              :error="fieldError('api_key_header')"
              required
            >
              <input
                id="api_key_header"
                v-model="model.api_key_header"
                name="api_key_header"
                autocomplete="off"
                placeholder="X-API-Key"
              />
            </FormField>
            <FormField
              v-if="model.auth_type === 'basic'"
              label="Basic 用户名"
              name="username"
              :error="fieldError('username')"
              required
            >
              <input
                id="username"
                v-model="model.username"
                name="username"
                autocomplete="new-password"
              />
            </FormField>
            <FormField
              v-if="model.auth_type !== 'none'"
              label="Token / 密码"
              name="password"
              :hint="isEdit ? '留空则保留现有凭据' : '凭据只会在服务端加密保存'"
              :error="fieldError('password')"
            >
              <input
                id="password"
                v-model="model.password"
                name="password"
                type="password"
                autocomplete="new-password"
              />
            </FormField>
            <label v-if="isEdit && model.auth_type !== 'none'" class="checkbox-field">
              <input v-model="model.clear_password" type="checkbox" name="clear_password" />
              <span><strong>清除已保存凭据</strong></span>
            </label>
          </div>

          <div v-else class="form-grid">
            <FormField
              label="主机"
              name="host"
              :error="fieldError('host')"
              required
              data-field="host"
            >
              <input id="host" v-model="model.host" name="host" autocomplete="off" />
            </FormField>
            <FormField
              label="端口"
              name="port"
              :error="fieldError('port')"
              required
              data-field="port"
            >
              <input
                id="port"
                v-model.number="model.port"
                name="port"
                type="number"
                min="1"
                max="65535"
              />
            </FormField>
            <FormField
              label="数据库"
              name="database"
              :error="fieldError('database')"
              required
              data-field="database"
            >
              <input
                id="database"
                v-model="model.database"
                name="database"
                autocomplete="off"
              />
            </FormField>
            <FormField
              label="用户名"
              name="username"
              :error="fieldError('username')"
              required
              data-field="username"
            >
              <input
                id="username"
                v-model="model.username"
                name="username"
                autocomplete="new-password"
              />
            </FormField>
            <FormField
              label="密码"
              name="password"
              :hint="isEdit ? '留空则保留现有密码' : '可按数据库配置留空'"
              :error="fieldError('password')"
              data-field="password"
            >
              <input
                id="password"
                v-model="model.password"
                name="password"
                type="password"
                autocomplete="new-password"
              />
            </FormField>
            <FormField
              label="SSL 模式"
              name="ssl_mode"
              :error="fieldError('ssl_mode')"
              required
              data-field="ssl_mode"
            >
              <select id="ssl_mode" v-model="model.ssl_mode" name="ssl_mode">
                <template v-if="model.type === 'postgresql'">
                  <option value="disable">Disable</option>
                  <option value="allow">Allow</option>
                  <option value="prefer">Prefer</option>
                  <option value="require">Require</option>
                  <option value="verify-ca">Verify CA</option>
                  <option value="verify-full">Verify Full</option>
                </template>
                <template v-else>
                  <option value="disabled">Disabled</option>
                  <option value="preferred">Preferred</option>
                  <option value="required">Required</option>
                </template>
              </select>
            </FormField>
            <label v-if="isEdit" class="checkbox-field" data-field="clear_password">
              <input
                v-model="model.clear_password"
                type="checkbox"
                name="clear_password"
              />
              <span>
                <strong>清除已保存密码</strong>
                <small>仅在数据库账号不需要密码时使用。</small>
                <small v-if="fieldError('clear_password')" class="form-field__error">
                  {{ fieldError("clear_password") }}
                </small>
              </span>
            </label>
          </div>
        </div>

        <div class="form-actions">
          <RouterLink class="secondary-button" to="/studio/datasources">取消</RouterLink>
          <button class="primary-button primary-button--compact" type="submit" :disabled="submitting">
            {{ submitting ? "正在保存…" : isEdit ? "保存修改" : "创建数据源" }}
          </button>
        </div>
      </form>
    </template>
  </section>
</template>
