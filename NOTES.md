# Manual verification notes

Detailed notes for rows that needed checks beyond the script output. The README keeps only the summary.

Statements marked **(docs)** come from the project's own documentation, **(press)** from news reporting, and **(interpretation)** are readings of code or data that were not executed or confirmed by the project.

## Protocol notes

In the same order as the table in the README.

### Aave

The script reports `other_contract`. The controllers were identified using the project's official documentation. The chain is `0x2f39...` (PoolAddressesProvider), `0x5300...` (Executor Lvl1 / ACL Admin), `0xdAba...` (PayloadsController).

### Lido stETH

The script reports `other_contract`. The controller `0xb8FF...` is the address returned by the stETH contract's `kernel()` function. Lido's docs **(docs)** describe the Lido DAO as an Aragon organization in which LDO token holders vote on upgrades. The implementation address in `results.json` (`0x028271E3...`) matches the implementation shown on Etherscan.

### Morpho Blue

The script found no proxy. `owner()` is a Safe at `0xcBa2...9AFa` with threshold 6 and 10 owners. Whether the contract's code can be changed was not checked beyond the proxy test.

### Ethena USDe

The script found no proxy. `owner()` is a timelock at `0xE8Dc...7c94` with a 24 h delay. Who controls that timelock was not traced.

### Ether.fi eETH

The proxy's control is read through `roleRegistry()` (`0x6224...7cE9`), whose owner is a timelock at `0x9f26...0761` with a 240 h (10 day) delay **(interpretation: the script treats the role registry as the holder of upgrade rights)**. Who controls the timelock was not traced.

### Compound III USDC

The proxy admin slot points to a contract at `0x1EC6...8779`, whose owner is a Compound-style timelock at `0x6d90...3925` with a 48 h delay. The timelock's `admin` is recorded as `0x309a...c8C0` in `results.json` and was not traced further here.

### Uniswap V3 Factory

The script found no proxy. `owner()` is a contract at `0xf237...Bf5A`, whose owner is a Compound-style timelock at `0x1a9C...35BC` with a 48 h delay. The timelock's `admin` is recorded as `0x408E...24C3` and was not traced further here.

### Circle USDC

The admin storage slot was read directly and matches the script. Etherscan logs show the admin was rotated in the past, so treat this as the *current* state only.

### Chainlink LINK

The script reports `none_found`. Etherscan's Read Contract shows only standard token functions (`name`, `totalSupply`, `decimals`, `balanceOf`, `symbol`, `allowance`) and no proxy, so it is recorded as immutable with no admin.

### Tether USDT

The owner is an old Gnosis-style multisig, which uses `required()` instead of Safe's `getThreshold()`. The script was extended to detect this, and it now reports 3 of 6.

### EigenLayer

The proxy admin `0x8b95...` is owned by a Safe at `0x369e...9111` with threshold 1 and 2 owners. That address is listed as the **Executor Multisig** in EigenLayer's contracts repository.

The owners were read on-chain at block 26164277 (about 100 blocks after the main snapshot) using a one-off script that is not included in this repository. To reproduce: open the Safe on Etherscan, then Contract, Read as Proxy, `getOwners`, `getThreshold`, and check each owner address:

| Owner | Type | Details |
|---|---|---|
| `0xC06Fd4F821eaC1fF1ae8067b36342899b57BAa2d` | Timelock | 240 h (10 days) minimum delay |
| `0xFEA47018D632A77bA579846c840d5706705Dc598` | Multisig | 9 of 13 |

Both addresses match EigenLayer's current governance docs **(docs)**: the first is listed as the primary timelock, which enforces a minimum 10-day delay on safety-critical functions, and the second is listed as the Community Multisig (9-of-13).

Because the Safe's threshold is 1, **either owner can act on its own**:

- the **timelock path**: upgrades queued by the proposers (the Operations and Protocol Council multisigs, per the docs) and executed after the delay;
- the **Community Multisig path**: 9 of 13 community signers, which the docs describe as an emergency path that can execute time-critical upgrades immediately.

So the "1 of 2" is not two individuals. It is a 10-day timelock plus a 9-of-13 multisig. The docs describe the Community Multisig's role as emergency-only, but nothing on-chain limits it to that. Who the proposers are, and the signers of the Community Multisig, are taken from the docs and were not checked on-chain here.

Sources: EigenLayer docs (multisig governance); Eigen Foundation docs (technical architecture); `Layr-Labs/eigenlayer-contracts` README.

### Pendle

The script reports `is_proxy: false`. Pendle's own developer docs **(docs)** describe RouterV4 (`0x8888...F946`) as upgradable, with features added gradually without partners migrating. A third-party code analysis describes the router as an EIP-2535 diamond proxy and names a governance proxy as the upgrade path **(interpretation, third-party)**. The script does not detect diamond proxies, so the README records Pendle as a proxy and notes the discrepancy. The 3-of-5 multisig in the table is the contract's `owner()`; whether it is the sole upgrade authority was not confirmed.

Source: Pendle developer docs (Router overview).

### Rocket Pool

The guardian `0x0cCF...df21e` has no contract code, so it is recorded as a single wallet. In 2023, press coverage **(press)** reported that this address was the Rocket Pool deployer account, that many functions in Rocket Pool's contracts are restricted to the guardian, and that Rocket Pool said it intended to move toward decentralization of its Protocol DAO. **Not verified here:** how much power the guardian still holds today. Treat "single wallet" as a statement about the address type, not a full description of who controls Rocket Pool.

Sources: Cointelegraph and The Block coverage, July 2023.

### Balancer

The Vault's `getAuthorizer()` returns `0x6048...`. Balancer's docs **(docs)** state that permissioned Vault actions are checked against an Authorizer contract, and that the current Authorizer should be read from the Vault. The docs also describe a DAO multisig with powers granted through V2 contracts. This README did not trace the Authorizer to its final controller, so the row stays unresolved.

