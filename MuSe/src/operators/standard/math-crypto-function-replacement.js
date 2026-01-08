const Mutation = require('../../mutation');

/**
 * MCROperator is a mutation testing operator designed to mutate math and cryptographic functions in Solidity smart contracts.
 * 
 * **Purpose**:
 * This operator tests the impact of replacing certain math and cryptographic functions with other related functions.
 * 
 * **How It Works**:
 * 1. **Identifies Function Calls**: Searches for function calls to specific math and cryptographic functions.
 * 2. **Generates Mutations**:
 *    - Replaces each identified function call with another related function.
 * 
 * **Mutation Details**:
 * - For each identified function call, create mutations by replacing it with a related function.
 */

function MCROperator() {
  this.ID = "MCR";
  this.name = "math-and-crypto-function-replacement";
}

MCROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  const functions = ["addmod", "mulmod", "keccak256", "sha256", "ripemd160"];
  const ranges = []; // Visited node ranges

  // Visit function call nodes
  visit({
    FunctionCall: (node) => {
      if (!ranges.includes(node.range)) {
        if (functions.includes(node.expression.name)) {
          ranges.push(node.range);
          const start = node.expression.range[0];
          const end = node.expression.range[1] + 1;
          const startLine = node.expression.loc.start.line;
          const endLine = node.expression.loc.end.line;
          const original = source.slice(start, end);

          // Create mutations by replacing the function call with related functions
          switch (node.expression.name) {
            case "addmod":
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "mulmod", this.ID));
              break;
            case "mulmod":
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "addmod", this.ID));
              break;
            case "keccak256":
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "sha256", this.ID));
              break;
            case "sha256":
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "keccak256", this.ID));
              break;
            case "ripemd160":
              mutations.push(new Mutation(file, start, end, startLine, endLine, original, "sha256", this.ID));
              break;
          }
        }
      }
    }
  });
  
  return mutations;
};

module.exports = MCROperator;
