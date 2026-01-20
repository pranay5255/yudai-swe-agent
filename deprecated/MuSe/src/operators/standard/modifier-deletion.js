const Mutation = require('../../mutation');

/**
 * MODOperator is a mutation testing operator designed to remove modifiers from function definitions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of removing modifiers from functions, which can help identify potential security and logical flaws.
 * 
 * **How It Works**:
 * 1. **Identifies Function Definitions**: Searches for function definitions that have modifiers.
 * 2. **Generates Mutations**:
 *    - For each modifier in the function definition, create a mutation by removing the modifier.
 * 
 * **Mutation Details**:
 * - For each identified function modifier, create a mutation by removing it from the function definition.
 */

function MODOperator() {
  this.ID = "MOD";
  this.name = "modifier-deletion";
}

MODOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Visit function definition nodes
  visit({
    FunctionDefinition: (node) => {
      let replacement;
      if (node.modifiers.length > 0) { // Check if the function has modifiers
        const start = node.range[0];
        const end = node.body.range[0];
        const startLine = node.loc.start.line;
        const endLine = node.body.loc.start.line; 
        const original = source.substring(start, end); // Get the function signature without the body

        // For each modifier, create a mutation by removing the modifier
        node.modifiers.forEach(m => {
          const mod = source.slice(m.range[0], m.range[1] + 1);
          replacement = original.replace(mod, "");
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        });
      }
    }
  });
  
  return mutations;
};

module.exports = MODOperator;