### Maker

The script confirms that the pause proxy is a ward of the Vat and that the DSPause behind it has a 48 h delay. The pause proxy was supplied as a candidate, not discovered. Other wards may exist, because they cannot be listed with one call.

### Curve

The script reports `other_contract` for the CRV token's `admin()` (`0x4090...`). Curve's docs **(docs)** list this address as the **Ownership Agent** of Curve DAO, which executes votes made through an Aragon-based voting app. Ownership votes need 30% quorum and 51% support, and voting lasts 7 days.

Sources: Curve docs (Governance and Voting; deployed contracts).

### Synthetix

The proxy is detected through `target()`. The owner is a multisig with threshold 4 and 7 owners.

### Yearn YFI

The script reports `other_contract` because the controller has no `owner()`. YFI's `governance()` is `0x026D...FB61`, a verified contract named `TimelockGovernance`. Its constructor arguments are the Yearn multisig and YFI. That multisig, `0xFEB4...Ff52`, is labeled "Yearn Treasury" on Etherscan and is a 6-of-9 Safe, matching Yearn's docs **(docs)**, which describe the multisig (yChad) as a 6-of-9 Gnosis Safe.

The delay (`period`, 17280) is counted in blocks, not seconds: the update functions revert with a `<block.number` message. At 12-second blocks that is about 2.4 days.

**(interpretation, not executed)** From the bytecode, the functions that queue a change can only be called by the governance address, and the functions that apply a queued change have no caller check.

**(interpretation)** The timelock still stores `newTargetGovernance = 0x0C97...6110` with an old block number. That address is a verified Vyper contract with four functions (`brrr`, `revoke`, `yfi`, `minted`) and two transactions in 2021. From the bytecode, `brrr()` makes the contract a YFI minter, mints to the Yearn multisig, drops the minter role and returns governance to the timelock. `minted()` currently returns `true`, so `brrr()` cannot run again. This appears to be a spent one-off mint helper, not a hidden controller.

### Convex

The chain is Booster, then "Convex Finance: Booster Owner" (`0x3cE6...`), then `0x256e...`, then "Convex Finance: Multisig" (`0xa3C5...`, 3 of 5). `0x256e...` has no label but has verified source named `BoosterOwnerSecondary` and was created by "Convex Finance: Deployer". Its interface has `owner`, `execute`, `executeDirect`, `sealOwnership` and many admin setters. The only wait-style functions are `queueForceShutdown` and `forceShutdownSystem`. No general timelock appears in its interface. Its source code was not reviewed, so what it restricts is not stated here.

### Optimism

The bridge proxy's admin is a verified `ProxyAdmin` (`0x543b...`). Its owner `0x5a0A...` is labeled "Optimism: L1 Proxy Admin" and is a Safe with threshold 2 and two owners. The two owners are the Optimism Foundation Safe `0x847B...9D92` (threshold 5, 7 owners) and the Security Council Safe `0xc281...Bd03` (threshold 10, 13 owners). Optimism governance posts **(docs)** name `0x5a0A...` as the OP Governed L1 ProxyAdmin Owner in the standard 2-of-2 setup, and Protocol Upgrade #8 sets the Security Council Safe's threshold to 10 of 13. The sources checked mention no upgrade delay, which means none is documented there, not that none exists.

## Sources

### Project documentation and governance posts

- Aave, deployed contracts: https://aave.com/docs/resources/addresses
- Lido, deployed contracts: https://docs.lido.fi/deployed-contracts/
- EigenLayer, multisig governance: https://docs.eigenlayer.xyz/eigenlayer/security/multisig-governance
- Eigen Foundation, technical architecture: https://docs.eigenfoundation.org/protocol-governance/technical-architecture
- Pendle, Router: https://docs.pendle.finance/Developers/Contracts/PendleRouter
- Curve, governance: https://docs.curve.finance/governance/overview
- Balancer, multisig: https://docs.balancer.fi/concepts/governance/multisig.html
- Yearn, multisig: https://docs.yearn.fi/developers/security/multisig
- Optimism governance, Protocol Upgrade #8 (Security Council threshold): https://gov.optimism.io/t/final-protocol-upgrade-8-guardian-security-council-threshold-and-l2-proxyadmin-ownership-changes-for-stage-1-decentralization/8157
- Optimism governance, Unichain ProxyAdmin Owner proposal (names the OP Governed L1 ProxyAdmin Owner): https://gov.optimism.io/t/maintenance-upgrade-proposal-unichain-proxyadmin-owner-transition-to-standard-optimism-governance/10839

### News coverage

- Cointelegraph, "Lido, Rocket Pool team members argue over decentralization" (July 2023): https://cointelegraph.com/news/lido-rocket-pool-team-members-argue-over-decentralization
- The Block, "Rocket Pool promises to fix centralization concerns related to pDAO" (July 2023): https://www.theblock.co/post/237808/rocket-pool-promises-to-fix-centralization-concerns-related-to-pdao

### Related research

- "Not so immutable: Upgradeability of Smart Contracts on Ethereum": https://arxiv.org/abs/2206.00716
- "Immutable in Principle, Upgradeable by Design: Exploratory Study of Smart Contract Upgradeability": https://arxiv.org/abs/2407.01493
- "Definition and Detection of Centralization Defects in Smart Contracts": https://arxiv.org/abs/2411.10169
- L2BEAT: https://l2beat.com

### On-chain data

- Etherscan address pages (labels, verified source, Read Contract) for the contracts in `results.json`: https://etherscan.io
- Ethereum mainnet read through a public RPC (`https://ethereum-rpc.publicnode.com`) at block 26164177.
