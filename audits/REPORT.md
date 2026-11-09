# Auditoría Iron Fish (iron-fish) — reporte final

**Fecha de anclaje:** 2026-11-09 (UTC)
**Branch de trabajo:** `arena/f1650a31-ironfish`
**Fuente de verdad:** clones locales de los 48 repos de la org `iron-fish` + estado live leído por API pública/explorer/pool/minería.

---

## 1. Veredicto

**1 crítico live y ya ejecutado:** inflation arbitraria del activo nativo IRON por *alias de posición* en el árbol de compromisos de notas (Merkle), que produce nullifiers distintos para una misma nota y permite gastarla N veces.

- ¿Vulnerable ahora? **Sí en código y en red viva** (nodo 2.12.0, la release desplegada; la cadena sigue produciendo bloques PoW). No existe parche desplegado ni desplegable sin una actualización de consenso: el fix disponible cambia las raíces y sólo sirve para una cadena nueva (el propio repo lo declara y sólo regeneró el génesis de **devnet**); la alternativa (acotar la posición en el circuito) exige nuevos parámetros Groth16 y una activación por altura que no existe.
- ¿Drena terceros? **Sí.** El valor falsificado se realiza contra inventario ajeno: pools DEX en Base vía wIRON/ChainPort (lado USDC ya vaciado), compradores de wIRON y el libro IRON/USDT de Gate (único mercado vivo hoy).
- Magnitud medida: **2.787.953.680 wIRON** en Base frente a **76.993.394,75 IRON** reales (36,2× la oferta total de la cadena).

Detalle completo en la sección 4. Estado del requisito previo de clonado en la sección 2.

---

## 2. REQUISITO PREVIO OBLIGATORIO — estado

### 2.1 Orgs/espacios de la fundación

| Espacio | Resultado |
|---|---|
| GitHub `iron-fish` | **Org canónica.** 48 repos, todos públicos (`private=false`, 0 archivados visibles). Todos clonados. |
| GitHub `ironfish`, `iron-fish-labs`, `ironfishfoundation`, `IronFishFoundation`, `ironfish-network` | 404 (no existen). |
| GitLab (búsqueda de grupos "iron fish") | 0 resultados (`gitlab.com/api/v4/groups?search=iron fish`). |
| Bitbucket | Sin evidencia de espacio propio. Todos los `repository.url` de los paquetes (17/17 detectados en `package.json`/`Cargo.toml`) apuntan a `github.com/iron-fish/*`. |

### 2.2 Clonado

- Destino: `/tmp/foundation-repos/github/<repo>` (fuera del árbol de trabajo para no inflar el snapshot; 638 MB).
- Comando: `git clone --filter=blob:none --no-single-branch --tags https://github.com/iron-fish/<repo>.git` + `git fetch --tags --all`, sobre la lista completa de `orgs/iron-fish/repos?type=all` (paginado).
- **48/48 repos clonados.** Manifiesto con commit exacto por repo: [`audits/foundation-repos-manifest.tsv`](./foundation-repos-manifest.tsv).
- **Submodules:** ninguno (`0` repos con `.gitmodules`).
- **Git LFS:** ninguno (`git lfs ls-files` = 0 en los 48).
- **Repos bloqueados:** ninguno de los 48 públicos. **Limitación declarada:** el token de este entorno no ve repos privados de la org; si `iron-fish` mantiene repos privados, no están cubiertos → la cobertura no se declara completa respecto de material privado.

### 2.3 Commits usados (los que importan para el hallazgo)

