import { defaultTheme } from '@vuepress/theme-default'
import { viteBundler } from '@vuepress/bundler-vite'
import { markdownMathPlugin } from '@vuepress/plugin-markdown-math'
import { markdownChartPlugin } from '@vuepress/plugin-markdown-chart'
import { slimsearchPlugin } from '@vuepress/plugin-slimsearch'
import markdownItFootnote from 'markdown-it-footnote'
import katex from 'katex'

export default {
  lang: 'en-US',
  title: 'Ragu & Tachyon',
  description: 'Unofficial notes on the Ragu proving system and Project Tachyon, from first principles',
  // Served from custom domain https://ragu-tachyon.methyl.cc
  base: '/',
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
  ],

  bundler: viteBundler(),

  theme: defaultTheme({
    navbar: [
      { text: 'Home', link: '/' },
      {
        text: 'Part One',
        children: [
          { text: 'Chapter One', link: '/chapter-one.html' },
          { text: 'Chapter Two', link: '/chapter-two.html' },
        ],
      },
      { text: 'Final Recap', link: '/recap.html' },
      {
        text: 'Appendix',
        children: [
          { text: 'Appendix One', link: '/appendix-one.html' },
        ],
      },
    ],
    // Reading order for the Prev/Next footer links on each page.
    sidebar: [
      { text: 'Chapter One', link: '/chapter-one.html' },
      { text: 'Chapter Two', link: '/chapter-two.html' },
      { text: 'Final Recap', link: '/recap.html' },
      {
        text: 'Appendix',
        children: [
          { text: 'Appendix One', link: '/appendix-one.html' },
        ],
      },
    ],
  }),

  plugins: [
    markdownChartPlugin({ mermaid: true }),
    markdownMathPlugin({ type: 'katex', output: 'html' }),
    slimsearchPlugin({
      indexContent: true,
      // Suggestions start a separate worker on page load. Keep the full-text
      // index deferred until the reader opens search instead.
      suggestion: false,
    }),
  ],

  extendsMarkdown(md) {
    md.use(markdownItFootnote)

    // Markdown-it treats the contents of raw HTML blocks as opaque. Render
    // only TeX inside <summary> elements so the footnote plugin does not
    // accidentally insert footnote markup into the raw HTML block.
    const defaultHtmlBlock = md.renderer.rules.html_block
    const defaultHtmlInline = md.renderer.rules.html_inline

    const renderSummaryMath = (defaultRule) => (tokens, idx, options, env, self) => {
      const token = tokens[idx]
      const content = token.content.replace(
        /(<summary\b[^>]*>)([\s\S]*?)(<\/summary>)/gi,
        (_, open, inner, close) => {
          const rendered = inner.replace(
            /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g,
            (_, display, inline) => katex.renderToString(display ?? inline, {
              displayMode: display !== undefined,
              throwOnError: false,
            }),
          )
          return open + rendered + close
        },
      )

      if (content === token.content) {
        return defaultRule
          ? defaultRule(tokens, idx, options, env, self)
          : self.renderToken(tokens, idx, options)
      }

      return content
    }

    md.renderer.rules.html_block = renderSummaryMath(defaultHtmlBlock)
    md.renderer.rules.html_inline = renderSummaryMath(defaultHtmlInline)
  },
}
