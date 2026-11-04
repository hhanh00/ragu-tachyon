<script setup>
const groups = [
  {
    number: '01',
    name: 'The Problem',
    desc: 'Trace the costs that shape the proof system.',
    color: '#2563eb',
    soft: '#dbeafe',
    items: [
      { number: '01', title: 'Scaling Zcash', desc: 'Trace state growth and wallet sync costs to the design of nullifiers and in-band notes.', link: '/scaling-zcash.html', symbol: 'Δ' },
    ],
  },
  {
    number: '02',
    name: 'The Structure of a Proof',
    desc: 'Follow one statement through arithmetization, polynomial encoding, commitments, and openings.',
    color: '#7c3aed',
    soft: '#ede9fe',
    items: [
      { number: '02', title: 'Statements and Challenges', desc: 'Define statements and witnesses, then use random challenges to catch false claims.', link: '/statements-and-challenges.html', symbol: 'r' },
      { number: '03', title: 'Arithmetization', desc: 'Express a computation as constraints, ending in one revdot equation, with a short comparison to R1CS and PLONK.', link: '/arithmetization.html', symbol: '⟨r, r̂⟩' },
      { number: '04', title: 'Polynomial Encoding', desc: 'Turn the single constraint into a polynomial identity that a random point can test.', link: '/polynomial-encoding.html', symbol: 'c(X)' },
      { number: '05', title: 'Polynomial Commitments', desc: 'Build Pedersen commitments and turn a polynomial evaluation into an inner product claim.', link: '/polynomial-commitments.html', symbol: 'C' },
      { number: '06', title: 'The Inner Product Argument', desc: 'Halve an inner product claim round by round and locate the linear verifier cost.', link: '/inner-product-argument.html', symbol: 'L, R' },
      { number: '07', title: 'Batched Openings', desc: 'Reduce many evaluation claims to one using quotient polynomials.', link: '/batched-openings.html', symbol: 'α, β' },
      { number: '08', title: 'The Complete Proof', desc: 'Assemble every earlier step into one proof, without recursion yet.', link: '/nark.html', symbol: 'r(X)' },
    ],
  },
  {
    number: '03',
    name: 'Recursion',
    desc: 'Replace full recursive verification with deferred checks.',
    color: '#059669',
    soft: '#d1fae5',
    items: [
      { number: '09', title: 'Recursive Proofs and PCD', desc: 'Prove the verification of earlier proofs across chains and trees of computation.', link: '/recursive-proofs.html', symbol: 'π' },
      { number: '10', title: 'Accumulation', desc: 'Defer the expensive IPA check and merge deferred claims, following Halo.', link: '/accumulation.html', symbol: 'acc' },
      { number: '11', title: 'Split Accumulation', desc: 'Fold public instances separately from witnesses, so a NARK is enough.', link: '/split-accumulation.html', symbol: 'acc.V' },
      { number: '12', title: 'Curve Cycles', desc: 'Use the Pasta cycle to keep group and field arithmetic native on each side.', link: '/curve-cycles.html', symbol: '𝔽p, 𝔽q' },
    ],
  },
  {
    number: '04',
    name: 'Ragu',
    desc: 'Study the parts of the recursive construction specific to Ragu.',
    color: '#d97706',
    soft: '#fef3c7',
    items: [
      { number: '13', title: 'Revdot Folding', desc: 'Reduce many revdot claims to one with a two-layer protocol.', link: '/revdot-folding.html', symbol: 'k(Y)' },
      { number: '14', title: 'Wiring and the Registry', desc: 'Check wiring consistency across many circuits without verification keys.', link: '/wiring-and-registry.html', symbol: 's(X,Y)' },
      { number: '15', title: 'Endoscalars', desc: 'Share challenges across the cycle and reduce scalar multiplication costs.', link: '/endoscalars.html', symbol: 'ζ' },
      { number: '16', title: 'Staging', desc: 'Commit to a circuit trace in stages and keep inputs consistent between circuits.', link: '/staging.html', symbol: 'stage' },
      { number: '17', title: 'Recursion in Ragu', desc: 'Assemble internal circuits, public inputs, and compression into a full PCD step.', link: '/ragu-recursion.html', symbol: 'fuse' },
    ],
  },
  {
    number: '05',
    name: 'Tachyon',
    desc: 'Apply Ragu to a shielded protocol without perpetual nullifier state.',
    color: '#db2777',
    soft: '#fce7f3',
    items: [
      { number: '18', title: 'Notes, Nullifiers, and Tachygrams', desc: 'Follow a note from its key hierarchy to the values it publishes.', link: '/notes-and-nullifiers.html', symbol: 'nf' },
      { number: '19', title: 'Pool State and Anchors', desc: 'Commit to the pool with a Poseidon hash chain over stamps and epochs.', link: '/pool-state.html', symbol: 'anchor' },
      { number: '20', title: 'Oblivious Sync', desc: 'Delegate proofs of nullifier absence without revealing the note.', link: '/oblivious-sync.html', symbol: 'Δ(X)' },
      { number: '21', title: 'The Proof Tree', desc: 'Walk through each proof step from note creation to a spend.', link: '/proof-tree.html', symbol: 'step' },
      { number: '22', title: 'Aggregation and Bundles', desc: 'Merge stamps across transactions and study the resulting on-chain format.', link: '/aggregation-and-bundles.html', symbol: 'stamp' },
    ],
  },
  {
    number: '06',
    name: 'Final Recap',
    desc: 'Connect the protocol layers in a single example.',
    color: '#0f766e',
    soft: '#ccfbf1',
    items: [
      { number: '23', title: 'Final Recap', desc: 'Trace one Tachyon spend through every layer of the system.', link: '/recap.html', symbol: 'Σ', final: true },
    ],
  },
  {
    number: 'A',
    name: 'Appendix',
    desc: 'Look up notation, terms, and curve parameters used across the chapters.',
    color: '#64748b',
    soft: '#f1f5f9',
    appendix: true,
    items: [
      { number: 'A1', title: 'Notation', desc: 'The symbols used for groups, vectors, and polynomials.', link: '/appendix-notation.html', symbol: '⟨a, b⟩' },
      { number: 'A2', title: 'Glossary', desc: 'One-line reminders, each linked to the chapter that teaches the term.', link: '/appendix-glossary.html', symbol: 'A–Z' },
      { number: 'A3', title: 'Curves', desc: 'The toy curve cycle used in worked examples, and the Pasta curves.', link: '/appendix-curves.html', symbol: 'E' },
    ],
  },
]

