# Admin Key Snapshot

A small Python tool that answers one question for each DeFi contract on Ethereum mainnet: **who holds its admin power?**

For every contract listed in `protocols.csv`, the script finds the immediate controller and classifies it as a **single wallet**, a **multisig**, or a **timelock**. Results are saved to `results.json` and printed as a table in the terminal.

> **Status:** all 20 protocols were run through the script and spot-checked by hand on Etherscan. Rows the script cannot classify on its own are explained in [NOTES.md](NOTES.md). A few open items are listed at the end of this file.

This is a portfolio project, not new research. See [Related work](#related-work).

**Live dashboard:** https://muhammad-abbas-khalil.github.io/admin-key-snapshot/

## Snapshot

- **Date:** 10 Oct 2026 (19:41 UTC)
- **Network:** Ethereum mainnet
- **Block:** 26164177
- **RPC:** `https://ethereum-rpc.publicnode.com` (public endpoint)
- **EigenLayer Safe owners:** read separately at block 26164277, about 20 minutes after the main snapshot (see [NOTES.md](NOTES.md))

Admins can change at any time. This is a point-in-time snapshot, not a live monitor, and not an audit or a risk rating.

This repository reports who holds a role at one point in time. It does not claim that any protocol is unsafe, and it is not financial or security advice.

## Setup and usage

```bash
pip3 install web3
python3 admin_snapshot.py
```

Optional: use your own RPC endpoint.

```bash
export ETH_RPC_URL="https://..."
```

Add protocols to `protocols.csv` as `name,address` lines (lines starting with `#` are ignored). Each run overwrites `results.json`.

## How to read the results

- **Controller type is the immediate controller.** A **timelock** means a delay exists, not who is behind it. A timelock can itself be controlled by a multisig or by on-chain governance.
- **"Controller" is not always "can upgrade the code."** For contracts that are not proxies (for example USDT, Morpho Blue, Uniswap V3 Factory), the owner controls privileged functions such as fees, minting or blacklisting, but may not be able to replace the code.
- **A single wallet (EOA) is not necessarily one person.** It only means the address has no contract code.
- **A multisig's threshold does not tell you who the signers are.** Signers can be people, or other contracts (for example a timelock or another multisig).

## How the script finds the controller

For each contract it first checks whether it is a proxy (EIP-1967 implementation slot, `implementation()`, the legacy ZeppelinOS slot, or `target()` for Synthetix-style proxies). It then looks for the controller in this order:

1. **EIP-1967 admin slot** (standard proxies)
2. **Legacy ZeppelinOS admin slot** (older proxies, e.g. Circle USDC)
3. **`owner()`**
4. **`ADDRESSES_PROVIDER()`** (Aave style)
5. **`kernel()`** (Aragon style, e.g. Lido)
6. **`roleRegistry()`** (role-registry pattern, e.g. Ether.fi)
7. **`getGuardian()`** (Rocket Pool style)
8. **`getAuthorizer()`** (Balancer style)
9. **`admin()`** (Curve style)
10. **`governance()`** (Yearn style)
11. **`wards(address)`** (Maker style). This cannot list all wards, so the script asks about one candidate address and confirms it. **The Maker candidate was supplied manually, not discovered by the script.**

If the contract has none of these, the script probes a few common getters and marks the row `none_found`.

It then follows the controller for up to 3 hops and classifies each address:

- **single_wallet:** an address with no contract code (an EOA)
- **multisig:** a Safe (`getThreshold()`) or an old Gnosis-style MultiSigWallet (`required()`)
- **timelock:** an OpenZeppelin TimelockController (`getMinDelay()`), a Compound-style Timelock (`delay()` + `admin()`), or Maker's DSPause (`delay()` + `proxy()`)
- **other_contract:** anything else (needs a manual look)

## Results

| Protocol | Proxy? | Immediate controller | Details |
|---|---|---|---|
| Aave | Yes | On-chain DAO governance | PoolAddressesProvider, then Executor Lvl1 (ACL Admin), then PayloadsController |
| Lido stETH | Yes | DAO (Aragon Kernel) | LDO token holder votes |
| Morpho Blue | No | Multisig | 6 of 10 |
| Ethena USDe | No | Timelock | 24 h delay; who is behind it was not traced |
| Ether.fi eETH | Yes | Timelock | 240 h (10 days) delay; who is behind it was not traced |
| Compound III USDC | Yes | Timelock | 48 h delay |
| Uniswap V3 Factory | No | Timelock | 48 h delay |
| Circle USDC | Yes | Single wallet (EOA) | `0x807a96288A1A408dBC13DE2b1d087d10356395d2` |
| Chainlink LINK | No | Immutable (no admin) | No owner or admin function |
| Tether USDT | No | Multisig (legacy MultiSigWallet) | 3 of 6 |
| EigenLayer StrategyManager | Yes | Multisig of contracts | 1 of 2, behind a ProxyAdmin (`0x8b95...`). The two owners are a timelock (240 h = 10 days, `0xC06F...`) and the Community Multisig (9 of 13, `0xFEA4...`). Either owner can act alone: through the timelock, or through the multisig directly (see NOTES.md) |
| Pendle Router | Yes (see note) | Multisig | 3 of 5 (`owner()`). The script reports "No" because the router is a diamond proxy, which it does not detect |
| Rocket Pool Storage | No | Single wallet (EOA) | Guardian `0x0cCF14983364A7735d369879603930Afe10df21e`; the guardian role has special permissions (see NOTES.md) |
| Balancer V2 Vault | No | Contract (authorizer) | `0x6048...`, not traced further |
| Maker Sky Vat | No | Timelock (DSPause) | 48 h delay, via the pause proxy `0xBE8E...` |
| Curve CRV | No | DAO governance (Aragon Ownership Agent) | `0x4090...`, listed as the Ownership Agent in Curve's docs |
| Synthetix SNX | Yes | Multisig | 4 of 7 |
| Yearn YFI | No | Timelock contract, then multisig | 17280 block delay (about 2.4 days), then a 6-of-9 Safe |
| Convex Booster | No | Multisig | 3 of 5, behind two contracts (Booster Owner, then `BoosterOwnerSecondary`) |
| Optimism L1 Standard Bridge | Yes | Multisig of multisigs | 2 of 2: Optimism Foundation (5 of 7) and Security Council (10 of 13) |

### Summary of immediate controllers (20 protocols)

| Controller | Count | Protocols |
|---|---|---|
| Multisig | 7 | Morpho, USDT, EigenLayer, Pendle, Synthetix, Convex, Optimism |
| Timelock | 6 | Ethena, Ether.fi, Compound, Uniswap, Maker, Yearn (ends in a multisig) |
| On-chain DAO governance | 3 | Aave, Lido, Curve |
| Single wallet | 2 | Circle USDC, Rocket Pool |
| Immutable (no admin) | 1 | Chainlink LINK |
| Not resolved | 1 | Balancer |

EigenLayer and Optimism are multisigs whose signers are themselves contracts (a timelock and multisigs), not individuals. Yearn is counted as a timelock because the immediate controller is a timelock, which ends in a multisig.

This is a small, hand-picked sample of well-known protocols, not a statistical survey.

## Key findings

- Only **1 of 20** (Chainlink LINK) has no admin at all.
- **2 of 20** have a single externally owned address in the controller role: the Circle USDC proxy admin and the Rocket Pool guardian. The reading notes above apply: an address is not necessarily one person, and the guardian's current powers were not verified.
- Timelock delays in the sample range from **24 hours** (Ethena) to **10 days** (Ether.fi).
- **7 of 20** are controlled by a multisig, from 1 of 2 up to 6 of 10. Two of them (EigenLayer, Optimism) have contracts as signers, not individuals.
- **3 of 20** are controlled through on-chain DAO governance (Aave, Lido, Curve), based on each project's documentation.

These describe this sample at one block. They are not a ranking of how safe the protocols are.

## Limitations

- Snapshot only: admins can change after the snapshot block.
- **One flagship contract per protocol.** Each protocol is represented by a single main contract. Other contracts of the same protocol can have different controllers.
- **Admin or upgrade controller only.** Other privileged roles (for example pausers, minters, blacklisters or fee setters) are not covered.
- "Controller type" describes the immediate controller. It does not measure how trustworthy the signers are or how a multisig is operated.
- A multisig's threshold and signer count are read at the snapshot time. If a signer is itself a contract (for example Optimism's nested multisigs), the script does not follow it.
- Diamond (EIP-2535) proxies, such as Pendle's router, are not detected, so `is_proxy` can be wrong for them.
- The script prints delays as hours and assumes seconds. A delay counted in blocks (Yearn) is not detected.
- Maker's `wards` list cannot be read in one call, so only one candidate controller is confirmed.
- Some patterns need manual review (`other_contract` rows).
- Uses a public RPC with a short pause between calls. Use your own endpoint for large runs.

