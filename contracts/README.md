# Smart Contracts Collection

A curated collection of 22 smart contracts for security research, education, and development.

## Quick Stats

- **Total Contracts**: 22
- **Total Lines of Code**: 6,092
- **Categories**: 5 main categories
- **Vulnerability Types**: 6 types covered

## Directory Structure

```
contracts/
├── audited/                  # 3 professional ERC-20 tokens
├── vulnerabilities/          # 14 educational vulnerability examples
│   ├── reentrancy/          # 3 contracts (SWC-107)
│   ├── access_control/      # 3 contracts (SWC-105, 118)
│   ├── arithmetic/          # 3 contracts (SWC-101)
│   ├── unchecked_calls/     # 2 contracts (SWC-104)
│   ├── denial_of_service/   # 2 contracts (SWC-113, 128)
│   └── time_manipulation/   # 1 contract (SWC-116)
└── real_world/              # 4 contracts from Kaggle dataset
    ├── secure/              # 2 secure implementations
    └── vulnerable/          # 2 vulnerable contracts
```

## Quick Reference

### Audited Contracts (Production-Ready)
1. **HFABRIC_Token.sol** (1,706 LOC) - Full-featured ERC-20 with OpenZeppelin
2. **WadzPayToken.sol** (744 LOC) - Payment token with advanced features
3. **Quidax_Token.sol** (709 LOC) - Exchange token with security updates

### Most Educational Vulnerabilities
1. **BECToken_overflow.sol** - Famous $1B overflow exploit (April 2018)
2. **personal_bank_reentrancy.sol** - Classic reentrancy pattern
3. **fibonacci_delegatecall.sol** - Unsafe delegatecall demonstration

## Documentation

See [CONTRACT_TRANSFER_REPORT.md](CONTRACT_TRANSFER_REPORT.md) for:
- Detailed contract descriptions
- Vulnerability analysis
- Learning paths
- Testing recommendations
- Historical context
- Security patterns

## Quick Start

### Analyze a Vulnerability
```bash
# Read a reentrancy example
cat vulnerabilities/reentrancy/personal_bank_reentrancy.sol

# Check for the vulnerability marker
grep -n "REENTRANCY" vulnerabilities/reentrancy/personal_bank_reentrancy.sol
```

### Study Best Practices
```bash
# Examine a professional implementation
cat audited/HFABRIC_Token.sol | less

# Count contract complexity
wc -l audited/*.sol
```

### Compare Secure vs Vulnerable
```bash
# View a secure contract
cat real_world/secure/kaggle_secure_1.sol

# Compare with vulnerable version
cat real_world/vulnerable/kaggle_vuln_1.sol
```

## Recommended Tools

- **Slither**: Static analysis
- **Mythril**: Symbolic execution
- **Echidna**: Fuzzing
- **Foundry**: Testing framework
- **Hardhat**: Development environment

## Learning Path

1. **Start Simple**: `overflow_add.sol`, `auction_dos.sol`
2. **Classic Exploits**: `personal_bank_reentrancy.sol`, `BECToken_overflow.sol`
3. **Complex Patterns**: `fibonacci_delegatecall.sol`, `unchecked_call_1.sol`
4. **Production Code**: `HFABRIC_Token.sol`, `WadzPayToken.sol`

## Sources

- **SmartBugs Curated**: Labeled vulnerability dataset
- **BCCC 2023**: Kaggle secure/vulnerable contract pairs
- **Professional Audits**: Real-world audited tokens

## Notes

- All contracts preserve original annotations and vulnerability markers
- Vulnerable contracts are for **educational purposes only**
- Audited contracts follow OpenZeppelin standards and best practices

---

**Last Updated**: January 12, 2026
