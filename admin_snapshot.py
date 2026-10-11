"""
Admin Key Snapshot
For each contract in protocols.csv, find who can upgrade/control it
and classify the controller as: single wallet, multisig (Safe), or timelock.

Setup:   pip3 install web3
Run:     python3 admin_snapshot.py
Output:  results.json (and a summary table printed in the terminal)

Optional: set your own RPC with   export ETH_RPC_URL="https://..."
"""
import csv
import json
import os
import time
from datetime import datetime, timezone

from web3 import Web3

RPC_URL = os.environ.get("ETH_RPC_URL", "https://ethereum-rpc.publicnode.com")

# EIP-1967 standard storage slots
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"

# Legacy ZeppelinOS proxy slots (used by Circle's USDC proxy)
ZOS_IMPL_SLOT = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
ZOS_ADMIN_SLOT = "0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b"

# 4-byte function selectors
OWNER = "0x8da5cb5b"          # owner()
GET_THRESHOLD = "0xe75235b8"  # getThreshold()  -> Safe multisig
GET_OWNERS = "0xa0e67e2b"     # getOwners()     -> Safe multisig
REQUIRED = "0x" + bytes(Web3.keccak(text="required()")[:4]).hex()  # required() -> old Gnosis MultiSigWallet (Tether)
GET_MIN_DELAY = "0xf27a0c92"  # getMinDelay()   -> Timelock controller
COMPOUND_DELAY = "0x6a42b8f8" # delay()         -> Compound-style Timelock
COMPOUND_ADMIN = "0xf851a440" # admin()         -> Compound-style Timelock (also Curve's CRV)

ADDRESSES_PROVIDER = "0x" + bytes(Web3.keccak(text="ADDRESSES_PROVIDER()")[:4]).hex()

# Aragon-style app proxies (Lido): the DAO "Kernel" controls upgrades
KERNEL = "0x" + bytes(Web3.keccak(text="kernel()")[:4]).hex()
ARAGON_IMPL = "0x" + bytes(Web3.keccak(text="implementation()")[:4]).hex()

# Role-registry pattern (ether.fi): upgrade rights live in a separate registry contract
ROLE_REGISTRY = "0x" + bytes(Web3.keccak(text="roleRegistry()")[:4]).hex()

# Rocket Pool: the "guardian" in RocketStorage controls the protocol
GUARDIAN = "0x" + bytes(Web3.keccak(text="getGuardian()")[:4]).hex()

# Balancer V2: the Vault asks an "authorizer" contract who is allowed to do what
AUTHORIZER = "0x" + bytes(Web3.keccak(text="getAuthorizer()")[:4]).hex()

# --- Additional protocol patterns ---
# Yearn YFI: governance() returns the controlling address
GOVERNANCE = "0x" + bytes(Web3.keccak(text="governance()")[:4]).hex()

# Synthetix proxies expose target() instead of an EIP-1967 implementation slot
TARGET = "0x" + bytes(Web3.keccak(text="target()")[:4]).hex()

# Maker: permission list wards(address) -> 1 if the address is a ward
WARDS = "0x" + bytes(Web3.keccak(text="wards(address)")[:4]).hex()

# Maker's DSPause (the governance delay): has delay(), proxy(), authority()
DS_PROXY = "0x" + bytes(Web3.keccak(text="proxy()")[:4]).hex()
DS_AUTHORITY = "0x" + bytes(Web3.keccak(text="authority()")[:4]).hex()

# Maker's wards list cannot be read in one call, so we ask a specific question:
# "is this candidate a ward of this contract?"  Contract -> candidate controllers.
WARD_CANDIDATES = {
    # MCD_VAT -> MCD_PAUSE_PROXY
    Web3.to_checksum_address("0x35d1b3f3d7966a1dfe207aa4514c12a259a0492b"):
        [Web3.to_checksum_address("0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB")],
}

# Tried in this order after the proxy slots and owner() have found nothing.
# New entries are appended at the end so earlier results do not change.
GETTER_CHAIN = [
    ("ADDRESSES_PROVIDER() (Aave-style)", ADDRESSES_PROVIDER),
    ("kernel() (Aragon-style DAO)", KERNEL),
    ("roleRegistry() (role-registry pattern)", ROLE_REGISTRY),
    ("getGuardian() (Rocket Pool style)", GUARDIAN),
    ("getAuthorizer() (Balancer style)", AUTHORIZER),
    ("admin() (Curve style)", COMPOUND_ADMIN),
    ("governance() (Yearn style)", GOVERNANCE),
]

