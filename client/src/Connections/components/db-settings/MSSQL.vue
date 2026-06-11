<template>
  <DatabaseConnectionForm
    title="Microsoft SQL Server"
    :logo-url="MssqlIcon"
    logo-class="mssql-logo"
    :message="message"
    :error="error"
    :is-checked="isChecked"
    :loading="loading"
    @create="createConnection"
    @check-connection="handleCheckConnection"
    ref="formRef"
  >
    <DatabaseFormFields
      v-model="host"
      label="Имя хоста"
      field-id="host"
      type="text"
      :required="true"
      :disabled="loading"
      :full-width="true"
      error-message="Укажите хост"
    />
    
    <DatabaseFormFields
      v-model="port"
      label="Порт"
      field-id="port"
      type="number"
      :required="true"
      :disabled="loading"
      control-class="form-control-port"
      error-message="Укажите порт"
    />

    <DatabaseFormFields
      v-model="database"
      label="Путь к базе данных"
      field-id="database"
      type="text"
      :required="true"
      :disabled="loading"
      :full-width="true"
      error-message="Укажите путь"
    />

    <DatabaseFormFields
      v-model="username"
      label="Имя пользователя"
      field-id="username"
      type="text"
      :required="true"
      :disabled="loading"
      control-class="form-control-sm form-control-wide"
      error-message="Укажите имя пользователя"
    />

    <DatabaseFormFields
      v-model="password"
      label="Пароль"
      field-id="password"
      type="password"
      :required="true"
      :disabled="loading"
      control-class="form-control-pass form-control-wide"
      error-message="Укажите пароль"
    />
  </DatabaseConnectionForm>
  
  <ConnectionNameDialog 
    v-model:visible="showDialog" 
    :connector-type="'mssql'" 
    :connection-config="{
      host: host,
      port: port,
      username: username,
      password: password,
      database: database
    }" 
    @saved="onConnectionSaved" 
  />
</template>

<script setup>
import { ref, watch } from 'vue'
import DatabaseConnectionForm from './DatabaseConnectionForm.vue'
import DatabaseFormFields from './DatabaseFormFields.vue'
import ConnectionNameDialog from '@/modules/bi_analysis_modern/client/src/Connections/components/ConnectionNameDialog.vue'
import { useDatabaseConnection } from './composables/useDatabaseConnection'
import { useRouter } from 'vue-router'
import MssqlIcon from '@/modules/bi_analysis_modern/client/src/assets/icons/mssql.svg'

const router = useRouter()
const formRef = ref(null)
const showDialog = ref(false)

const {
  form: connectionForm,
  host,
  port,
  database,
  username,
  password,
  message,
  error,
  isChecked,
  loading,
  checkConnection
} = useDatabaseConnection('mssql', 1433)

// Связываем форму из базового компонента с логикой композабла
watch(() => formRef.value?.form, (newForm) => {
  if (newForm) {
    connectionForm.value = newForm
  }
}, { immediate: true })

async function handleCheckConnection() {
  await checkConnection()
}

async function createConnection() {
  const prevMessage = message.value
  message.value = ''

  await checkConnection()

  if (!isChecked.value || error.value) {
    message.value = prevMessage
    return
  }

  showDialog.value = true
}

function onConnectionSaved(data) {
  message.value = `Подключение "${data.name}" успешно сохранено`
  error.value = false
  isChecked.value = true

  setTimeout(() => {
    router.push({ name: 'ConnectionsModern' })
  }, 3000)
}
</script>

<style scoped lang="scss">
.mssql-logo {
  filter: invert(7%) sepia(69%) saturate(4321%) hue-rotate(347deg) brightness(119%) contrast(91%);
}
</style>