| Rol | Repo | Commit | Fecha |
|---|---|---|---|
| **Release desplegada en mainnet** (tag `v2.12.0`, npm `@ironfish/sdk@2.12.0`) | `iron-fish/ironfish` | `b442f9b51a60bbb466b9e5cfbc859923b639161d` | 2025-08-12 |
| **Fix del bug** (sin tag, sin release, no desplegable en mainnet) | `iron-fish/ironfish` | `c5c3c22bfc26dbf40a26c58ffee3181bef6cef5e` | 2026-10-29 |
| HEAD de `master` al auditar | `iron-fish/ironfish` | `c5c3c22b…` (= v2.12.0 + 3 commits) | 2026-10-29 |
| API/explorer públicos | `iron-fish/ironfish-api` | `59570feb4577` | 2025-07-10 |
| CLI (puente ChainPort) | `iron-fish/ironfish` (`ironfish-cli/src/utils/chainport`) | `b442f9b5…` | 2025-08-12 |

`git rev-list --count v2.12.0..HEAD` = **3** → todo lo que corre en mainnet está contenido en `v2.12.0`; el fix es posterior y **no está en ninguna release** (`gh api repos/iron-fish/ironfish/releases` → última `v2.12.0`, 2025-08-12; npm `latest` = `2.12.0`).

### 2.4 Mapa componente/artefacto → repo + commit

