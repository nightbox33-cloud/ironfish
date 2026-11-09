# Anclaje del estado live — Iron Fish mainnet (capturado 2026-11-09, UTC)

Todo lo de abajo se leyó en vivo durante la auditoría, no de memoria ni de snippets.
Se guardan los cuerpos crudos relevantes para que el reporte sea reproducible.

---

## 1. Cadena viva

### 1.1 Índice público (congelado)

`GET https://api.ironfish.network/blocks/head` (2026-11-09)

```json
{"id":4041131,
 "hash":"00000000002d32648bb1f3e2d2563732b1e289c4611dfee7354370ad1b7a4a6b",
 "sequence":1864830,
 "previous_block_hash":"00000000000c09731c118c871391d0bfe3d8abc2abd01d8186974762d201f7c5",
 "main":true,"difficulty":5666684002190,"transactions_count":1,
 "timestamp":"2026-10-31T22:43:40.961Z",
 "graffiti":"4d696e6564206279206865726f6d696e6572732e636f6d203130343937323238",
 "size":846,"reward":"1725000000",
 "circulating_supply":76993394.75,"total_supply":76993394.75}
```

`GET https://api.ironfish.network/supply/circulating` → `76993394.75`
`GET https://api.ironfish.network/supply/total` → `76993394.75`
`GET https://api.ironfish.network/versions` →

```json
{"ironfish":{"object":"version","version":"2.12.0","created_at":"2025-08-12T18:44:31.882Z"}}
```

`explorer.ironfish.network` (mismo instante): "Node 2.12.0", Height 1864830,
Latest Block Hash `00000000002d32…1b7a4a6b`, Circulating Supply 76,993,394.75.

→ El índice y el explorer están **congelados** en el bloque del 2026-10-31.

### 1.2 La cadena NO está detenida (PoW sigue)

`https://ironfish.herominers.com/` (2026-11-09):

```
Network Hash Rate: 38.78 GH/s
Average Block Time: 70.34 s
Blocks Found: less than a minute ago
Difficulty: 2.33 TH          (Avg 1d/7d: 2.57 TH / 2.67 TH)
Blockchain Height: 1 876 236
Pool Hash Rate: 32.45 GH/s   Connected Miners: 94 (208 workers)
Last Reward: 17.2500 IRON
```

Altura 1.876.236 > 1.864.830 indexada ⇒ se produjeron ~11.400 bloques después del
anuncio de fin de soporte. La dificultad bajó de 5,67 TH (API, 31-oct) a 2,33 TH,
consistente con salida de mineros, no con un halt.

Segunda fuente independiente — `https://miningpoolstats.stream/ironfish`
(actualizado 2026-11-08 20:16, refresco cada 3 min):

```
herominers.com  36.16 GH/s (86.4% conocidos)  last block 1876248  hace 4 min
pool.kryptex.com 5.10 GH/s (12.2%)             last block 1876235  hace 15 min
tw-pool.com      571.67 MH/s                  last block 1876112  hace 2 horas
Network Hashrate 38.69 GH/s ; precio IRON/USD 0.00871 ; Market Cap 670.63 K ; 24h Vol 1.84 K
Last 1000 blocks: herominers 54.8% / kryptex 32.7% / tw-pool 0.5% / Unknown 12%
```

(Ojo: el "Block Height 1864830" que muestra esa misma página sale del feed del
explorer congelado; las filas por pool muestran 1.876.235–1.876.250 encontrados
hace minutos.)

### 1.3 Parámetros de red (repo, tag v2.12.0 = b442f9b5…)

```
ironfish/src/networks/definitions/mainnet.ts
  id: 1
  genesis hash: 00000000000045885508f3c1455d676fe8749433dc71a748d07719fdde39aeb2
  genesis noteSize: 75, timestamp 1682006400000
  genesisSupplyInIron: 42000000
  bootstrap: 1.main.bn.ironfish.network, 2.main.bn.ironfish.network
ironfish-rust/src/assets/asset_identifier.rs:10
  NATIVE_ASSET = 51f33a2f14f92735e562dc658a5639279ddca3d5079a6d1242b2a588a9cbf44c
```

El fix `c5c3c22b` **no toca** `mainnet.ts` ni `testnet.ts` (sólo `devnet.ts`):

```
$ git show --stat c5c3c22 -- ironfish/src/networks/definitions/
 ironfish/src/networks/definitions/devnet.ts | 11 ++++++-----
```

---

## 2. Mercado (única vía de realización hoy)

`GET https://api.coingecko.com/api/v3/coins/iron-fish/tickers` (2026-11-09T01:01Z)

```json
{"base":"IRON","target":"USDT","market":{"name":"Gate","identifier":"gate"},
 "last":0.008718,"volume":211373.0,
 "converted_volume":{"usd":1841.04},
 "timestamp":"2026-11-09T00:56:40+00:00",
 "trade_url":"https://www.gate.com/trade/IRON_USDT",
 "coin_mcap_usd":670608.6460077706}
```

(La segunda entrada de CoinGecko es un token de Base mal etiquetado, marcado
`is_anomaly: true`, `is_stale: true` — ignorada.)

`market_data`: precio USD 0,00870995, `market_cap_rank` 3435,
`price_change_percentage_14d` = **−88,33 %**.

---

## 3. Evidencia on-chain del exploit (lado transparente)

### 3.1 wIRON en Base — oferta

`GET https://base.blockscout.com/api/v2/tokens/0x166E70941262AE7CbF9df5C8897a6242c546457D`

