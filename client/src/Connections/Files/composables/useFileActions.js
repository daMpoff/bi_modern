import { apiClient } from '@/js/api/manager'
import { biEndpoints as endpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'
import { MAX_UPLOAD_SIZE_MB } from '@/modules/bi_analysis_modern/client/src/Connections/Files/uploadConfig'
import { confirmDelete } from '@/js/utils/confirm.js'

export function useFileActions(uploadedFiles, selectedFile, fileToReplace, loadUserFiles, connectionId, isSheetPickerVisible, currentUploadFile, availableSheets, isReplacing, fileError = null, selectFileCallback = null) {

  async function deleteFile(file) {
    const confirmed = await confirmDelete('Удаление', `Вы уверены, что хотите удалить файл "${file.name}"?`)
    if (!confirmed) return

    try {
      const res = await apiClient.delete(endpoints.bi.uploadDelete(file.id))

      if (res.status === 204 || res.success) {
        const deletedFileIndex = uploadedFiles.value.findIndex(f => f.id === file.id)
        const wasSelected = selectedFile.value?.id === file.id

        if (deletedFileIndex !== -1) {
          uploadedFiles.value.splice(deletedFileIndex, 1)
        }

        if (wasSelected) {
          if (fileError && typeof fileError === 'object' && 'value' in fileError) {
            fileError.value = null
          }

          let nextFile = null
          if (uploadedFiles.value.length > 0) {
            if (deletedFileIndex < uploadedFiles.value.length) {
              nextFile = uploadedFiles.value[deletedFileIndex]
            } else {
              nextFile = uploadedFiles.value[uploadedFiles.value.length - 1]
            }
          }

          if (nextFile && selectFileCallback) {
            selectFileCallback(nextFile)
          } else if (nextFile) {
            selectedFile.value = nextFile
          } else {
            selectedFile.value = null
          }
        }

        console.log('[deleteFile] файл удалён успешно')
      } else {
        logWarn('[deleteFile] ошибка удаления:', res)
      }
    } catch (error) {
      logError('[deleteFile] ошибка при запросе:', error)
    }
  }

  async function handleFileReplace(event) {
    const file = event.target.files[0]
    if (!file || !fileToReplace.value) return

    if (file.size === 0) {
      alert('Файл пустой. Пожалуйста, выберите непустой файл.')
      return
    }

    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      alert(`Файл превышает ${MAX_UPLOAD_SIZE_MB} МБ`)
      return
    }

    if (isReplacing) isReplacing.value = true

    try {
      if (file.name.endsWith('.xlsx')) {
        const formData = new FormData()
        formData.append('file', file)
        const sheetRes = await apiClient.post(endpoints.bi.xlsxSheets, formData)

        if (sheetRes.success && sheetRes.data.sheets.length > 1) {
          const tempFile = {
            name: file.name,
            originalFile: file,
            pendingSheets: sheetRes.data.sheets,
            replaceFileId: fileToReplace.value.id
          }
          currentUploadFile.value = tempFile
          availableSheets.value = sheetRes.data.sheets
          isSheetPickerVisible.value = true
          if (isReplacing) isReplacing.value = false
          event.target.value = ''
          return
        } else if (sheetRes.success && sheetRes.data.sheets.length === 1) {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('name', file.name)
          formData.append('sheet', sheetRes.data.sheets[0])

          const res = await apiClient.put(
            endpoints.bi.uploadDelete(fileToReplace.value.id),
            formData
          )

          if (res.success) {
            await loadUserFiles(connectionId)
            if (selectedFile.value && selectedFile.value.id === fileToReplace.value.id) {
              selectedFile.value = { ...res.data }
            }
          } else {
            logError('[handleFileReplace] Ошибка замены файла с листом:', res.errors)
            alert('Не удалось заменить файл')
          }
          if (isReplacing) isReplacing.value = false
          event.target.value = ''
          fileToReplace.value = null
          return
        }
      }

      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', file.name)
      if (file.name.endsWith('.xlsx')) {
        formData.append('sheet', 'Sheet1')
      }

      const res = await apiClient.put(
        endpoints.bi.uploadDelete(fileToReplace.value.id),
        formData
      )

      if (res.success) {
        await loadUserFiles(connectionId)
        if (selectedFile.value && selectedFile.value.id === fileToReplace.value.id) {
          selectedFile.value = { ...res.data }
        }
      } else {
        logError('[handleFileReplace] Ошибка замены файла:', res.errors)
        alert('Не удалось заменить файл')
      }
    } catch (error) {
      logError('[handleFileReplace] Ошибка при замене файла:', error)
      alert('Произошла ошибка при замене файла')
    }

    if (isReplacing) isReplacing.value = false
    event.target.value = ''
    fileToReplace.value = null
  }

  async function handleFileReplaceWithSheets(sheets) {
    isSheetPickerVisible.value = false
    const file = currentUploadFile.value
    if (!file || !sheets.length || !file.replaceFileId) return

    if (isReplacing) isReplacing.value = true

    try {
      const sheet = sheets[0]
      const formData = new FormData()
      formData.append('file', file.originalFile)
      formData.append('sheet', sheet)
      formData.append('name', file.name)

      const res = await apiClient.put(
        endpoints.bi.uploadDelete(file.replaceFileId),
        formData
      )

      if (res.success) {
        await loadUserFiles(connectionId)
        if (selectedFile.value && selectedFile.value.id === file.replaceFileId) {
          selectedFile.value = { ...res.data }
        }
      } else {
        logError('[handleFileReplaceWithSheets] Ошибка замены файла:', res.errors)
        alert(`Не удалось заменить файл листом "${sheet}"`)
      }
    } catch (error) {
      logError('[handleFileReplaceWithSheets] Ошибка:', error)
      alert('Ошибка при замене файла')
    }

    if (isReplacing) isReplacing.value = false
    currentUploadFile.value = null
    fileToReplace.value = null
  }

  async function renameFile(file) {
    const originalExt = file.name.split('.').pop()
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '')

    const newNameInput = prompt('Новое имя файла:', nameWithoutExt)
    if (!newNameInput || newNameInput.trim() === '') return

    const newName = `${newNameInput.trim()}.${originalExt}`

    const res = await apiClient.patch(endpoints.bi.uploadDelete(file.id), {
      name: newName
    })

    if (res.success) {
      await loadUserFiles(connectionId)
    } else {
      alert('Ошибка переименования')
      logError('[renameFile] Ошибка:', res.errors)
    }
  }

  return {
    deleteFile,
    handleFileReplace,
    handleFileReplaceWithSheets,
    renameFile
  }
}