const chapterCount = groups.filter(g => !g.appendix).reduce((n, g) => n + g.items.length, 0)
</script>

<template>
  <div class="site-home">
    <section class="home-hero" aria-labelledby="home-title">
      <div class="hero-copy">
        <p class="kicker"><span class="kicker-dot"></span>Unofficial notes</p>
        <h1 id="home-title">Ragu &amp; Tachyon</h1>
        <p class="hero-text">
          Learn how the Ragu proving system works and how Project Tachyon uses it, starting from linear algebra, hashes, and discrete log. These notes are unofficial and assume no knowledge of proving systems.
        </p>
        <div class="hero-actions">
          <a class="start-button" href="/scaling-zcash.html">
            Start reading
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" /></svg>
          </a>
          <span class="chapter-count"><strong>{{ chapterCount }}</strong> chapters</span>
        </div>
      </div>

      <div class="field-visual" aria-hidden="true">
        <div class="visual-grid"></div>
        <svg class="field-lines" viewBox="0 0 520 420" fill="none">
          <path d="M78 96C150 110 170 175 215 196" />
          <path d="M78 212c62 0 92-8 137-8" />
          <path d="M92 326c58-22 86-82 128-108" />
          <path d="M322 200c52-30 76-56 118-82" />
          <path d="M322 222c52 26 74 58 112 88" />
          <ellipse cx="271" cy="215" rx="174" ry="73" transform="rotate(-24 271 215)" />
          <ellipse cx="271" cy="215" rx="174" ry="73" transform="rotate(34 271 215)" />
        </svg>
        <div class="visual-core">
          <span>π</span>
          <small>proof</small>
        </div>
        <span class="particle particle-a"></span>
        <span class="particle particle-b"></span>
        <span class="particle particle-c"></span>
        <div class="formula formula-a">C = ⟨a, G⟩</div>
        <div class="formula formula-b">p(x) = v</div>
        <div class="axis-label axis-x">step</div>
        <div class="axis-label axis-t">depth</div>
      </div>
    </section>

    <section class="curriculum" aria-labelledby="curriculum-title">
      <div class="curriculum-intro">
        <div>
          <p class="section-label">Contents</p>
          <h2 id="curriculum-title">Chapters</h2>
        </div>
        <p>Read in order, or jump directly to the idea you need. Only Chapter 05 is drafted so far.</p>
      </div>

      <div class="stages">
        <section
          v-for="g in groups"
          :key="g.name"
          class="stage"
          :style="{ '--accent': g.color, '--accent-soft': g.soft }"
        >
          <div class="stage-marker" aria-hidden="true">
            <span>{{ g.number }}</span>
          </div>

          <header class="stage-head">
            <p>{{ g.items.length }} {{ g.items.length === 1 ? 'chapter' : 'chapters' }}</p>
            <h3>{{ g.name }}</h3>
            <div class="stage-rule"></div>
            <p class="stage-desc">{{ g.desc }}</p>
          </header>

          <div class="cards" :class="{ 'cards-single': g.items.length === 1 }">
            <a
              v-for="s in g.items"
              :key="s.link"
              class="chapter-card"
              :class="{ 'final-card': s.final }"
              :href="s.link"
            >
              <div class="card-topline">
                <span class="chapter-number">{{ g.appendix ? s.number : 'Chapter ' + s.number }}</span>
                <span class="chapter-symbol">{{ s.symbol }}</span>
              </div>
              <h4>{{ s.title }}</h4>
              <p>{{ s.desc }}</p>
              <span class="read-link">
                Read chapter
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11m-4-4 4 4-4 4" /></svg>
              </span>
            </a>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<style>
