<template>
    <div class="connections-page">
        <div class="connections-layout">
            <!-- Левая панель: Дерево подключений -->
            <aside class="connections-sidebar">
                <ConnectionsTree
                    ref="connectionsTreeRef"
                    @create-connection="goToCreateConnection"
                    @node-click="handleNodeClick"
                    @file-deleted="handleFileDeleted"
                />
            </aside>

            <!-- Правая панель: Предпросмотр данных -->
            <main class="connections-preview">
                <ConnectionPreview
                    :node="selectedNode"
                    :is-loading="isLoadingPreview"
                    @connection-deleted="handleConnectionDeleted"
                />
            </main>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ConnectionsTree from './ConnectionsTree.vue'
import ConnectionPreview from './ConnectionsTree/ConnectionPreview.vue'

const router = useRouter()
const selectedNode = ref(null)
const isLoadingPreview = ref(false)
const connectionsTreeRef = ref(null)

function goToCreateConnection() {
    router.push('/bi-modern/connections/new')
}

function handleNodeClick(node) {
    selectedNode.value = node
    isLoadingPreview.value = true
    // Загрузка предпросмотра будет происходить в компоненте ConnectionPreview
    setTimeout(() => {
        isLoadingPreview.value = false
    }, 100)
}

function handleFileDeleted({ connectionId }) {
    // Обновляем дерево подключений после удаления файла
    if (connectionsTreeRef.value) {
        // Диспатчим событие для обновления счетчика файлов в ConnectionInfo
        window.dispatchEvent(new CustomEvent('files-reload', { detail: { connectionId } }))
    }
}

function handleConnectionDeleted(connectionId) {
    // Очищаем выбранный узел, если удалено выбранное подключение
    if (selectedNode.value?.id === connectionId) {
        selectedNode.value = null
    }
    
    // Обновляем дерево подключений
    // Используем событие для обновления через ConnectionsTree
    window.dispatchEvent(new CustomEvent('connections-reload'))
}
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';
@import '../scss/_bi-theme.scss';

.connections-page {
    @include bi-burgundy-tokens;
    display: flex;
    flex-direction: column;
    height: 90vh;
    min-height: 90vh;
    max-height: 90vh;
    overflow: hidden;
    background: var(--color-background);
}

.connections-layout {
    display: grid;
    grid-template-columns: 340px 1fr;
    height: 100%;
    background: var(--color-background);
    gap: 0;
}

.connections-sidebar {
    display: flex;
    flex-direction: column;
    background: var(--color-primary-background);
    border-right: 1px solid var(--color-border);
    overflow: hidden;
    position: relative;
}

.connections-preview {
    display: flex;
    flex-direction: column;
    background: var(--color-background);
    overflow: hidden;
    position: relative;
}

@keyframes float {
    0%, 100% {
        transform: translate(0, 0) scale(1);
    }
    33% {
        transform: translate(30px, -30px) scale(1.1);
    }
    66% {
        transform: translate(-20px, 20px) scale(0.9);
    }
}

// Адаптивность
@media (max-width: 1024px) {
    .connections-layout {
        grid-template-columns: 300px 1fr;
    }
}

@media (max-width: 768px) {
    .connections-layout {
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr;
    }
    
    .connections-sidebar {
        max-height: 350px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }
}
</style>
