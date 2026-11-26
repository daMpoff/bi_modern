/**
 * Конфиг загрузки файлов BI. Значения из env (VITE_BI_UPLOAD_*), задаются при сборке.
 */
const raw = import.meta.env.VITE_BI_UPLOAD_MAX_SIZE_MB
export const MAX_UPLOAD_SIZE_MB = raw != null && raw !== '' ? parseInt(String(raw), 10) : 200
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

export const MAX_UPLOAD_FILES = 10
