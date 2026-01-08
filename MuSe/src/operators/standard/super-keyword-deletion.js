const Mutation = require('../../mutation');

/**
 * SKDOperator is a mutation testing operator designed to remove the `super` keyword from Solidity smart contracts.
 * 
 * **Purpose**:
 * The operator tests how the contract behaves when `super` keyword references are removed. The `super` keyword is used to call functions from a base contract. Removing `super` calls can help evaluate if the contract is correctly handling inheritance and base contract functions when they are no longer accessible.
 * 
 * **How It Works**:
 * 1. **Identify Base Contracts**: The script first identifies contracts that have base contracts, which are contracts inherited from other contracts.
 * 2. **Find `super` References**: Within these contracts, it locates occurrences of the `super` keyword used in member access.
 * 3. **Replace `super` Keyword**: Each occurrence of `super` is replaced with an empty string, effectively removing the call to the base contract's method.
 * 4. **Create Mutation Instances**: The mutations, which consist of the removal of `super` references, are added to a list for testing and further analysis.
 */

function SKDOperator() {
  this.ID = "SKD";
  this.name = "super-keyword-deletion";
}

SKDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit Contract Definitions to find contracts that inherit from other contracts
  visit({
    ContractDefinition: (node) => {
      if (node.baseContracts.length > 0) {
        visit({
          MemberAccess: (node) => {
            // Look for occurrences of the `super` keyword
            if (node.expression.name === "super") {
              const start = node.expression.range[0];
              const end = node.expression.range[1] + 2; // Adjusting end to include 'super'

              const startLine = node.expression.loc.start.line;
              const endLine = node.expression.loc.end.line;
              const original = source.slice(start, end);

              // Create a mutation for replacing `super` with an empty string
              const mutation = new Mutation(file, start, end, startLine, endLine, original, "", this.ID);

              // Ensure no duplicate mutations
              if (mutations.filter(m => m.hash() === mutation.hash()).length === 0) {
                mutations.push(mutation);
              }  
            }
          }
        });
      }
    }
  });

  return mutations;
};

module.exports = SKDOperator;
