<template>
  <div ref="dropdownRef" class="chart-export-dropdown">
    <button
      type="button"
      class="chart-export-btn chart-export-btn--icon-only"
      :class="{ 'chart-export-btn--compact': compact }"
      :title="buttonTitle"
      @click.stop="toggleDropdown"
      aria-label="Скачать"
    >
      <Download :size="compact ? 16 : 18" />
    </button>
    <Transition name="chart-export-menu">
      <ul v-if="isOpen" class="chart-export-menu">
        <li>
          <button type="button" class="chart-export-item" @click="onExportPng">
            <Image :size="16" />
            <span>PNG</span>
          </button>
        </li>
        <li>
          <button type="button" class="chart-export-item" @click="onExportCsv">
            <FileText :size="16" />
            <span>CSV</span>
          </button>
        </li>
        <li>
          <button type="button" class="chart-export-item" @click="onExportXlsx">
            <FileSpreadsheet :size="16" />
            <span>XLSX</span>
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Download, Image, FileText, FileSpreadsheet } from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { useDropdown } from '@/composables/useDropdown.js'

const props = defineProps({
  exportApi: {
    type: Object,
    default: () => ({})
  },
  chartTitle: {
    type: String,
    default: 'График'
  },
  buttonTitle: {
    type: String,
    default: 'Скачать график или данные'
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const toast = useToast()
const emit = defineEmits(['dropdown-toggle'])
const { dropdownRef, isOpen, toggleDropdown, closeDropdown } = useDropdown(emit)

function sanitizeFilename(name) {
  return (name || 'chart').replace(/[^\w\u0400-\u04FF-]/g, '_')
}

function buildCsv(data) {
  if (!data.length) return ''
  const headers = Object.keys(data[0])
  function escape(val) {
    const s = val === null || val === undefined ? '' : String(val)
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
    return s
  }
  const headerLine = headers.map(escape).join(',')
  const rows = data.map(row => headers.map(h => escape(row[h])).join(','))
  return '\uFEFF' + headerLine + '\n' + rows.join('\n')
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function getTitle() {
  return props.chartTitle || 'График'
}

function onExportPng() {
  closeDropdown()
  const api = props.exportApi
  const dataUrl = api?.getChartDataURL?.()
  if (!dataUrl) {
    toast.warning('График ещё не готов для экспорта или данные отсутствуют')
    return
  }
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = `${sanitizeFilename(getTitle())}.png`
  link.click()
  toast.success('Изображение сохранено')
}

function onExportCsv() {
  closeDropdown()
  const api = props.exportApi
  const data = api?.getChartData?.() ?? []
  if (!data.length) {
    toast.warning('Нет данных для экспорта')
    return
  }
  try {
    const csv = buildCsv(data)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    downloadBlob(blob, `${sanitizeFilename(getTitle())}.csv`)
    toast.success('CSV сохранён')
  } catch (err) {
    toast.error(err?.message || 'Ошибка экспорта CSV')
  }
}

async function onExportXlsx() {
  closeDropdown()
  const api = props.exportApi
  const data = api?.getChartData?.() ?? []
  if (!data.length) {
    toast.warning('Нет данных для экспорта')
    return
  }
  try {
    const ExcelJSModule = await import('exceljs')
    const ExcelJS = ExcelJSModule.default || ExcelJSModule.ExcelJS || ExcelJSModule
    const Workbook = ExcelJS.Workbook || ExcelJS
    const workbook = new Workbook()
    const worksheet = workbook.addWorksheet('Данные')
    const headers = Object.keys(data[0])
    worksheet.addRow(headers)
    data.forEach(row => {
      worksheet.addRow(headers.map(h => row[h] ?? ''))
    })
    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    downloadBlob(blob, `${sanitizeFilename(getTitle())}.xlsx`)
    toast.success('Excel сохранён')
  } catch (err) {
    toast.error(err?.message || 'Ошибка экспорта Excel')
  }
}
</script>

<style scoped lang="scss">
.chart-export-dropdown {
  position: relative;
  display: inline-block;
}

.chart-export-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: transparent;
  color: var(--color-secondary-text);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.chart-export-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-primary-text);
}

.chart-export-btn--icon-only {
  width: 36px;
  height: 36px;
}

.chart-export-btn--compact {
  width: 32px;
  height: 32px;
  color: var(--color-secondary-text);
  opacity: 0;
}

.dashboard-block:hover .chart-export-btn--compact,
.dashboard-block--selected .chart-export-btn--compact,
.dashboard-block--view .chart-export-btn--compact {
  opacity: 1;
}

.chart-export-btn--compact:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-primary-text);
}

.chart-export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin: 0.25rem 0 0;
  padding: 0.25rem 0;
  min-width: 140px;
  list-style: none;
  background: var(--bs-body-bg, #fff);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.08);
  z-index: 1050;
}

.chart-export-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  text-align: left;
  border: none;
  background: transparent;
  color: var(--bs-body-color, #212529);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.chart-export-item:hover {
  background: rgba(0, 0, 0, 0.06);
}

.chart-export-menu-enter-active,
.chart-export-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.1s ease;
}

.chart-export-menu-enter-from,
.chart-export-menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
