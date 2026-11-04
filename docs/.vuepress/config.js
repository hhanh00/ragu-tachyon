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
        text: 'The Problem',
        children: [
          { text: 'Scaling Zcash', link: '/scaling-zcash.html' },
          { text: 'An Introduction to Proof-Carrying Data', link: '/pcd-intro.html' },
        ],
      },
      {
        text: 'Proof Structure',
        children: [
          { text: 'Statements and Challenges', link: '/statements-and-challenges.html' },
          { text: 'Arithmetization', link: '/arithmetization.html' },
          { text: 'QAP and Polynomial Encoding', link: '/polynomial-encoding.html' },
          { text: 'Polynomial Commitments', link: '/polynomial-commitments.html' },
          { text: 'The Inner Product Argument', link: '/inner-product-argument.html' },
          { text: 'Batched Openings', link: '/batched-openings.html' },
          { text: 'The Complete Proof', link: '/nark.html' },
        ],
      },
      {
        text: 'Recursion',
        children: [
          { text: 'Recursive Proofs', link: '/recursive-proofs.html' },
          { text: 'Accumulation', link: '/accumulation.html' },
          { text: 'Split Accumulation', link: '/split-accumulation.html' },
          { text: 'Curve Cycles', link: '/curve-cycles.html' },
        ],
      },
      {
        text: 'Ragu',
        children: [
          { text: 'Revdot Folding', link: '/revdot-folding.html' },
          { text: 'Wiring and the Registry', link: '/wiring-and-registry.html' },
          { text: 'Endoscalars', link: '/endoscalars.html' },
          { text: 'Staging', link: '/staging.html' },
          { text: 'Recursion in Ragu', link: '/ragu-recursion.html' },
        ],
      },
      {
        text: 'Tachyon',
        children: [
          { text: 'Notes, Nullifiers, and Tachygrams', link: '/notes-and-nullifiers.html' },
          { text: 'Pool State and Anchors', link: '/pool-state.html' },
          { text: 'Oblivious Sync', link: '/oblivious-sync.html' },
          { text: 'The Proof Tree', link: '/proof-tree.html' },
          { text: 'Aggregation and Bundles', link: '/aggregation-and-bundles.html' },
        ],
      },
      { text: 'Final Recap', link: '/recap.html' },
      {
        text: 'Appendix',
        children: [
          { text: 'Notation', link: '/appendix-notation.html' },
          { text: 'Glossary', link: '/appendix-glossary.html' },
          { text: 'Curves', link: '/appendix-curves.html' },
        ],
      },
    ],
    // Reading order for the Prev/Next footer links on each page.
    sidebar: [
      { text: 'Scaling Zcash', link: '/scaling-zcash.html' },
      { text: 'An Introduction to Proof-Carrying Data', link: '/pcd-intro.html' },
      { text: 'Statements and Challenges', link: '/statements-and-challenges.html' },
      { text: 'Arithmetization', link: '/arithmetization.html' },
      { text: 'QAP and Polynomial Encoding', link: '/polynomial-encoding.html' },
      { text: 'Polynomial Commitments', link: '/polynomial-commitments.html' },
      { text: 'The Inner Product Argument', link: '/inner-product-argument.html' },
      { text: 'Batched Openings', link: '/batched-openings.html' },
      { text: 'The Complete Proof', link: '/nark.html' },
      { text: 'Recursive Proofs', link: '/recursive-proofs.html' },
      { text: 'Accumulation', link: '/accumulation.html' },
      { text: 'Split Accumulation', link: '/split-accumulation.html' },
      { text: 'Curve Cycles', link: '/curve-cycles.html' },
      { text: 'Revdot Folding', link: '/revdot-folding.html' },
      { text: 'Wiring and the Registry', link: '/wiring-and-registry.html' },
      { text: 'Endoscalars', link: '/endoscalars.html' },
      { text: 'Staging', link: '/staging.html' },
      { text: 'Recursion in Ragu', link: '/ragu-recursion.html' },
      { text: 'Notes, Nullifiers, and Tachygrams', link: '/notes-and-nullifiers.html' },
      { text: 'Pool State and Anchors', link: '/pool-state.html' },
      { text: 'Oblivious Sync', link: '/oblivious-sync.html' },
      { text: 'The Proof Tree', link: '/proof-tree.html' },
      { text: 'Aggregation and Bundles', link: '/aggregation-and-bundles.html' },
      { text: 'Final Recap', link: '/recap.html' },
      {
        text: 'Appendix',
        children: [
          { text: 'Notation', link: '/appendix-notation.html' },
          { text: 'Glossary', link: '/appendix-glossary.html' },
          { text: 'Curves', link: '/appendix-curves.html' },
        ],
      },
    ],
  }),

  plugins: [
    markdownChartPlugin({ mermaid: true }),
    markdownMathPlugin({
      type: 'katex',
      output: 'html',
      // The same shorthand the Ragu Book uses.
      macros: {
        '\\v': '\\mathbf{#1}',
        '\\F': '\\mathbb{F}',
        '\\G': '\\mathbb{G}',
        '\\dot': '\\langle #1,\\,#2 \\rangle',
        '\\rv': '\\hat{\\mathbf{#1}}',
        '\\revdot': '\\langle\\!\\langle #1,\\,#2 \\rangle\\!\\rangle',
      },
    }),
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
