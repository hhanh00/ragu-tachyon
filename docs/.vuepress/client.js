import { defineClientConfig } from 'vuepress/client'
import SectionGrid from './components/SectionGrid.vue'

export default defineClientConfig({
  enhance({ app }) {
    app.component('SectionGrid', SectionGrid)
  },
})
