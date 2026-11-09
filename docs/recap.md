# Final Recap

This chapter follows one spend from a wallet's note to a block and names the chapter that explains each part, so that you can see how the site's pieces connect and return to whichever one you want to reread. It adds no protocol content. The derivations, the numbers, and the arguments about cheating all stay in the linked chapters.

::: warning Status of this design
Tachyon has not activated on mainnet and its design is still changing. The trace below reads Tachyon at commit [`7e50254`](https://github.com/tachyon-zcash/tachyon/tree/7e502548db33845dbaacdc0efe905d1a3c45e626) and Ragu at commit [`3219e08`](https://github.com/tachyon-zcash/ragu/tree/3219e0865e8bff1f9d817bfe3850d9e94b64338c), while Tachyon itself pins Ragu at [`0725b52`](https://github.com/tachyon-zcash/tachyon/blob/7e502548db33845dbaacdc0efe905d1a3c45e626/crates/tachyon/Cargo.toml#L74-L76). We found no real Tachyon circuits and no validator at these commits. When a sentence below says that a step checks something, it describes what the design asks for, and [Section 10](#_10-what-exists-at-the-pinned-commits) separates what exists from what does not.
:::

## 1. The spend we follow

Alice holds [a note from Bob](./notes-and-nullifiers.md#_4-notes-and-commitments), [created in epoch 3 and spent with target epoch 7](./notes-and-nullifiers.md#_6-deriving-a-note-s-nullifiers). Her bundle has one spend and [one output to Carol](./proof-tree.md#_7-outputs), and [chapter 22's run](./proof-tree.md#_2-the-running-example) carries it as far as a published stamp. All of the values live in those chapters' tables, and most of them come from stand-in hashes rather than real Poseidon outputs.

[Chapter 23](./aggregation-and-bundles.md) uses bundles of its own for its numbers. Its [bundle Y](./aggregation-and-bundles.md#_1-what-aggregation-removes-and-what-it-keeps) also has one spend and one output, so you can read Y as standing in for Alice's bundle in that chapter.

Sections 2 to 6 and Section 8 follow the spend through Tachyon. Section 7 pauses at one node of the proof tree to go through the proof system underneath it, and Section 9 collects every layer in a table.

## 2. The note reaches Alice

Alice's wallet derives [two children from its spending key](./notes-and-nullifiers.md#_2-the-spending-key-and-its-two-children), namely $\mathsf{ask}$ for authorizing spends and $\mathsf{nk}$ for deriving nullifiers. Bob needs a way to name her as the owner without learning $\mathsf{nk}$, so she gives him a [payment key](./notes-and-nullifiers.md#_3-the-payment-key), which is a hash of $\mathsf{ak}$ and $\mathsf{nk}$.

Bob then forms the [note](./notes-and-nullifiers.md#_4-notes-and-commitments) $(\mathsf{pk}, v, \psi, \mathsf{rcm})$ and its commitment $\mathsf{cm}$. Alice has to learn all four fields, and Tachyon leaves that to a [payment protocol outside the shielded protocol](./scaling-zcash.md#_7-separating-note-delivery-from-the-shielded-protocol), which is what frees her wallet from trial-decrypting all traffic. Her wallet should also [compare the note against her others](./notes-and-nullifiers.md#_9-reusing-a-trapdoor), because a sender who reuses $\psi$ can make one of her notes unspendable.

## 3. The pool records the commitment

Bob's stamp publishes $\mathsf{cm}$ as a [tachygram](./notes-and-nullifiers.md#_11-tachygrams-and-output-padding), the single kind of value that covers both commitments and nullifiers. Validators will eventually forget that tachygram, yet Alice has to prove facts about it later, so the pool keeps a short reference to it.

The stamp's tachygrams become the [roots of a polynomial](./pool-state.md#_2-encoding-a-set-as-a-polynomial), a [Pedersen commitment](./pool-state.md#_3-committing-to-the-set) shrinks that polynomial to one point, and a [Poseidon hash chain](./pool-state.md#_6-folding-stamps-into-a-hash-chain) absorbs the point together with the block's epoch. A [boundary digest](./pool-state.md#_7-crossing-epoch-boundaries) joins each epoch to the next. The chain's state is the anchor, and [chapter 22's pool history](./proof-tree.md#_2-the-running-example) lists the anchors this note lives through. A proof can witness history freely, because [one consensus check at the far end](./pool-state.md#_10-moving-a-proof-along-the-chain) pins every earlier state.

## 4. What the spend has to show

Alice's nullifiers come from a [master key $\mathsf{mk}$ and a sponge](./notes-and-nullifiers.md#_6-deriving-a-note-s-nullifiers) that gives a different value for each epoch, and [the commitment pins them](./notes-and-nullifiers.md#_8-how-the-commitment-pins-the-nullifiers), so she has no choice about their values. Validators hold only [two epochs of tachygrams](./pool-state.md#_11-the-consensus-window), which divides her double-spend obligations in two:

- She proves $\mathsf{nf}_j$ absent from epoch $j$ for each of the closed epochs 3 to 6, since validators no longer hold all of that history.
- She publishes $\mathsf{nf}_7$ and $\mathsf{nf}_8$. The spend might land in its target epoch or the next, and [publishing the pair](./notes-and-nullifiers.md#_10-why-a-spend-publishes-two-nullifiers) means that a spend accepted in epoch $a$ always puts $\mathsf{nf}_a$ into epoch $a$, where a later test will find it.

The proof makes no claim about epoch 7 itself, because the window covers it.

## 5. The sync service tests old nullifiers

Testing absence means reading whole epochs, which is the work wallets were supposed to stop doing. Alice can hand it to a service because [each epoch's value is unrelated to the others](./oblivious-sync.md#_1-the-work-a-spend-needs). She sends [explicit values and no key](./notes-and-nullifiers.md#_7-why-the-wallet-derives-its-own-nullifiers), and she has to [keep $\mathsf{nf}_7$ and $\mathsf{nf}_8$ out of every request](./oblivious-sync.md#_14-what-the-service-learns).

An epoch's polynomial is [too large to open directly](./oblivious-sync.md#_8-why-one-opening-per-epoch-needs-buckets), so a builder routes its tachygrams into [buckets by quadratic-residue profile](./oblivious-sync.md#_11-routing-an-epoch-into-buckets). Each bucket's [seal computes the crossing](./pool-state.md#_9-covering-a-whole-epoch), so that it covers the whole epoch. The service then [opens the matching bucket at the value](./oblivious-sync.md#_12-testing-a-value-against-its-bucket) and [composes the results into a segment](./oblivious-sync.md#_13-composing-segments-and-keeping-evidence), an `ArbitraryUnspent` proof that names no note.

[Chapter 22's segments](./proof-tree.md#segments-from-the-sync-service) give the service all four epochs and use one bucket per epoch to keep the numbers short, while [chapter 21's run](./oblivious-sync.md#_6-a-full-run-on-the-toy-curve) delegates a narrower range. Both are choices of example, and a wallet may run these steps itself.

## 6. The wallet builds the proof tree

Alice's wallet now combines its secrets with the service's segments, working up the tree one step at a time:

1. [`NoteSeed`](./proof-tree.md#noteseed) pairs $\mathsf{cm}$ with $\mathsf{mk}$, and [`NullifierDerive`](./proof-tree.md#nullifierderive) commits a window of (epoch, nullifier) pairs as a product of irreducible cubic factors.
2. [`UnspentBind`](./proof-tree.md#unspentbind) divides the service's polynomial out of that window, [using a factor that carries its epoch](./oblivious-sync.md#_4-putting-the-epoch-into-the-factor). This is the first point at which the service's work belongs to a note.
3. [`QrSpendableInit`](./proof-tree.md#qrspendableinit) consumes the test of epoch 3 and finds $\mathsf{cm}$ in that epoch's bucket, and [`SpendableLift`](./proof-tree.md#spendablelift) moves the lineage to the entry anchor of epoch 7.
4. [`SpendBind`](./proof-tree.md#spendbind) derives $\mathsf{nf}_7$, $\mathsf{nf}_8$, and the value commitment, and [`SpendAction`](./proof-tree.md#spendaction) derives the randomized key $\mathsf{rk}$ and builds the action and tachygram sets.
5. [`OutputBind` and `OutputAction`](./proof-tree.md#_7-outputs) create Carol's note, with the same header type and two tachygrams.
6. [`ActionLift` and `ActionMerge`](./proof-tree.md#_8-moving-and-merging-actions) bring the two actions to one anchor and combine them.
7. [`FeeFuse`](./proof-tree.md#_9-applying-the-fee) applies a fee chosen after signing, and turns `Actions` into a `Stamp` exactly once.
8. [`StampLift`](./proof-tree.md#_11-publishing-a-stamp) moves the stamp to a later anchor in epoch 7.

[The whole tree](./proof-tree.md#_13-the-whole-tree) appears in chapter 22, which flags its exact mix of steps as its own reconstruction. Two facts remain outside the proof. A [signature under $\mathsf{rk}$](./proof-tree.md#action-signatures) requires $\mathsf{ask}$, which lets a custody device hold the key while another device proves. Since no step adds up values, a [binding signature](./proof-tree.md#the-binding-signature) shows that the bundle balances.

## 7. What one fuse proves

Every node in that tree is [one call to `fuse`](./pcd-intro.md#fusing-in-ragu), which runs a step on two child proofs and emits a [header and a proof](./pcd-intro.md#_6-attaching-a-proof). Take `SpendBind` as the node, and follow what its proof has to contain.

Its step first becomes [gates and linear constraints](./arithmetization.md#_3-gates), which random powers reduce to [one consolidated equation](./arithmetization.md#_12-the-consolidated-equation). Ragu reads that equation as [one coefficient of a polynomial product](./polynomial-encoding.md#_10-the-consolidated-equation-as-a-coefficient), where a QAP would use a [quotient by a vanishing polynomial](./polynomial-encoding.md#_5-the-vanishing-polynomial-and-the-quotient). The prover [commits to its polynomials](./polynomial-commitments.md#_7-committing-to-a-polynomial), and [many evaluation claims batch into one](./batched-openings.md#_8-the-complete-protocol), which an [inner product argument](./inner-product-argument.md#_4-one-round-of-folding) can open. [Random checks and Fiat–Shamir](./statements-and-challenges.md#_8-removing-the-verifier-with-fiat–shamir) remove the interaction, and [chapter 9](./nark.md#_17-a-short-proof-from-the-same-parts) assembles these parts into one complete proof.

That proof leaves [the verifier two linear costs](./nark.md#_16-what-the-verifier-pays), computing $s(x, y)$ and computing $\hat{G}$. The node has to [verify its children inside its own circuit](./recursive-proofs.md#_2-a-proof-about-a-verifier), and [those costs block this](./recursive-proofs.md#_4-what-the-verifier-costs). So the rest of the proof system moves that work out of the circuit, along with the checks that read whole vectors:

- [Accumulation](./accumulation.md#_5-merging-two-claims) turns $\hat{G}$ into a claim that travels with the proof and merges with others, and [splitting the accumulator](./split-accumulation.md#_3-instances-and-witnesses) keeps its witness out of the circuit, so a fuse runs no inner product argument.
- [Revdot folding](./revdot-folding.md#_10-the-quotient-fold-in-ragu-s-fuse) carries the product claims forward in the same way.
- The [registry](./wiring-and-registry.md#_5-a-polynomial-for-many-circuits) replaces $s(x, y)$ with claims about one polynomial holding every circuit, so a node pays only for the step it chooses.
- The [Pasta cycle](./curve-cycles.md#_5-recursion-on-a-cycle) lets each side handle the other's points natively, [endoscalars](./endoscalars.md#_11-transcript-bridging) carry challenges across it, and [stages](./staging.md#_2-splitting-a-trace) let circuits share data.

[Chapter 18](./ragu-recursion.md#_1-what-one-fuse-has-to-do) assembles these into many small internal circuits. [Three accumulators per side](./ragu-recursion.md#_7-what-a-proof-carries-to-its-parent) pass up the tree, and each fuse replaces two of each with one, so `SpendBind`'s proof has the same shape as the proof at the top.

A proof that leaves the tree goes through [compression](./ragu-recursion.md#_8-from-a-large-proof-to-a-short-one), which replaces its polynomials with commitments and a few values and finishes with an inner product argument on each curve. Its verifier [pays the deferred linear costs once](./ragu-recursion.md#_13-what-the-verifier-pays), and [Section 14 of that chapter](./ragu-recursion.md#_14-the-size-of-the-result) gives the size.

## 8. From the stamp to a block

Alice's wallet publishes her bundle as an [autonome](./aggregation-and-bundles.md#_1-what-aggregation-removes-and-what-it-keeps). On [the wire](./aggregation-and-bundles.md#_2-the-bundle-on-the-wire), her signatures cover only effecting data, so the stamp in the trailer can change without invalidating them. A miner could include the bundle as it stands, and [a validator would rebuild its header](./proof-tree.md#_11-publishing-a-stamp) from published data.

An aggregator may instead [merge it with other stamps](./aggregation-and-bundles.md#_5-merging-stamps). The aggregator [lifts its inputs to one anchor and keeps them disjoint](./aggregation-and-bundles.md#_10-the-aggregator-s-role), and it needs none of Alice's secrets, because [its steps read only commitments and published values](./proof-tree.md#_12-the-aggregator-s-steps). If a block mines one of the inputs first, [`StampUnmerge` divides it out](./aggregation-and-bundles.md#_11-when-a-block-lands).

A miner then [strips each covered bundle](./aggregation-and-bundles.md#_6-stripping), so Alice's bundle keeps its body and fee and gains a pointer to the aggregate's `wtxid`. Its [`txid` half stays stable](./aggregation-and-bundles.md#_7-transaction-identifiers) through all of this, so her wallet can still recognize it.

The block's validators then run the [checks on the aggregate](./aggregation-and-bundles.md#verifying-a-block-s-aggregate), covering signatures, pointers, coverage, the tachygram count, the set commitment, and the proof. They also run the [consensus rules](./pool-state.md#_11-the-consensus-window), which look up the anchor, require its epoch to be current or preceding, check each tachygram against the window, and absorb the commitment into the chain. Finding the anchor [closes the free witnesses below it](./proof-tree.md#_11-publishing-a-stamp).

Alice's $\mathsf{nf}_7$ and $\mathsf{nf}_8$ are now in the pool, and a second spend of this note runs into [either the window or the exclusion proof](./notes-and-nullifiers.md#_10-why-a-spend-publishes-two-nullifiers).

::: warning Reconstructed from code at commit 7e50254, not confirmed by the authors
The crate has no block validator, so this sequence combines `Bundle::verify` with consensus rules from the book. [Chapter 23](./aggregation-and-bundles.md#_13-why-cheating-fails) and [chapter 20](./pool-state.md#_11-the-consensus-window) both note that this is a reading of the sources, and that no source fixes the full order.
:::

## 9. The layers and their chapters

The table lists the layers in the order that the trace meets them.

| Layer | What it gives Alice's spend | Chapter |
| --- | --- | --- |
| Motivation | why state and scanning have to shrink | [1, Scaling Zcash](./scaling-zcash.md) |
| Keys, notes, nullifiers | the objects and their derivations | [19, Notes, Nullifiers, and Tachygrams](./notes-and-nullifiers.md) |
| Pool state | a short reference to forgotten history | [20, Pool State and Anchors](./pool-state.md) |
| Absence evidence | epochs tested by a party who does not know the note | [21, Oblivious Sync](./oblivious-sync.md) |
| Proof tree | the steps from note to stamp | [22, The Proof Tree](./proof-tree.md) |
| PCD model | header and proof at every node | [2, An Introduction to Proof-Carrying Data](./pcd-intro.md) |
| Circuit | a step written as one equation | [4, Arithmetization](./arithmetization.md) |
| Encoding | that equation as a polynomial test | [5, QAP and Polynomial Encoding](./polynomial-encoding.md) |
| Commitments | one point per polynomial | [6, Polynomial Commitments](./polynomial-commitments.md) |
| Batching | one claim in place of many | [8, Batched Openings](./batched-openings.md) |
| Opening | a short evaluation proof | [7, The Inner Product Argument](./inner-product-argument.md) |
| Challenges | small checks that stand for large ones | [3, Statements and Challenges](./statements-and-challenges.md) |
| Complete proof | the parts assembled, with two linear costs left | [9, The Complete Proof](./nark.md) |
| Recursion | a proof that its children verify | [10, Recursive Proofs](./recursive-proofs.md) |
| Deferred checks | $\hat{G}$ carried as a claim | [11, Accumulation](./accumulation.md) and [12, Split Accumulation](./split-accumulation.md) |
| Product claims | many revdot claims folded to one | [14, Revdot Folding](./revdot-folding.md) |
| Wiring | any registered step, at fixed recursive cost | [15, Wiring and the Registry](./wiring-and-registry.md) |
| Two fields | points handled on the other curve | [13, Curve Cycles](./curve-cycles.md) |
| Crossing challenges | one short string serving both curves | [16, Endoscalars](./endoscalars.md) |
| Shared witness | circuits reading the same stage | [17, Staging](./staging.md) |
| Assembled fuse | the node's circuits, and compression | [18, Recursion in Ragu](./ragu-recursion.md) |
| Bundle to block | fees, merging, stripping, block checks | [23, Aggregation and Bundles](./aggregation-and-bundles.md) |

## 10. What exists at the pinned commits

The trace reads as one working system, but its parts have very different status, and each chapter's warnings give the details.

**What we read as code.** Ragu at `3219e08` contains `fuse`, `compress`, and their verifiers, although [we did not build or run it](./ragu-recursion.md) or run its benchmarks. The Tachyon crate contains the [proof steps, written as native step bodies](./proof-tree.md#_1-steps-headers-and-parties), the fold functions, the wire format, and a [`Bundle::verify`](./aggregation-and-bundles.md#verifying-a-block-s-aggregate) for one covering bundle.

**What the sources describe and we did not find in code.**

- No real Tachyon circuits. The crate [builds against a mock of Ragu](./proof-tree.md) at `0725b52`, whose `fuse` runs a step natively, discards the polynomial openings, and does not verify child proofs.
- No validator and no mempool. The [window and the anchor lookup](./pool-state.md) appear only in the book and in doc comments, and [block assembly and transaction-level balance](./aggregation-and-bundles.md) appear only in the book and in tests.
- No normative specification. The [shielded protocol](./notes-and-nullifiers.md), [accumulator](./pool-state.md), [syncing service](./oblivious-sync.md), and [bundle and aggregator](./aggregation-and-bundles.md) ZIPs are empty outlines.
- No [wallet check for reused trapdoors](./notes-and-nullifiers.md#_9-reusing-a-trapdoor) in the crate.

**What remains open in the design.**

- [Zero knowledge and unlinkability](./ragu-recursion.md#_16-rerandomization-and-zero-knowledge) are not yet established, although the Tachyon book assumes them.
- [Decompression](./aggregation-and-bundles.md#decompression) has not landed, so a compressed proof cannot be fused today, and an aggregator's real costs are unknown.
- The sources differ on [which anchors consensus accepts and where the crossing sits](./pool-state.md#_8-end-of-block-anchors).
- [Service privacy measures](./oblivious-sync.md#_14-what-the-service-learns), [fee levels and aggregator payment](./aggregation-and-bundles.md#_12-fee-levels-and-payment), and [per-note proving delegation](./notes-and-nullifiers.md#_3-the-payment-key) are unspecified or unsettled.
- The [comparison with Orchard](./ragu-recursion.md#_17-performance-against-orchard) is an estimate, and [real proof size](./aggregation-and-bundles.md#_9-what-aggregation-saves) is not settled for Tachyon.

## 11. Where this chapter leaves us

This chapter took the following steps:

1. A note enters the pool as a tachygram, and the pool refers to it through a polynomial commitment absorbed into a hash chain.
2. A spend proves absence for closed epochs, with help from a service that does not know the note, and it publishes a nullifier pair for the window to check.
3. Each step of the wallet's tree is one fuse, and Ragu's accumulators keep the proof the same shape at every depth.
4. A stamp can pass through an aggregator and a miner without disturbing what Alice signed, and validators check the result against the anchor chain.
5. All of this is a design at fixed commits, with mock proofs on the Tachyon side and no validator, and any later commit may differ.

This is the last chapter. The [glossary](./appendix-glossary.md), the [notation page](./appendix-notation.md), and the [curves appendix](./appendix-curves.md) remain as references.
