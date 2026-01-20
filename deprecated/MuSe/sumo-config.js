module.exports = {
  buildDir: 'build',
  contractsDir: 'contracts',
  testDir: 'test',
  skipContracts: ['contractName.sol'], // Relative paths from contractsDir
  skipTests: ['testFileName.js'], // Relative paths from testDir
  testingTimeOutInSec: 300,
  network: "none",
  testingFramework: "truffle",
  minimal: false,
  tce: false
}