| Componente live | Identificador | Repo / ruta | Commit/artefacto |
|---|---|---|---|
| Cadena mainnet | `network id 1`; génesis: secuencia 1, timestamp 1682006400000, graffiti `genesis`, `noteSize` 75, `genesisSupplyInIron` 42.000.000, hash **no literal en el repo** (se deriva de `MAINNET_GENESIS.header`); checkpoint hardfork-1 = altura **503.338**, hash `00000000000045885508f3c1455d676fe8749433dc71a748d07719fdde39aeb2` | `ironfish/src/networks/definitions/mainnet.ts:9-45` | `b442f9b5…` |
| Activo nativo IRON (asset id) | `51f33a2f14f92735e562dc658a5639279ddca3d5079a6d1242b2a588a9cbf44c` | `ironfish-rust/src/assets/asset_identifier.rs:10` | `b442f9b5…` |
| Árbol de notas (consenso) | `MerkleTree{depth:32, defaultValue: Buffer.alloc(32), name:'n'}` | `ironfish/src/blockchain/blockchain.ts:186` | `b442f9b5…` |
| Verificación de spend | `Verifier.verifySpend` → `chain.notes.pastRoot(spend.size)` | `ironfish/src/consensus/verifier.ts:482-500` | `b442f9b5…` |
| Nullifier | `Note::nullifier(nk, position)` | `ironfish-rust/src/note.rs:305` | `b442f9b5…` |
| Circuito spend (posiciones) | `position_bits` desde los bits del auth path | `ironfish-zkp/src/circuits/spend.rs:346-366,421-433` | `b442f9b5…` |
| Parámetros Groth16 mainnet (spend/output/mint) | trusted setup 2870 contribuciones | `mainnet-parameters/params`, `ironfish-mpc` | `b442f9b5…` (sin cambios en el fix) |
| Puente (dirección de depósito en Iron Fish / fee memo) | `GET /bridges/transactions/create` → `bridge_output.publicAddress` | `ironfish-cli/src/utils/chainport/send.ts`, `ironfish-cli/src/utils/chainport/{metadata,requests,types}.ts` | `b442f9b5…` (fee V2, PR #5755) |
| USDC puenteado en Iron Fish (ChainPort) | asset id `8e36e31d677a47cbd883843a345654c814b1e9ec1e0125bac9031f052ced9174`, chainport network 22 | `ironfish-api` `/bridges/tokens` | `59570feb…` |
| wIRON en Base (lado EVM del puente, **tercero**) | `0x166E70941262AE7CbF9df5C8897a6242c546457D` (TransparentUpgradeableProxy, 8 dec.) | No está en `iron-fish/*`: token de ChainPort | Verificado en Base vía Blockscout (2026-11-09) |
| Pool DEX tercero que absorbía wIRON | Aerodrome Volatile AMM wIRON/USDC `0x9941dfa4d724fd7a2E5E5d9777560b20de98cE0d` | externo | ídem |

---

## 3. Anclaje del estado live (2026-11-09)

| Dato | Valor | Fuente |
|---|---|---|
| Altura de cadena | **1.876.236**, bloques encontrados "hace menos de un minuto", 38,78 GH/s, 94 mineros, dificultad 2,33 TH | `ironfish.herominers.com` |
| Corroboración de cadena viva | herominers último bloque **1.876.248** (hace 4 min), kryptex **1.876.235** (hace 15 min), tw-pool **1.876.112** (hace 2 h); reparto de 1000 bloques 54,8/32,7/0,5/12 % | `miningpoolstats.stream/ironfish` |
| Altura indexada (API/explorer) | 1.864.830, timestamp 2026-10-31T22:43:40Z — **índice congelado**, no la cadena | `api.ironfish.network/blocks/head`, `explorer.ironfish.network` |
| Oferta total / circulante IRON | **76.993.394,75** (ambas) | `api.ironfish.network/supply/{total,circulating}` |
| Versión de nodo | **2.12.0** | explorer (cabecera "Node 2.12.0"), `GET /versions`, release GitHub `v2.12.0` |
| Mercado IRON | Gate IRON/USDT, último trade 2026-11-09T00:56Z, precio 0,008718, volumen 24h **1.841 USD**, mcap **670.608 USD** | CoinGecko `/coins/iron-fish/tickers` |
| wIRON en Base | `total_supply = 278.795.368.000.099.518` (8 dec.) = **2.787.953.680,00099518** | Blockscout Base `/api/v2/tokens/0x166E…457D` |
| Pool Aerodrome wIRON/USDC | **118,748231 USDC** vs **269.086.975,19 wIRON** | Blockscout Base `/api/v2/addresses/0x9941…/token-balances` |
| Uniswap V4 PoolManager (Base) | **917.509.833,43 wIRON** | Blockscout Base (holders) |

Nota: el índice público dejó de actualizarse el 2026-10-31, el mismo día del anuncio de fin de soporte. La cadena **no** está detenida: es PoW y sigue minándose (hero miners con bloques cada ~70 s y dificultad ajustada a la baja). Esto es relevante: la red es permissionless *hoy*, no sólo hasta el anuncio.

---

## 4. HALLAZGO CRÍTICO

### 4.1 Qué es

El árbol de compromisos de notas rellenaba una rama derecha ausente **copiando su rama izquierda** (`H(left,left)`) y ponía esa misma copia como *sibling* en el witness. Al ser ambos hijos iguales, intercambiar el orden no cambia el padre → el bit de dirección de ese nivel (que el circuito usa **a la vez** para el orden del hash y para la posición) puede invertirse sin cambiar la raíz. La posición privada entra en `rho = cm + position·G` y por tanto en el nullifier → **dos nullifiers válidos para la misma nota**.

### 4.2 Código exacto (release desplegada `v2.12.0`)

`ironfish/src/merkletree/merkletree.ts` — relleno por auto-copia:

```
520:  const rootDepth = depthAtLeafCount(pastSize)          // pastRoot
533:  currentHash = combineHash(0, currentHash, currentHash)   // sibling ausente = sí mismo
543:  currentHash = combineHash(depth, currentHash, currentHash)
…     561: idem en el bucle superior hasta depth 32
712:  authenticationPath.push({ side: Side.Left, hashOfSibling: currentHash })
713:  currentHash = combineHash(0, currentHash, currentHash)   // witness
723/724, 743/744: idem por nivel
716:  const rootDepth = Math.min(depthAtLeafCount(witnessLeafCount), this.depth)
```

Cadena de validación (nada de esto compara la posición con el tamaño):

```
ironfish/src/consensus/verifier.ts:482-500
    if (spend.size > notesSize) return NOTE_COMMITMENT_SIZE_TOO_LARGE
    const realSpendRoot = await this.chain.notes.pastRoot(spend.size, tx)
    if (!spend.commitment.equals(realSpendRoot)) return INVALID_SPEND
```

```
ironfish-rust/src/transaction/spends.rs:370-382   // public inputs del spend
    [0,1] = randomized_public_key ; [2,3] = value_commitment ; [4] = root_hash ; [5,6] = nullifier
```

No hay `size` ni `position` entre los 7 inputs públicos: el tamaño sólo se **firma** (`serialize_signature_fields`), no se prueba.

```
ironfish-zkp/src/circuits/spend.rs:346-366
    // los bits de dirección del auth path SON la posición
    let cur_is_right = Boolean::alloc(... e.1 ...); position_bits.push(cur_is_right.clone());
    conditional_reverse(&cur, &path_element, &cur_is_right)      // orden del hash
421-433:  let position = fixed_base_multiplication(g^position, &position_bits);
          rho = rho.add("faerie gold prevention", &position)
```

```
ironfish-rust/src/note.rs:305
    rho = cm + position·G ;  nf = BLAKE2s(personal="ironf_nf", nk ‖ rho)
```

`G` tiene orden primo r ≈ 2^252 y la posición es de 32 bits ⇒ `position·G` es inyectiva ⇒ posiciones distintas dan `rho` distinto ⇒ nullifiers distintos.

### 4.3 Por qué los 4 criterios se cumplen

1. **Bug concreto en código que corre live:** líneas anteriores, en `v2.12.0` (release y npm vigentes). El fix `c5c3c22b` es posterior, sin release, y **explícitamente inaplicable**: el README del propio repo (añadido por el fix) dice que cambia las raíces de consenso y sólo sirve para una cadena nueva; el commit sólo regenera el génesis de **devnet**, no toca `mainnet.ts`/`testnet.ts`. No hay activación por altura ni verificador dual.
2. **Permissionless:** sólo hace falta poseer *una* nota (cualquier usuario; comprar 1 IRON o minar), la spending key propia y el proving key público (incluido en `mainnet-parameters/params`). Sin rol, sin admin, sin governance. Todo con transacciones normales.
3. **Call graph/estado live:** el árbol de `blockchain.ts:186` es el árbol de notas real; `verifier.verifySpend` es el gate de mainnet; el circuito y los parámetros son los desplegados (el fix no los toca). El `spend.size` puede ser **cualquier tamaño histórico ≤ tamaño actual**, así que el atacante elige el momento en que su nota estaba en un árbol pequeño (más niveles auto-copiados ⇒ más alias).
4. **PnL:** ver 4.5. El atacante mete 1 nota de valor V y saca N notas de valor V (N = nº de alias), con balance de valor intacto porque cada spend aporta su propio `value_commitment` de V.

### 4.4 PoC

- [`audits/ironfish-merkle-alias/merkle_alias_poc.py`](./ironfish-merkle-alias/merkle_alias_poc.py) — reimplementación en Python del árbol **tal como lo hace el nodo**, con doble validación:
  - `--selftest` reproduce **exactamente** los vectores publicados en los tests de `v2.12.0` (auto-copia: `'<<<a|b-0>|<c|c-0>-1>|<<a|b-0>|<c|c-0>-1>-2>'`, `pastRoot(13)` con `<<8|8-0>|<8|8-0>-1>`) **y** los del código con fix (`'<<<a|b-0>|<c|~-0>-1>|~-2>'`, `pastRoot(13)` con `<<8|~-0>|~-1>`). Pasa.
  - `--demo` construye un árbol depth-32, calcula el witness real de una hoja, enumera los niveles auto-copiados, genera posiciones alias, verifica que **todas recomputan la misma raíz** y que los nullifiers difieren; después simula el balance de valor de la transacción.
- Prueba end-to-end con **proofs reales** ya incluida en el repo (la aporta el propio fix): `ironfish/src/merkletree/positionProof.test.slow.ts` construye dos spends de la misma nota con nullifiers distintos, ambos satisfacen el verifier de proofs, y en el código con fix son rechazados sólo porque su anchor (raíz auto-copiada) ya no coincide con `pastRoot` — es decir, en `v2.12.0` **sí** coincidía.

Salida a **tamaño real de mainnet** (`--leaves 1864830 --position 1864829`):

```
tree size              : 1864830
depthAtLeafCount(size) : 22
leaf real position     : 1864829
self-copy (free) levels: [1,7,8,9,11,15,16,17,21,22,23,24,25,26,27,28,29,30,31]
distinct positions     : 524288
aliases verified       : 1023 (all reuse the same root)   # enumeración capada a 1024
distinct alias nullifs : 1023 / 1023
nullifier(real pos)    : 1bac6da2…
nullifier(alias pos)   : 77d747cc…
```

(También validado a 60.000 hojas: 21 niveles libres, 2.097.152 posiciones.)

### 4.5 Números live y capacidad de mint

- Medido al tamaño real del árbol de mainnet (`S = 1.864.830`, `depthAtLeafCount = 22`), con la hoja en el borde derecho (`position = 1.864.829`):
  **19 niveles auto-copiados ⇒ 524.288 posiciones distintas**, todas recomputando la misma raíz, todas con nullifier distinto (PoC, 7,9 s de ejecución). Una nota "no borde" conserva al menos los 10 niveles superiores ⇒ ≥1.024 posiciones. Las notas viejas (posición pequeña, `size = posición+1`) tienen más alias aún.
- **Compone multiplicativamente:** ronda 1: 1 nota de V → hasta 524.288 notas de V; ronda 2: ~2,7×10^11 × V. Sólo limita el espacio de bloque (`maxBlockSizeBytes`) y el nº de spends por tx.
- Inflación efectiva: **sin cota** (la cadena shielded no tiene chequeo de oferta agregada; sólo balances por transacción).

Inventario ajeno medido:

| Inventario | Valor medido | Comentario |
|---|---|---|
| Oferta IRON (todos los holders) | 76.993.394,75 IRON ≈ **670.608 USD** (mcap CoinGecko) | diluible al 100% |
| wIRON en Base (ChainPort) | **2.787.953.680** wIRON = **36,2×** la oferta real | 2.710.960.285 wIRON sin respaldo |
| Pool Aerodrome wIRON/USDC | 118,75 USDC vs 269,09 M wIRON | lado USDC ya vaciado; el residuo es wIRON basura |
| Uniswap V4 PoolManager (Base) | 917,5 M wIRON | ídem |
| Gate IRON/USDT (único mercado vivo) | volumen 24h **1.841 USD** | libro y MM de Gate = delta realizable hoy |

**Estimación honesta de lo tocable hoy:** el mint es ilimitado, pero la realización está acotada por la profundidad de los venues supervivientes: ~10^4 USD (libro de Gate, mcap 0,67 M USD) más OTC. **Lo ya realizado** (2026-10-27) fue a costa de liquidez de terceros en Base y compradores de wIRON; la prueba on-chain es la oferta de wIRON (2,788 mil millones) contra 76,99 M de IRON. La prensa cifra el daño en ~675 k USD, pero ese artículo mezcla el incidente de SAND/LayerZero, así que **no** uso esa cifra como hecho.

### 4.6 ¿Qué mataría el claim? (descartado explícitamente)

- Que la posición estuviera acotada por `size` en el circuito → **no**: los 7 public inputs son `{pk_r, cv, root, nf}`; `size` sólo se firma.
- Que el validador recompute la raíz con regla nueva → **no** en `v2.12.0`; `pastRoot` usa auto-copia.
- Que el doble nullifier se detecte → no, son bytes distintos; `NullifierSet` sólo compara bytes.
- Que el balance de valor lo impida → no: cada spend expone su propio `value_commitment`; `ValueBalances` suma por spend.
- Que el atacante necesite rol → no.
- Que sea dust/irrealizable → no: 1.024–2^21 alias por nota y composición multiplicativa; el propio equipo confirmó explotación real (2.788 B wIRON).

### 4.7 Límites de la evidencia

- No pude **rebuildear** `@ironfish/rust-nodejs` (no hay toolchain Rust en el sandbox), así que el PoC con proofs reales es el test del propio repo; la reproducción independiente cubre la aritmética del árbol (validada contra los vectores del código desplegado) y el álgebra de nullifiers/valores.
- El índice público está congelado en 1.864.830; la altura 1.876.236 viene del pool de minería. No pude leer `noteSize` exacto del header (la API no lo expone), por eso uso la cota inferior `≥ nº de bloques`.
- La atribución de un spend histórico concreto al mecanismo no es posible desde fuera (la posición es privada); el repo también lo deja abierto. Lo que sí es concluyente es el código, la mecánica y la oferta de wIRON.

---

## 5. Otros caminos revisados y descartados (no críticos)

| Camino | Resultado |
|---|---|
| Recompensa de bloque / miner fee (`verifier.ts:47-160`) | Chequeo exacto: `minersFee.fee() === -(miningReward(seq) + Σfees)`, fees ≥ `minFee` y ≥ 0. Sin inflación. |
| Mints de assets (`verifyMintOwnersIncremental`, `verifier.ts:595-680`) | Owner debe ser creador/owner actual; transferencia explícita. No permite acuñar el nativo. |
| Burns (`verifyBurns`) | `NATIVE_BURN` rechazado. |
| Balance de valor (`ironfish-rust/src/transaction/mod.rs`, `value_balances.rs`) | `ValueBalances` sólo se usa al **construir** la tx (`proposed.rs`); en verificación la conservación la impone la firma de binding (§5.1). Correcto. |
| Notas de valor 0 y anchor libre (`spend.rs`: `(cur − rt)·value = 0`) | Bypass real del chequeo de raíz **sólo** para valor 0 ⇒ no aporta valor; heredado del diseño Sapling. No crítico. |
| Resto del parche Merkle (índice de duplicados tras `truncate`, contadores u32, `depth` inválido, caché de pastRoot) | Estado local del nodo/reorg; sin delta de valor ajeno. |
| DEX/contratos en Iron Fish | La L1 no tiene smart contracts; no hay pools ni vaults on-chain de IRON. El único inventario ajeno on-chain en Iron Fish es USDC puenteado de ChainPort (no comprable con IRON: no hay mercado). |
| Faucet / testnet | Sin TVL relevante. |

### 5.1 Segundo barrido (auth de mints, conservación de valor, generadores, cabecera/dificultad)

Pasada adicional sobre los caminos restantes de `v2.12.0`. **No produce ningún crítico**; se documenta el porqué de cada uno para que el descarte sea verificable.

| Camino | Qué se comprobó (código) | Hecho que lo mata |
|---|---|---|
| Acuñar un asset existente (p.ej. el USDC puenteado `8e36e31d…`) | `mints.rs:225-316` (4 public inputs: `rk`,`owner`), `MintDescription::verify_signature` (RedDSA sobre `rk‖hash`), `verifier.ts:595-680` (`owner` = creador o owner en cadena) | El proof de mint acredita conocimiento de la clave de `owner` y la firma cubre el hash de la tx; cambiar `owner` invalida el proof. `enableAssetOwnership: null` en mainnet sólo fija **V1**, y V1 **no puede serializar** `transfer_ownership_to` (`mints.rs:308-345`, `version.rs:60-63`): no hay robo de propiedad. El chequeo de owner es incondicional en `verifyBlockConnect`, no depende de ese flag. |
| Colisión de `asset id` / usar el generador nativo | `verify_valid_asset` recalcula `id = blake2s(creator‖name‖metadata‖nonce)` **dentro** del circuito de mint | Para que el balance use el generador nativo haría falta una preimagen del id nativo; si el campo `id` ≠ recalculado, el `cv` del proof usa otro generador y la firma de binding no verifica. |
| Conservación de valor, fee, mints y burns | `transaction/mod.rs:240-350`: `bvk = Σcv_spend − Σcv_output`; `calculate_value_balance` resta `fee·G` y suma/resta mints/burns; `verify_binding_signature` exige RedDSA con base `R` sobre ese punto | La firma sólo existe si el atacante conoce el dlog del punto; los términos de valor se cancelan únicamente si cada asset suma 0 neto (generadores hash-to-curve independientes). `fee_to_point` rechaza `i64::MIN`. Verificado que mints/burns **no** se cuentan dos veces (no están en `bvk`). |
| Generador de asset en el lado spend (`assert_valid_asset_generator` sólo en `output.rs:236`) | `spend.rs:265-300,346-372`: el circuito testifica `cv.asset_generator`, lo incluye en `note_contents`, deriva `cm` y arranca el auth path en `cm.get_u()` | No falta restricción: en un spend no hay campo `asset_id`. El asset queda fijado por el camino de Merkle (§4); cambiar el generador cambia `cm` y rompe el ancla. El chequeo explícito sólo hace falta donde se **crea** un id (output/mint). |
| Manipular `noteSize` para forzar raíces viejas | `blockheader.ts:196-210` (`serialize()` = 180 B, sin `noteSize` ni `work`); `blockchain.ts:1262-1285` (`prevNotesSize` debe igualar el tamaño real) | `noteSize`/`work` no se transmiten ni entran en el hash: cada nodo los deriva (`prev + counts().notes`). No es un campo elegible por el minero. |
| Time-warp / bajar dificultad | `mainnet.ts:10-20` (`allowedBlockFutureSeconds: 15`, bucket 10 s), `verifier.ts:172-236`, `target.ts:70-115` | Timestamp ≤ `now+15 s` y estrictamente creciente desde la altura 503.338; ajuste de ±1/2048 por bucket ⇒ como máximo ~0,1 % de dificultad por bloque. No hay colapso. |
| Checkpoints | `mainnet.ts:21-26`, `blockchain.ts:288-297,546-547,761` | Único checkpoint = altura **503.338**, hash `0000000000004588…`; sólo bloquea reorgs por debajo (`CHECKPOINT_REORG`). **Corrección de un dato previo de este informe: ese hash es el checkpoint de hardfork-1, no el génesis** (el hash del génesis no está literal en el repo). |
| Mempool | `verifier.ts:243-300` | No valida `root` ni duplicados intra-tx, pero el bloque sí (`verifyConnectedBlock` + `verifyInternalNullifiers`). Sólo spam, no valor. |
| `truncate`/reorg y nullifiers | `blockchain.ts:1315-1320`, `NullifierSet` | Desconectar trunca el árbol y borra nullifiers; el doble gasto por reorg exige reescribir >1,3 M de bloques de PoW. |

---

## 6. Conclusión operativa

El único crítico que pasa los cuatro criterios es el **alias de posición del árbol de notas**. Está en la release desplegada (`v2.12.0`), es permissionless, produce inflación sin cota del nativo y ya fue ejecutado contra el puente (2.787.953.680 wIRON en Base vs 76.993.394,75 IRON). El fix existente (`c5c3c22b`, 2026-10-29) **no es un parche de mainnet**: cambia las raíces de consenso y sólo regenera el génesis de devnet, por lo que el estado desplegado sigue siendo incompatible y no puede migrarse sin una cadena nueva o un circuito nuevo con nuevos parámetros. Hoy el delta realizable está limitado a los venues supervivientes (Gate IRON/USDT, ~1,8 k USD/24 h, mcap ~0,67 M USD); la dilución potencial es del 100% de la oferta.

Un segundo barrido (§5.1) sobre autorización de mints y propiedad de assets, conservación de valor y generadores, `noteSize`, dificultad/timestamps, checkpoints, mempool y reorgs **no encontró ningún crítico adicional** ni una segunda vía permissionless de crear valor. Los contratos y attesters del puente ChainPort en Ethereum/Base no están en ningún repo de la fundación (el repo sólo contiene el CLI que construye el depósito), así que esa superficie queda fuera de alcance por falta de código clonable, no por descarte.
