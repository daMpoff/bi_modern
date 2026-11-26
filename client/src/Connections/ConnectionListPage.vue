<script setup>
import GenericListPage from '../components/lists/GenericListPage.vue'
import { getListConfig } from '@/modules/bi_analysis_modern/client/src/components/lists/listConfigs.js'

const config = getListConfig('connections')
</script>

<template>
  <GenericListPage :config="config" />
</template>