## Open items

- **Balancer:** the authorizer contract was not traced to its final controller.
- **Rocket Pool:** the current scope of the guardian's powers was not verified (see NOTES.md).
- **Compound and Uniswap:** the timelock `admin` addresses are recorded in `results.json` but were not traced further here.

## Related work

This project is small and builds on public work, including:

- the 2022 paper ["Not so immutable: Upgradeability of Smart Contracts on Ethereum"](https://arxiv.org/abs/2206.00716), which measured upgradeable proxies and who can upgrade them on Ethereum;
- the 2024 study ["Immutable in Principle, Upgradeable by Design: Exploratory Study of Smart Contract Upgradeability"](https://arxiv.org/abs/2407.01493), which examined upgradeable proxies at larger scale;
- the 2024 paper ["Definition and Detection of Centralization Defects in Smart Contracts"](https://arxiv.org/abs/2411.10169), which defines issues such as a single proxy admin and management without a timelock;
- [L2BEAT](https://l2beat.com), which publishes admin and upgrade-risk information for rollups.

Corrections are welcome: open an issue if a row looks wrong.

## Files

- `admin_snapshot.py`: the script
- `protocols.csv`: input list of protocol names and addresses
- `results.json`: output of the latest run
- `index.html`: the dashboard page, served by GitHub Pages
- `og.png`: preview image shown when the dashboard link is shared
- `NOTES.md`: detailed manual verification notes and sources
- `LICENSE`: MIT license
- `.gitignore`: keeps Python cache and macOS files out of the repository