.vp-home .vp-hero { display: none; }
.vp-home { padding: 0; max-width: none; }
.vp-home [vp-content] { max-width: none; padding: 0; }
.vp-home [vp-content] > div { max-width: none; }

.site-home {
  --ink: #152238;
  --muted: #5f6b7c;
  --paper: #fbfcfe;
  --line: #dfe5ec;
  color: var(--ink);
  overflow: hidden;
}
.home-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(380px, .9fr);
  align-items: center;
  gap: clamp(2rem, 6vw, 6.5rem);
  max-width: 1280px;
  min-height: 560px;
  margin: 0 auto;
  padding: clamp(4.5rem, 8vw, 7.5rem) clamp(2rem, 6vw, 5.5rem) 4.5rem;
}
.hero-copy { position: relative; z-index: 2; }
.kicker, .section-label { margin: 0; color: #2563eb; font-size: .73rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
.kicker { display: flex; align-items: center; gap: .6rem; }
.kicker-dot { width: 7px; height: 7px; border-radius: 50%; background: #2563eb; box-shadow: 0 0 0 5px rgba(37, 99, 235, .12); }
.home-hero h1 { max-width: 40rem; margin: 1.25rem 0 1.35rem; color: var(--ink); font-size: clamp(3.1rem, 6vw, 5.3rem); font-weight: 700; letter-spacing: -.055em; line-height: .98; }
.hero-text { max-width: 35rem; margin: 0; color: var(--muted); font-size: clamp(1.05rem, 1.7vw, 1.3rem); line-height: 1.65; }
.hero-actions { display: flex; align-items: center; gap: 1.5rem; margin-top: 2rem; }
.start-button { display: inline-flex; align-items: center; gap: .7rem; padding: .85rem 1.1rem; border-radius: 8px; color: #fff !important; background: #152238; font-size: .9rem; font-weight: 650; text-decoration: none !important; box-shadow: 0 9px 24px rgba(21, 34, 56, .16); transition: transform .2s ease, background .2s ease, box-shadow .2s ease; }
.start-button:hover { background: #2563eb; transform: translateY(-2px); box-shadow: 0 12px 30px rgba(37, 99, 235, .2); }
.start-button:focus-visible, .chapter-card:focus-visible { outline: 3px solid #60a5fa; outline-offset: 4px; }
.start-button svg, .read-link svg { width: 18px; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.chapter-count { color: var(--muted); font-size: .84rem; }
.chapter-count strong { color: var(--ink); font-family: Georgia, serif; font-size: 1.2rem; }
.field-visual { position: relative; width: min(100%, 500px); aspect-ratio: 1.18; justify-self: center; border: 1px solid rgba(37, 99, 235, .18); border-radius: 50% 50% 48% 52% / 43% 55% 45% 57%; background: radial-gradient(circle at 50% 50%, rgba(37, 99, 235, .1), transparent 24%), linear-gradient(145deg, rgba(219, 234, 254, .7), rgba(238, 242, 255, .2)); transform: rotate(-2deg); }
.visual-grid { position: absolute; inset: 7%; border-radius: inherit; opacity: .35; background-image: linear-gradient(rgba(37, 99, 235, .15) 1px, transparent 1px), linear-gradient(90deg, rgba(37, 99, 235, .15) 1px, transparent 1px); background-size: 38px 38px; mask-image: radial-gradient(circle, #000 20%, transparent 72%); }
.field-lines { position: absolute; inset: 3%; width: 94%; height: 94%; stroke: #2563eb; stroke-width: 1.2; opacity: .5; }
.field-lines ellipse { stroke-dasharray: 4 7; opacity: .65; }
.visual-core { position: absolute; top: 50%; left: 52%; display: grid; place-items: center; width: 102px; height: 102px; border: 1px solid rgba(37, 99, 235, .25); border-radius: 50%; background: rgba(255, 255, 255, .8); box-shadow: 0 22px 60px rgba(37, 99, 235, .18), inset 0 0 0 8px rgba(37, 99, 235, .04); transform: translate(-50%, -50%); }
.visual-core span { margin-top: .55rem; color: #2563eb; font-family: Georgia, serif; font-size: 2.4rem; font-style: italic; line-height: 1; }
.visual-core small { align-self: start; color: var(--muted); font-size: .62rem; letter-spacing: .14em; text-transform: uppercase; }
.particle { position: absolute; width: 10px; height: 10px; border: 3px solid #fff; border-radius: 50%; background: #7c3aed; box-shadow: 0 3px 12px rgba(124, 58, 237, .4); }
.particle-a { top: 24%; left: 18%; }
.particle-b { right: 14%; bottom: 29%; background: #059669; box-shadow: 0 3px 12px rgba(5, 150, 105, .4); }
.particle-c { right: 20%; top: 20%; width: 7px; height: 7px; background: #d97706; }
.formula { position: absolute; padding: .45rem .7rem; border: 1px solid rgba(21, 34, 56, .1); border-radius: 6px; color: var(--ink); background: rgba(255, 255, 255, .82); font-family: Georgia, serif; font-size: .82rem; box-shadow: 0 8px 22px rgba(21, 34, 56, .08); backdrop-filter: blur(8px); }
.formula-a { top: 10%; right: 9%; }
.formula-b { bottom: 11%; left: 8%; }
.axis-label { position: absolute; color: #8290a3; font-size: .6rem; letter-spacing: .12em; text-transform: uppercase; }
.axis-x { right: 5%; top: 51%; }
.axis-t { left: 51%; top: 4%; writing-mode: vertical-rl; }
.curriculum { max-width: 1280px; margin: 0 auto; padding: 4.5rem clamp(2rem, 6vw, 5.5rem) 5rem; border-top: 1px solid var(--line); }
.curriculum-intro { display: flex; align-items: end; justify-content: space-between; gap: 3rem; padding-bottom: 2.5rem; }
.curriculum-intro h2 { margin: .4rem 0 0; color: var(--ink); font-size: clamp(2rem, 4vw, 3rem); font-weight: 700; letter-spacing: -.035em; }
.curriculum-intro > p { max-width: 20rem; margin: 0 0 .35rem; color: var(--muted); font-size: .9rem; line-height: 1.55; }
.stages { position: relative; }
.stages::before { content: ''; position: absolute; top: 1.6rem; bottom: 1.6rem; left: 25px; width: 1px; background: var(--line); }
.stage { position: relative; display: grid; grid-template-columns: 52px minmax(180px, .72fr) minmax(0, 2.2fr); gap: clamp(1.25rem, 3vw, 3.5rem); padding: 2.8rem 0; border-top: 1px solid var(--line); }
.stage:last-child { border-bottom: 1px solid var(--line); }
.stage-marker { position: relative; z-index: 1; padding-top: .1rem; }
.stage-marker span { display: grid; place-items: center; width: 51px; height: 51px; border: 1px solid color-mix(in srgb, var(--accent) 35%, white); border-radius: 50%; color: var(--accent); background: var(--paper); font-family: Georgia, serif; font-size: .9rem; font-weight: 700; }
.stage-head > p:first-child { margin: .1rem 0 .45rem; color: var(--accent); font-size: .65rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }
.stage-head h3 { margin: 0; border: 0; color: var(--ink); font-size: 1.45rem; font-weight: 700; letter-spacing: -.025em; }
.stage-rule { width: 2rem; height: 2px; margin: 1.1rem 0; background: var(--accent); }
.stage-desc { max-width: 15rem; margin: 0; color: var(--muted); font-size: .82rem; line-height: 1.6; }
.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; }
.chapter-card { position: relative; display: flex; min-height: 230px; flex-direction: column; padding: 1.15rem; border: 1px solid var(--line); border-radius: 10px; color: inherit !important; background: #fff; text-decoration: none !important; box-shadow: 0 1px 0 rgba(21, 34, 56, .02); transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease; }
.chapter-card::before { content: ''; position: absolute; inset: 0 0 auto; height: 3px; border-radius: 10px 10px 0 0; background: var(--accent); transform: scaleX(0); transform-origin: left; transition: transform .25s ease; }
.chapter-card:hover { border-color: color-mix(in srgb, var(--accent) 45%, white); box-shadow: 0 14px 36px rgba(21, 34, 56, .09); transform: translateY(-4px); }
.chapter-card:hover::before { transform: scaleX(1); }
.card-topline { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.chapter-number { color: #8a94a3; font-size: .62rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.chapter-symbol { display: grid; place-items: center; min-width: 38px; height: 30px; padding: 0 .35rem; border-radius: 6px; color: var(--accent); background: var(--accent-soft); font-family: Georgia, serif; font-size: .76rem; font-style: italic; }
.chapter-card h4 { margin: 1.5rem 0 .65rem; color: var(--ink); font-size: 1.05rem; font-weight: 700; letter-spacing: -.015em; line-height: 1.2; }
.chapter-card > p { margin: 0; color: var(--muted); font-size: .78rem; line-height: 1.55; }
.read-link { display: flex; align-items: center; gap: .4rem; margin-top: auto; padding-top: 1.1rem; color: var(--accent); font-size: .72rem; font-weight: 700; }
.read-link svg { width: 15px; transition: transform .2s ease; }
.chapter-card:hover .read-link svg { transform: translateX(3px); }
.cards-single { grid-template-columns: minmax(240px, 1fr) 2fr; }
.final-card { min-height: 200px; background: linear-gradient(135deg, #fff, color-mix(in srgb, var(--accent-soft) 52%, white)); }
@media (max-width: 960px) {
  .home-hero { grid-template-columns: 1fr minmax(310px, .75fr); min-height: 500px; gap: 2rem; }
  .stage { grid-template-columns: 52px 1fr; }
  .cards { grid-column: 2; }
  .stage-desc { max-width: 30rem; }
}
@media (max-width: 720px) {
  .home-hero { grid-template-columns: 1fr; min-height: 0; padding-top: 4.5rem; }
  .field-visual { width: min(100%, 430px); margin-top: 1rem; }
  .curriculum { padding-top: 4.5rem; }
  .curriculum-intro { display: block; }
  .curriculum-intro > p { margin-top: 1rem; }
  .cards { grid-template-columns: 1fr; }
  .cards-single { grid-template-columns: 1fr; }
  .chapter-card { min-height: 190px; }
}
@media (max-width: 480px) {
  .home-hero, .curriculum { padding-inline: 1.25rem; }
  .home-hero h1 { font-size: 3.25rem; }
  .hero-actions { align-items: flex-start; flex-direction: column; gap: 1rem; }
  .field-visual { width: 108%; margin-left: -4%; }
  .stage { grid-template-columns: 40px 1fr; gap: 1rem; }
  .stages::before { left: 19px; }
  .stage-marker span { width: 39px; height: 39px; font-size: .72rem; }
  .cards { grid-column: 1 / -1; }
}
[data-theme='dark'] .site-home { --ink: #edf3fb; --muted: #aab6c6; --paper: #1b1b1f; --line: #343b47; }
[data-theme='dark'] .field-visual { background: radial-gradient(circle at 50% 50%, rgba(96, 165, 250, .13), transparent 24%), linear-gradient(145deg, rgba(30, 58, 138, .25), rgba(30, 41, 59, .08)); }
[data-theme='dark'] .visual-core, [data-theme='dark'] .formula { background: rgba(27, 27, 31, .82); }
[data-theme='dark'] .chapter-card { background: #202126; }
[data-theme='dark'] .final-card { background: linear-gradient(135deg, #202126, rgba(120, 75, 10, .14)); }
@media (prefers-reduced-motion: reduce) {
  .start-button, .chapter-card, .chapter-card::before, .read-link svg { transition: none; }
}
</style>
