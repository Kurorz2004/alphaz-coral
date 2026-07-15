# CORAL patches — Tasks 3–4

Upstream: https://github.com/Human-Agent-Society/CORAL.git
Base commit: `c535d91a3118669a2ca46dfd6dc0fa447c17b03a` (merge-base of this
work with upstream `main`).

17 patches, generated with `git format-patch` against that base.

## Apply

```
git clone https://github.com/Human-Agent-Society/CORAL.git
cd CORAL
git checkout c535d91a3118669a2ca46dfd6dc0fa447c17b03a
git am ../coral-patches/*.patch
```

Verified clean (`git am`, 17/17 applied, no conflicts) against a fresh clone
of the base commit.

The same series is published on the fork's `task4-llm-consolidation` branch:
https://github.com/Kurorz2004/CORAL/tree/task4-llm-consolidation.
