<script setup>
import GenericListPage from './ConnectionList/GenericListPage.vue'
import { getListConfig } from '@/modules/bi_analysis_modern/client/src/js/listConfigs.js'

const config = getListConfig('connections')
</script>

<template>
  <GenericListPage :config="config" />
</template>