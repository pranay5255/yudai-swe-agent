const Mutation = require('../../mutation');

/**
 * OMDOperator is a mutation testing operator for deleting overridden modifiers in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator helps identify issues by testing the impact of removing overridden modifiers. It is useful for ensuring that the contract's behavior is robust and handles cases where overridden modifiers are missing.
 * 
 * **How It Works**:
 * 1. **Identify All Overridden Modifiers**: Collect all modifiers that are marked as overridden.
 * 2. **Generate Mutations**: Create mutations by removing these overridden modifiers.
 * 
 * **Mutation Details**:
 * - Deletes modifiers that are marked as overridden.
 */

function OMDOperator() {
  this.ID = "OMD";
  this.name = "overridden-modifier-deletion";
}

OMDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    ContractDefinition: (node) => {
      if (node.baseContracts.length > 0) {
        visit({
          ModifierDefinition: (node) => {
            if (node.override) {
              const start = node.range[0];
              const end = node.range[1] + 1;
              const startLine = node.loc.start.line;
              const endLine = node.loc.end.line; 
              const original = source.slice(start, end);
              const replacement = ""; // Removing the modifier
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
            }
          }
        });
      }
    }
  });

  return mutations;
};

module.exports = OMDOperator;
