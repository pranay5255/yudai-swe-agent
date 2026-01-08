const Mutation = require('../../mutation');

/**
 * SKIOperator is a mutation testing operator designed to insert the `super` keyword into function calls within Solidity smart contracts.
 * 
 * **Purpose**:
 * The operator tests how the contract behaves when the `super` keyword is added to function calls that override functions from a base contract. The `super` keyword is used to call methods from base contracts, and this mutation helps evaluate if adding such calls impacts the contract's functionality and correctness.
 * 
 * **How It Works**:
 * 1. **Identify Overridden Functions**: The script first identifies functions in derived contracts that override functions from base contracts.
 * 2. **Locate Function Calls**: It then locates function calls that match these overridden functions.
 * 3. **Insert `super` Keyword**: For each matching function call, the script inserts the `super` keyword before the function name.
 * 4. **Create Mutation Instances**: The mutations, which consist of adding the `super` keyword to function calls, are added to a list for testing and further analysis.
 */

function SKIOperator() {
  this.ID = "SKI";
  this.name = "super-keyword-insertion";
}

SKIOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  const overriddenFunctions = [];

  // Visit Contract Definitions to find contracts that inherit from other contracts
  visit({
    ContractDefinition: (node) => {
      if (node.baseContracts.length > 0) {
        // Visit Function Definitions to find overridden functions
        visit({
          FunctionDefinition: (node) => {
            if (node.override) {
              overriddenFunctions.push(node.name);
            }
          }
        });
        // Visit Function Calls to insert `super` keyword
        visit({
          FunctionCall: (node) => {
            if (overriddenFunctions.includes(node.expression.name)) {
              const start = node.expression.range[0];
              const end = node.expression.range[1] + 1; // Adjusting end to include the full function call

              const startLine = node.expression.loc.start.line;
              const endLine = node.expression.loc.end.line;
              const original = source.slice(start, end);

              // Create the replacement string with `super` keyword
              const replacement = "super." + original;
              const mutation = new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID);
              
              // Ensure no duplicate mutations
              if (!mutations.find(m => m.id === mutation.id)) {
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

module.exports = SKIOperator;
