const Mutation = require('../../mutation');

/**
 * ORFDOperator is a mutation testing operator for deleting overridden functions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator helps identify issues by testing the impact of removing overridden functions. It is useful for ensuring that the contract's behavior is robust and handles cases where overridden functions are missing.
 * 
 * **How It Works**:
 * 1. **Identify All Overridden Functions**: Collect all functions that are marked as overridden.
 * 2. **Generate Mutations**: Create mutations by removing these overridden functions.
 * 
 * **Mutation Details**:
 * - Deletes functions that are marked as overridden.
 */

function ORFDOperator() {
  this.ID = "ORFD";
  this.name = "overridden-function-deletion";
}

ORFDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var ranges = [];

  visit({
    ContractDefinition: (node) => {
      if (node.baseContracts.length > 0) {
        visit({
          FunctionDefinition: (node) => {
            if (!ranges.includes(node.range)) {
              if (node.override) {
                var start = node.range[0];
                var end = node.range[1] + 1;
                const startLine = node.loc.start.line;
                const endLine = node.loc.end.line; 
                var original = source.slice(start, end);
                const replacement = ""; // Removing the function
                mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
              }
              ranges.push(node.range);
            }
          }
        });
      }
    }
  });

  return mutations;
};

module.exports = ORFDOperator;
