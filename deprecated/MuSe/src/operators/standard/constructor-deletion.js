const Mutation = require("../../mutation");

/**
 * CCDOperator is a mutation testing operator that targets constructors in Solidity contracts.
 * 
 * This script is designed to create mutations by deleting constructor definitions from smart contracts.
 * 
 * **Purpose**:
 * The primary aim of this operator is to test how the absence of a constructor affects the behavior and functionality of a smart contract. By removing constructors, it helps assess the robustness of the contract's deployment and initialization logic.
 * 
 * **How It Works**:
 * 1. **Identifies Constructor Definitions**: It traverses the abstract syntax tree (AST) of the contract to find all constructor definitions.
 * 2. **Generates Mutations**:
 *    - For each constructor found, it creates a mutation that deletes the entire constructor block.
 * 3. **Mutation Details**:
 *    - The mutation captures the start and end positions of the constructor in the source code, the line numbers, the original constructor code, and an empty string as the replacement (indicating deletion).
 * 
 * This script helps in evaluating the contract's ability to handle the absence of initialization logic, which can be critical for ensuring that the contract behaves as expected under various conditions.
 */

function CCDOperator() {
  this.ID = "CCD";
  this.name = "contract-constructor-deletion";
}

CCDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      if (node.isConstructor) {
        const start = node.range[0];
        const end = node.range[1] + 1; // Include the end of the constructor
        var lineStart = node.loc.start.line;
        var lineEnd = node.loc.end.line;
        const original = source.slice(start, end); // Extract the original constructor code
        const replacement = ""; // Replacement is an empty string to indicate deletion
        mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = CCDOperator;
