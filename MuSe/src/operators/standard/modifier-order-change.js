const Mutation = require('../../mutation');

/**
 * MOCOperator is a mutation testing operator designed to test the effect of changing the order of modifiers applied to functions.
 * 
 * **Purpose**:
 * This operator helps identify potential issues arising from changes in the order of modifiers. Modifiers in Solidity can have significant effects on how functions operate, so altering their order can reveal vulnerabilities or logical errors.
 * 
 * **How It Works**:
 * 1. **Identify Functions with Multiple Modifiers**: Searches for functions that have more than one modifier.
 * 2. **Change the Order of Modifiers**: For each function, create mutations by swapping the order of adjacent modifiers.
 * 
 * **Mutation Details**:
 * - For each function with at least two modifiers, create mutations by changing the order of the first pair of adjacent modifiers.
 */

function MOCOperator() {
  this.ID = "MOC";
  this.name = "modifier-order-change";
}

MOCOperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      // If the function has at least two modifiers
      if (node.modifiers.length > 1) {
        const start = node.range[0];
        const end = node.body.range[0];
        const startLine = node.loc.start.line;
        const endLine = node.body.loc.start.line;
        const original = source.substring(start, end);  // Function signature
        let replacement;

        // Swap the order of adjacent modifiers
        for (let i = 0; i < node.modifiers.length - 1; i++) {
          const mod1 = source.slice(node.modifiers[i].range[0], node.modifiers[i].range[1] + 1);
          const mod2 = source.slice(node.modifiers[i + 1].range[0], node.modifiers[i + 1].range[1] + 1);
          replacement = original.replace(mod1, "*").replace(mod2, mod1).replace("*", mod2);

          // Create a mutation for each pair of swapped modifiers
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
      }
    }
  });

  return mutations;
};

module.exports = MOCOperator;