# Diagnostic only: for rows with no controller found, record which of these
# common getters answer, so we can see what pattern the contract uses.
PROBE_GETTERS = ["roleRegistry()", "authority()", "admin()", "governance()",
                 "proxyAdmin()", "pendingOwner()"]

MAX_HOPS = 3
PAUSE = 0.15  # seconds between RPC calls, to be polite to the public endpoint


def to_address(raw):
    """Last 20 bytes of a 32-byte word -> checksum address, or None if zero."""
    if raw is None or len(raw) < 32:
        return None
    tail = bytes(raw[-20:])
    if int.from_bytes(tail, "big") == 0:
        return None
    return Web3.to_checksum_address("0x" + tail.hex())


def safe_call(w3, to, data):
    try:
        time.sleep(PAUSE)
        res = w3.eth.call({"to": to, "data": data})
        return bytes(res) if res else None
    except Exception:
        return None


def read_slot(w3, addr, slot):
    time.sleep(PAUSE)
    return w3.eth.get_storage_at(addr, slot)


def describe(w3, addr):
    """Classify one address. Returns a dict with at least a 'type' key."""
    time.sleep(PAUSE)
    code = w3.eth.get_code(addr)
    if len(code) == 0:
        return {"type": "single_wallet", "address": addr}

    thr = safe_call(w3, addr, GET_THRESHOLD)
    if thr and len(thr) == 32:
        owners = safe_call(w3, addr, GET_OWNERS)
        n_owners = int.from_bytes(owners[32:64], "big") if owners and len(owners) >= 64 else None
        return {"type": "multisig", "address": addr,
                "threshold": int.from_bytes(thr, "big"), "signers": n_owners}

    # Old-style Gnosis MultiSigWallet (used by Tether): required() + getOwners()
    req = safe_call(w3, addr, REQUIRED)
    if req and len(req) == 32:
        owners = safe_call(w3, addr, GET_OWNERS)
        n_owners = int.from_bytes(owners[32:64], "big") if owners and len(owners) >= 64 else None
        return {"type": "multisig", "address": addr, "style": "legacy MultiSigWallet",
                "threshold": int.from_bytes(req, "big"), "signers": n_owners}

    delay = safe_call(w3, addr, GET_MIN_DELAY)
    if delay and len(delay) == 32:
        return {"type": "timelock", "address": addr,
                "delay_seconds": int.from_bytes(delay, "big")}

    # Compound-style Timelock: has both delay() and admin()
    c_delay = safe_call(w3, addr, COMPOUND_DELAY)
    c_admin = safe_call(w3, addr, COMPOUND_ADMIN)
    if c_delay and len(c_delay) == 32 and to_address(c_admin):
        return {"type": "timelock", "address": addr,
                "delay_seconds": int.from_bytes(c_delay, "big"),
                "admin": to_address(c_admin), "style": "Compound-style"}

    # Maker DSPause (governance delay): has delay() and proxy()
    if c_delay and len(c_delay) == 32:
        ds_proxy = to_address(safe_call(w3, addr, DS_PROXY))
        if ds_proxy:
            return {"type": "timelock", "address": addr,
                    "delay_seconds": int.from_bytes(c_delay, "big"),
                    "style": "DSPause (Maker)", "pause_proxy": ds_proxy,
                    "authority": to_address(safe_call(w3, addr, DS_AUTHORITY))}

    return {"type": "other_contract", "address": addr}


def follow_control(w3, addr):
    """Classify the controller; if it is a plain contract with an owner(), follow it."""
    chain = []
    current = addr
    for _ in range(MAX_HOPS):
        info = describe(w3, current)
        chain.append(info)
        if info["type"] != "other_contract":
            break
        nxt = to_address(safe_call(w3, current, OWNER))
        if not nxt or nxt == current:
            break
        current = nxt
    return chain


def find_ward(w3, addr):
    """Maker style: return the first candidate controller that is a ward of addr."""
    for cand in WARD_CANDIDATES.get(addr, []):
        arg = (bytes(12) + bytes.fromhex(cand[2:])).hex()
        res = safe_call(w3, addr, WARDS + arg)
        if res and len(res) == 32 and int.from_bytes(res, "big") == 1:
            return cand
    return None


