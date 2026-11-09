# PoC — alias de posición en el árbol de notas de Iron Fish

Demuestra que una nota insertada en el árbol de compromisos autentica en **varias
posiciones distintas contra la misma raíz**, y que cada posición produce un
**nullifier distinto**. El circuito de spend usa los mismos bits de dirección del
auth path para (a) ordenar el hash y (b) derivar el nullifier, y no recibe el
tamaño del árbol como input público, así que la segunda posición es un spend
válido de la misma nota.

## Ficheros

| Fichero | Contenido |
|---|---|
| `merkle_alias_poc.py` | Modelo del árbol (regla desplegada vs regla del fix), alias, nullifiers, balance de valor |
| `live-state.md` | Anclaje del estado live: cadena, oferta, wIRON en Base, pools, releases |
| `../foundation-repos-manifest.tsv` | Manifiesto de los 48 repos de la org con commit exacto |
| `../REPORT.md` | Reporte de auditoría |

## Ejecutar

```bash
python3 merkle_alias_poc.py --selftest
python3 merkle_alias_poc.py --demo --leaves 60000 --position 59999
```

Sin dependencias externas (sólo stdlib).

## Qué prueba el selftest

El modelo reproduce **exactamente** los vectores que el repo tiene hardcodeados en
sus tests, para las dos versiones del código:

| Vector | v2.12.0 (desplegada) | master (fix `c5c3c22b`) |
|---|---|---|
| depth 3, 3 hojas | `<<<a|b-0>\|<c\|c-0>-1>\|<<a\|b-0>\|<c\|c-0>-1>-2>` | `<<<a|b-0>\|<c\|~-0>-1>\|~-2>` |
| `pastRoot(13)` | `…\|<<8\|8-0>\|<8\|8-0>-1>-2>-3>` | `…\|<<8\|~-0>\|~-1>-2>-3>` |

La diferencia es exactamente la que explota el ataque: en la versión desplegada el
sibling ausente es **la propia rama** (auto-copia), en el fix es un valor vacío fijo.

Referencias:
`ironfish/src/merkletree/merkletree.ts` líneas 520/533/543/561 (pastRoot) y
712-714/723-724/743-744 (witness) en `v2.12.0`
(`git show v2.12.0:ironfish/src/merkletree/merkletree.ts`).

## Qué prueba el demo

- `self-copy (free) levels`: niveles del auth path cuyo sibling es el propio nodo →
  el bit de dirección puede invertirse sin cambiar la raíz.
- `distinct positions`: 2^niveles libres. Medido al tamaño real del árbol de
  mainnet (`--leaves 1864830 --position 1864829`, `depthAtLeafCount = 22`):
  **19 niveles libres ⇒ 524.288 posiciones**. Una nota "no borde" conserva al
  menos los 10 niveles superiores ⇒ ≥1.024. Una nota en el borde derecho de un
  árbol pequeño obtiene más (21 niveles libres con 60.000 hojas ⇒ 2^21).
- Cada alias recomputa **la misma raíz** ⇒ pasa `Verifier.verifySpend`
  (`pastRoot(spend.size) == spend.commitment`, `verifier.ts:482-500`).
- Los nullifiers son todos distintos ⇒ `NullifierSet` no detecta reuso.
- `value_accounting`: N spends de la misma nota de valor V + N notas de salida de
  valor V dejan el balance en `-fee`, que es exactamente lo que exige
  `calculate_value_balance` (`ironfish-rust/src/transaction/mod.rs`). El resultado
  es V falsificado × (N−1), y **compone**: cada nota nueva vuelve a tener N alias.

## Por qué no se incluye aquí una prueba con proof Groth16

Requiere construir `@ironfish/rust-nodejs` (toolchain Rust) y usar los parámetros
de `mainnet-parameters/params`. Esa prueba **ya existe en el repo** y la añadió el
propio fix: `ironfish/src/merkletree/positionProof.test.slow.ts`. Construye dos
spends de la misma nota con nullifiers distintos, ambos aceptados por el verifier
de proofs; en el código con fix se rechazan sólo porque su anchor auto-copiado ya
no coincide con `pastRoot` — es decir, en `v2.12.0` sí coincidía.

## Alcance / límites

- El atacante **no** puede gastar notas de terceros: necesita la spending key
  (nullifier key) de la nota. El ataque es **falsificación** (inflación del nativo),
  no robo directo de notas ajenas.
- El beneficio se realiza contra inventario ajeno (pools/bridge/exchanges). Ver
  `live-state.md` §2-3 para lo medido.
