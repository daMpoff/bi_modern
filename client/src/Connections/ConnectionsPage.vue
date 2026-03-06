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
    router.push('/bi/connections/new')
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

.connections-page {
    display: flex;
    flex-direction: column;
    height: 90vh;
    min-height: 90vh;
    max-height: 90vh;
    overflow: hidden;
    background: #ffffff;
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
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.92) 100%);
    overflow: hidden;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.04);
    position: relative;

    // Декоративные элементы для сайдбара
    &::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.08) 0%, transparent 70%);
        filter: blur(40px);
        pointer-events: none;
        z-index: 0;
    }
}

.connections-preview {
    display: flex;
    flex-direction: column;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.92) 100%);
    overflow: hidden;
    position: relative;

    // Декоративные прозрачные графические элементы
    &::before,
    &::after {
        content: '';
        position: absolute;
        pointer-events: none;
        opacity: 0.15;
        z-index: 0;
    }

    &::before {
        top: -10%;
        right: -5%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.3) 0%, transparent 70%);
        border-radius: 50%;
        filter: blur(60px);
        animation: float 20s ease-in-out infinite;
    }

    &::after {
        bottom: -15%;
        left: -8%;
        width: 350px;
        height: 350px;
        background: radial-gradient(circle, rgba(var(--bs-primary-rgb), 0.25) 0%, transparent 70%);
        border-radius: 50%;
        filter: blur(50px);
        animation: float 25s ease-in-out infinite reverse;
    }

    // Дополнительные декоративные элементы через псевдоэлемент wrapper
    background-image:
        radial-gradient(circle at 20% 30%, rgba(var(--bs-info-rgb), 0.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(var(--bs-primary-rgb), 0.06) 0%, transparent 50%),
        radial-gradient(circle at 50% 50%, rgba(var(--bs-success-rgb), 0.04) 0%, transparent 50%);
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