def analyse(w3, name, address):
    row = {"name": name, "contract": address, "is_proxy": False,
           "control_source": None, "controller_chain": [], "final_type": "none_found",
           "notes": ""}
    try:
        addr = Web3.to_checksum_address(address)
    except Exception:
        row["notes"] = "invalid address"
        row["final_type"] = "error"
        return row
    row["contract"] = addr
    try:
        impl = to_address(read_slot(w3, addr, IMPL_SLOT))
        if impl is None:
            # Aragon-style proxies (Lido) expose implementation() instead
            impl = to_address(safe_call(w3, addr, ARAGON_IMPL))
        if impl is None:
            # Legacy ZeppelinOS proxies (Circle USDC)
            impl = to_address(read_slot(w3, addr, ZOS_IMPL_SLOT))
        if impl is None:
            # Synthetix-style proxies expose target()
            impl = to_address(safe_call(w3, addr, TARGET))
        row["is_proxy"] = impl is not None
        row["implementation"] = impl

        admin = to_address(read_slot(w3, addr, ADMIN_SLOT))
        zos_admin = None
        if not admin:
            zos_admin = to_address(read_slot(w3, addr, ZOS_ADMIN_SLOT))

        controller = None
        if admin:
            row["control_source"] = "EIP-1967 admin slot"
            controller = admin
        elif zos_admin:
            row["control_source"] = "ZeppelinOS admin slot (legacy proxy)"
            controller = zos_admin
        else:
            owner = to_address(safe_call(w3, addr, OWNER))
            if owner:
                row["control_source"] = "owner()"
                controller = owner
            else:
                for label, selector in GETTER_CHAIN:
                    found = to_address(safe_call(w3, addr, selector))
                    if found:
                        row["control_source"] = label
                        controller = found
                        break
                if controller is None:
                    ward = find_ward(w3, addr)
                    if ward:
                        row["control_source"] = "wards(address) (Maker style)"
                        row["notes"] = ("Confirmed the candidate is a ward. Other wards "
                                        "(e.g. protocol modules) may also exist; they "
                                        "cannot be listed with one call.")
                        controller = ward

        if controller:
            row["controller_chain"] = follow_control(w3, controller)
            row["final_type"] = row["controller_chain"][-1]["type"]
        else:
            row["notes"] = "No standard admin/owner found (may be immutable or use a custom pattern)"
            # Diagnostic: which common getters answer on this contract?
            probe = {}
            for sig in PROBE_GETTERS:
                sel = "0x" + bytes(Web3.keccak(text=sig)[:4]).hex()
                found = to_address(safe_call(w3, addr, sel))
                if found:
                    probe[sig] = found
            row["probe"] = probe
            if probe:
                row["notes"] += f" | getters that answered: {probe}"
    except Exception as e:  # keep going if one contract fails
        row["final_type"] = "error"
        row["notes"] = f"error: {e}"
    return row


def load_protocols(path="protocols.csv"):
    rows = []
    with open(path, newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    for r in csv.DictReader(lines):
        if r.get("name") and r.get("address"):
            rows.append((r["name"].strip(), r["address"].strip()))
    return rows


def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise SystemExit(f"Could not connect to {RPC_URL}")
    block = w3.eth.block_number
    protocols = load_protocols()
    if not protocols:
        raise SystemExit("protocols.csv has no entries yet. Add name,address lines.")

    results = []
    for name, address in protocols:
        print(f"Checking {name} ...")
        results.append(analyse(w3, name, address))

    out = {"snapshot_utc": datetime.now(timezone.utc).isoformat(),
           "block_number": block, "rpc": RPC_URL, "results": results}
    with open("results.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"\nSnapshot at block {block}")
    print(f"{'Protocol':<30}{'Proxy':<7}{'Controller type':<18}Details")
    print("-" * 90)
    for r in results:
        last = r["controller_chain"][-1] if r["controller_chain"] else {}
        detail = ""
        if last.get("type") == "multisig":
            detail = f"{last['threshold']} of {last['signers']}"
        elif last.get("type") == "timelock":
            detail = f"{last['delay_seconds'] / 3600:.1f} h delay"
        print(f"{r['name']:<30}{str(r['is_proxy']):<7}{r['final_type']:<18}{detail}")
    print("\nSaved results.json. Now spot-check rows on etherscan.io.")


if __name__ == "__main__":
    main()
