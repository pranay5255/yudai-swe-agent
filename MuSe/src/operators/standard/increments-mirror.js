const Mutation = require('../../mutation');

/**
 * ICMOperator is a mutation testing operator designed to mutate increment operations in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of mirroring increment operations.
 * 
 * **How It Works**:
 * 1. **Identifies Increment Operations**: Searches for binary operations involving the `-=` operator.
 * 2. **Generates Mutations**:
 *    - Replaces each `-=` operator with `=-`.
 * 
 * **Mutation Details**:
 * - For each `-=` operator, create a mutation by mirroring the operator to `=-`.
 */

function ICMOperator() {
  this.ID = "ICM";
  this.name = "increments-mirror";
}

ICMOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    BinaryOperation: (node) => {
      // Check if the operator is '-='
      if (node.operator === "-=") {
        const start = node.left.range[1] + 1;
        const end = node.right.range[0];
        const startLine = node.left.loc.end.line;
        const endLine = node.right.loc.start.line;
        const original = source.slice(start, end);

        // Replace '-=' with '=-'
        const replacement = original.replace("-=", "=-");

        // Push the mutation if a replacement was made
        if (replacement) {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
        }
      }
    }
  });

  return mutations;
};

module.exports = ICMOperator;
