const Mutation = require("../../mutation");

/**
 * DLROperator is a mutation testing operator that targets data location keywords in variable declarations.
 * 
 * **Purpose**:
 * This operator is designed to create mutations by replacing data location keywords (`memory` and `storage`) in variable declarations within Solidity smart contracts. By doing so, it helps to evaluate how changing the data location affects the functionality and behavior of the contract.
 * 
 * **How It Works**:
 * 1. **Identifies Variable Declarations**: It traverses the abstract syntax tree (AST) of the smart contract to find all variable declarations that specify a data location.
 * 2. **Generates Mutations**:
 *    - If the variable's data location is `memory`, it creates a mutation that replaces `memory` with `storage`.
 *    - If the variable's data location is `storage`, it creates a mutation that replaces `storage` with `memory`.
 * 3. **Mutation Details**:
 *    - The mutation captures the start and end positions of the variable declaration, the line numbers, the original code, and the modified code with the data location replaced.
 * 
 * This script is useful for testing how changes in data location might impact the smart contract's functionality, efficiency, or gas usage.
 */

function DLROperator() {
  this.ID = "DLR";
  this.name = "data-location-replacement";
}

DLROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    VariableDeclaration: (node) => {
      if (node.storageLocation) {
        const start = node.range[0];
        const end = node.range[1] + 1; // Include the end of the variable declaration
        const lineStart = node.loc.start.line;
        const lineEnd = node.loc.end.line;
        const original = source.slice(start, end); // Extract the original code

        // Generate mutations by replacing data location keywords
        if (node.storageLocation === "memory") {
          const replacement = original.replace("memory", "storage");
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
        } else if (node.storageLocation === "storage") {
          const replacement = original.replace("storage", "memory");
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
        }
      }
    }
  });

  return mutations;
};

module.exports = DLROperator;