```json
{"address_hash":"0x166e70941262AE7cBf9df5c8897A6242c546457d",
 "decimals":"8","holders_count":"3140","name":"Wrapped IRON","symbol":"wIRON",
 "total_supply":"278795368000099518","type":"ERC-20"}
```

`278795368000099518 / 1e8 = 2.787.953.680,00099518 wIRON`

Oferta real de la L1: `76.993.394,75 IRON`
→ **36,21×** la oferta total; exceso sin respaldo ≈ **2.710.960.285 wIRON**.

El contrato es `TransparentUpgradeableProxy` (patrón de ChainPort): la autoridad de
mint es el puente, no los holders. Es decir, el wIRON salió de la L1 por el camino
IRON (L1) → depósito al puente → mint en Base.

### 3.2 Liquidez de terceros ya drenada

Pool Aerodrome volatile wIRON/USDC `0x9941dfa4d724fd7a2E5E5d9777560b20de98cE0d`
— `.../addresses/0x9941…/token-balances`:

```
USDC  0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913  value 118748231  (= 118,748231 USDC)
wIRON 0x166E70941262AE7CbF9df5C8897a6242c546457D  value 26908697519296129 (= 269.086.975,19 wIRON)
```

Pool asimétrico 118 USD / 269 M wIRON ⇒ el lado USDC fue extraído.

Holders de wIRON (Blockscout, `.../holders`), mayores:

```
0x498581fF718922c3f8e6A244956aF099B2652b2b  Uniswap V4 PoolManager      91750983343444910  (917,5 M)
0x9941dfa4d724fd7a2E5E5d9777560b20de98cE0d  Aerodrome wIRON/USDC        26908697519296129  (269,1 M)
0x351b698aC00D91f4cF8Da445fe9F67c207A1C4DA                               20229658047315168  (202,3 M)
0x378C0D8F3662AA49F7D9e2E8150C5d5c41c2f5E3  UniswapV2Pair              10902304995363011  (109,0 M)
```

### 3.3 El puente desde la L1 (código de la release desplegada)

```
ironfish-cli/src/commands/wallet/chainport/send.ts
  fetchChainportBridgeTransaction(...)  ->  bridge_output.publicAddress + amount + memoHex
  outputs = [ userOutput, gasOutput, (bridge_fee if > 0) ]
  -> tx normal de Iron Fish que paga al address del puente con memo
```

`GET https://api.ironfish.network/bridges/tokens` (2026-11-09):

```json
{"id":3323,"name":"USD Coin","symbol":"USDC","network_id":22,
 "web3_address":"8e36e31d677a47cbd883843a345654c814b1e9ec1e0125bac9031f052ced9174",
 "decimals":6,"chain_id":22,"network_name":"IRONFISH","blockchain_type":"ironfish"}
```

`/bridges/tokens/3323/networks` → Ethereum (chainport 2), Base (chainport 15).
→ el puente live es ChainPort; IRON nativo no aparece como token bridgeable, el
camino de salida es IRON (L1) → wIRON (Base) mediante el minter del puente.

---

## 4. Estado de despliegue del fix

```
$ gh api repos/iron-fish/ironfish/releases?per_page=3
v2.12.0  2025-08-12T18:44:02Z  prerelease=false
v2.11.0  2025-03-04T02:48:58Z
v2.10.0  2024-12-17T00:12:31Z

$ git log -1 --format='%H %ci' v2.12.0
b442f9b51a60bbb466b9e5cfbc859923b639161d 2025-08-12

$ git rev-list --count v2.12.0..HEAD
3      (c5c3c22b fix, 35c98a36 merge staging, 767a75cb rust CI)

$ git tag --contains c5c3c22b
(vacío)
```

`README.md` (versión con fix): "This code changes the consensus note commitment tree.
Its note roots are incompatible with existing Iron Fish mainnet and testnet history.
Use it only for a new chain with a new genesis".
`docs/merkle-note-position-alias-postmortem.md`: "It contains no activation-height
rule, dual-root verifier, legacy proof migration, or historical accounting plan."

→ Ningún nodo de mainnet puede estar corriendo el fix, y el fix no es desplegable
sobre el estado existente.

---

## 5. Cómo reproducir

```bash
# 1) Modelo del árbol + alias (sin dependencias)
python3 audits/ironfish-merkle-alias/merkle_alias_poc.py --selftest
python3 audits/ironfish-merkle-alias/merkle_alias_poc.py --demo --leaves 60000 --position 59999

# 2) Prueba con proofs reales (la aporta el propio repo; requiere toolchain Rust
#    para construir @ironfish/rust-nodejs y los parámetros Groth16)
cd ironfish && npx jest src/merkletree/positionProof.test.slow.ts

# 3) Código desplegado (release) para diff/inspección
git show v2.12.0:ironfish/src/merkletree/merkletree.ts | sed -n '500,760p'
git show v2.12.0:ironfish/src/consensus/verifier.ts    | sed -n '480,505p'
```

## 6. Capturas de estado (para re-verificar tras la auditoría)

| Endpoint | Valor esperado si nada cambia |
|---|---|
| `GET https://api.ironfish.network/supply/total` | `76993394.75` |
| `GET https://api.ironfish.network/blocks/head` | `sequence 1864830` (índice congelado) |
| `https://ironfish.herominers.com/` | altura > 1.876.236 |
| `GET https://base.blockscout.com/api/v2/tokens/0x166E…457D` | `total_supply 278795368000099518` |
